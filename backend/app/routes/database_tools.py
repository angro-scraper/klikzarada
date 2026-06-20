from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from .. import finance_models, models
from ..database import get_db
from ..services.admin_auth import require_admin_session
from ..services.json_store import read_json, write_json

router = APIRouter(prefix="/database", tags=["database tools"])

PILOT_TEXT_MARKERS = (
    "pilot",
    "test",
    "demo",
    "sample",
    "seed",
    "primer",
    "probni",
)
PILOT_URL_MARKERS = (
    "seed://",
    "seed://v",
    "example.com/pilot",
    "example.com/pilot-partner",
    "example.com/sacuvaj-hranu-demo",
    "/admin-assets/seed-images/",
    "sacuvaj-hranu.local",
    "/pilot/",
    "pilot-live",
    "partner-live",
    "partner-panel",
    "pilot-partner-onboarding",
)


def _csv_response(filename: str, rows: list[dict]) -> Response:
    output = io.StringIO()
    if rows:
        fieldnames = list(rows[0].keys())
    else:
        fieldnames = ["empty"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    if rows:
        writer.writerows(rows)
    else:
        writer.writerow({"empty": ""})
    content = output.getvalue().encode("utf-8-sig")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _norm_key(text: str | None) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9čćžšđа-я0-9]+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(akcija|snizenje|sniženje|popust|novo|super|cena)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _safe_price(price: float | None) -> str:
    if price is None:
        return ""
    return f"{price:.2f}"


def _contains_pilot_marker(*values: str | None) -> bool:
    haystack = " ".join(str(value or "").strip().lower() for value in values)
    return any(marker in haystack for marker in PILOT_TEXT_MARKERS)


def _contains_pilot_url(*values: str | None) -> bool:
    haystack = " ".join(str(value or "").strip().lower() for value in values)
    return any(marker in haystack for marker in PILOT_URL_MARKERS)


def _is_local_test_email(value: str | None) -> bool:
    return str(value or "").strip().lower().endswith(".local")


def _flatten_json_text(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_json_text(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten_json_text(item) for item in value)
    return str(value or "")


def _is_pilot_store(store: models.Store) -> bool:
    return (
        _contains_pilot_marker(
            store.name,
            store.city,
            store.address,
            store.website,
            store.phone,
            store.blocked_reason,
            store.seller_type,
        )
        or _contains_pilot_url(store.website, store.address)
    )


def _is_pilot_product(product: models.Product, store: models.Store | None) -> bool:
    return (
        _contains_pilot_marker(
            product.name,
            product.category,
            product.description,
            product.pickup_window,
            product.status,
            store.name if store else None,
            store.city if store else None,
        )
        or _contains_pilot_url(
            product.source_url,
            product.image_url,
            store.website if store else None,
        )
    )


def _is_pilot_customer(customer: models.Customer) -> bool:
    return (
        _contains_pilot_marker(
            customer.name,
            customer.block_reason,
            customer.status,
            customer.email,
            customer.phone,
        )
        or _is_local_test_email(customer.email)
        or "pilot" in str(customer.phone or "").lower()
    )


def _is_pilot_reservation(reservation: models.Reservation, product_id: int | None) -> bool:
    return (
        (product_id is not None and reservation.product_id == product_id)
        or _contains_pilot_marker(
            reservation.customer_name,
            reservation.customer_phone,
            reservation.note,
            reservation.payment_provider,
            reservation.payment_method,
            reservation.payment_reference,
            reservation.reservation_code,
            reservation.seller_payout_reference,
            reservation.seller_payout_note,
            reservation.status,
            reservation.payment_status,
        )
        or _contains_pilot_url(
            reservation.payment_provider,
            reservation.payment_method,
            reservation.payment_reference,
            reservation.seller_payout_reference,
        )
        or _is_local_test_email(reservation.customer_email)
    )


def _is_pilot_source(source: models.Source) -> bool:
    return _contains_pilot_marker(source.name, source.city, source.source_type) or _contains_pilot_url(source.url)


def _purge_pilot_rows(name: str, *, dry_run: bool) -> dict[str, int]:
    rows = read_json(name, [])
    if not isinstance(rows, list):
        return {"removed": 0, "remaining": 0}
    kept = []
    removed = 0
    for row in rows:
        if not isinstance(row, dict):
            kept.append(row)
            continue
        text_blob = _flatten_json_text(row)
        if _contains_pilot_marker(text_blob) or _contains_pilot_url(text_blob) or _is_local_test_email(text_blob):
            removed += 1
            continue
        kept.append(row)
    if not dry_run:
        write_json(name, kept)
    return {"removed": removed, "remaining": len(kept)}


@router.get("/products.csv", response_class=Response)
def export_products_csv(db: Session = Depends(get_db)):
    products = db.query(models.Product).outerjoin(models.Store).order_by(models.Product.id.asc()).all()
    rows = []
    for p in products:
        rows.append({
            "id": p.id,
            "store_id": p.store_id,
            "store_name": p.store.name if p.store else "",
            "store_city": p.store.city if p.store else "",
            "store_address": p.store.address if p.store else "",
            "store_latitude": p.store.latitude if p.store else "",
            "store_longitude": p.store.longitude if p.store else "",
            "name": p.name,
            "category": p.category or "",
            "original_price": p.original_price or "",
            "discounted_price": p.discounted_price or "",
            "discount_percent": p.discount_percent or "",
            "currency": p.currency,
            "expiry_date": p.expiry_date or "",
            "expiry_type": p.expiry_type,
            "quantity": p.quantity if p.quantity is not None else "",
            "pickup_window": p.pickup_window or "",
            "image_url": p.image_url or "",
            "source_url": p.source_url or "",
            "confidence_score": p.confidence_score,
            "status": p.status,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        })
    return _csv_response("food_saver_products.csv", rows)


@router.get("/stores.csv", response_class=Response)
def export_stores_csv(db: Session = Depends(get_db)):
    stores = db.query(models.Store).order_by(models.Store.id.asc()).all()
    rows = []
    for s in stores:
        rows.append({
            "id": s.id,
            "name": s.name,
            "city": s.city or "",
            "address": s.address or "",
            "latitude": s.latitude or "",
            "longitude": s.longitude or "",
            "website": s.website or "",
            "phone": s.phone or "",
            "verified": s.verified,
            "created_at": s.created_at,
        })
    return _csv_response("food_saver_stores.csv", rows)


@router.get("/sources.csv", response_class=Response)
def export_sources_csv(db: Session = Depends(get_db)):
    sources = db.query(models.Source).order_by(models.Source.id.asc()).all()
    rows = []
    for s in sources:
        product_count = db.query(models.Product).filter(models.Product.source_url == s.url).count()
        rows.append({
            "id": s.id,
            "name": s.name,
            "url": s.url,
            "city": s.city or "",
            "source_type": s.source_type,
            "crawl_frequency": s.crawl_frequency,
            "active": s.active,
            "last_checked_at": s.last_checked_at or "",
            "products_found": product_count,
        })
    return _csv_response("food_saver_sources.csv", rows)


@router.get("/source-report", response_model=list[dict])
def source_report(db: Session = Depends(get_db)):
    sources = db.query(models.Source).order_by(models.Source.id.asc()).all()
    report = []
    for s in sources:
        product_count = db.query(models.Product).filter(models.Product.source_url == s.url).count()
        visible_count = db.query(models.Product).filter(
            models.Product.source_url == s.url,
            models.Product.status.in_(["public_discount", "seller_verified", "near_expiry"]),
        ).count()
        latest_job = db.query(models.CrawlJob).filter(models.CrawlJob.source_id == s.id).order_by(models.CrawlJob.id.desc()).first()
        report.append({
            "id": s.id,
            "name": s.name,
            "url": s.url,
            "source_type": s.source_type,
            "active": s.active,
            "last_checked_at": s.last_checked_at,
            "products_found": product_count,
            "visible_products": visible_count,
            "last_job_status": latest_job.status if latest_job else None,
            "last_job_items_found": latest_job.items_found if latest_job else None,
            "last_job_error": latest_job.error_message if latest_job else None,
        })
    return report


@router.get("/quality-report", response_model=dict)
def quality_report(db: Session = Depends(get_db)):
    total = db.query(models.Product).count()
    by_status_rows = db.query(models.Product.status, func.count(models.Product.id)).group_by(models.Product.status).all()
    by_category_rows = db.query(models.Product.category, func.count(models.Product.id)).group_by(models.Product.category).all()
    missing_price = db.query(models.Product).filter(models.Product.discounted_price.is_(None), models.Product.original_price.is_(None)).count()
    missing_category = db.query(models.Product).filter(models.Product.category.is_(None)).count()
    low_confidence = db.query(models.Product).filter(models.Product.confidence_score < 0.55).count()
    duplicate_preview = _find_duplicate_groups(db, limit_groups=20)
    return {
        "products_total": total,
        "by_status": {row[0] or "unknown": row[1] for row in by_status_rows},
        "by_category": {row[0] or "unknown": row[1] for row in by_category_rows},
        "missing_price_total": missing_price,
        "missing_category_total": missing_category,
        "low_confidence_total": low_confidence,
        "duplicate_groups_preview": duplicate_preview,
        "note": "Public crawler podaci su akcijski kandidati. Rok trajanja ostaje unknown dok prodavac ne potvrdi.",
    }


def _find_duplicate_groups(db: Session, limit_groups: int = 50) -> list[dict]:
    products = db.query(models.Product).filter(models.Product.status != "hidden").all()
    groups: dict[tuple, list[models.Product]] = defaultdict(list)
    for p in products:
        key = (p.store_id, _norm_key(p.name), _safe_price(p.discounted_price), p.source_url or "")
        if key[1]:
            groups[key].append(p)
    duplicates = []
    for key, items in groups.items():
        if len(items) < 2:
            continue
        items_sorted = sorted(items, key=lambda x: (x.confidence_score or 0, x.updated_at or x.created_at), reverse=True)
        duplicates.append({
            "store_id": key[0],
            "normalized_name": key[1],
            "discounted_price": key[2],
            "source_url": key[3],
            "keep_id": items_sorted[0].id,
            "duplicate_ids": [p.id for p in items_sorted[1:]],
            "count": len(items_sorted),
        })
    duplicates.sort(key=lambda x: x["count"], reverse=True)
    return duplicates[:limit_groups]


@router.post("/cleanup-duplicates", response_model=dict)
def cleanup_duplicates(
    dry_run: bool = Query(default=True),
    limit_groups: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    duplicate_groups = _find_duplicate_groups(db, limit_groups=limit_groups)
    duplicate_ids = [pid for group in duplicate_groups for pid in group["duplicate_ids"]]
    if not dry_run and duplicate_ids:
        db.query(models.Product).filter(models.Product.id.in_(duplicate_ids)).update({models.Product.status: "hidden"}, synchronize_session=False)
        db.commit()
    return {
        "dry_run": dry_run,
        "duplicate_groups": len(duplicate_groups),
        "products_to_hide": len(duplicate_ids),
        "duplicate_ids": duplicate_ids[:500],
        "groups": duplicate_groups[:50],
    }


@router.post("/hide-low-quality", response_model=dict)
def hide_low_quality(
    min_confidence: float = Query(default=0.45, ge=0, le=1),
    dry_run: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    query = db.query(models.Product).filter(
        models.Product.confidence_score < min_confidence,
        models.Product.status.in_(["candidate", "needs_review", "public_discount"]),
    )
    ids = [p.id for p in query.limit(1000).all()]
    if not dry_run and ids:
        db.query(models.Product).filter(models.Product.id.in_(ids)).update({models.Product.status: "hidden"}, synchronize_session=False)
        db.commit()
    return {"dry_run": dry_run, "min_confidence": min_confidence, "products_to_hide": len(ids), "product_ids": ids[:500]}


@router.post("/promote-discounts", response_model=dict)
def promote_discounts(
    min_confidence: float = Query(default=0.55, ge=0, le=1),
    db: Session = Depends(get_db),
):
    products = db.query(models.Product).filter(
        models.Product.status.in_(["candidate", "needs_review"]),
        models.Product.discounted_price.is_not(None),
        models.Product.confidence_score >= min_confidence,
    ).all()
    for p in products:
        p.status = "public_discount"
        p.updated_at = datetime.utcnow()
    db.commit()
    return {"promoted_to_public_discount": len(products), "min_confidence": min_confidence}


@router.post("/purge-pilot-data", response_model=dict)
def purge_pilot_data(
    request: Request,
    dry_run: bool = Query(default=True),
    _: bool = Depends(require_admin_session),
    db: Session = Depends(get_db),
):
    stores = db.query(models.Store).all()
    store_map = {store.id: store for store in stores}
    pilot_store_ids = {store.id for store in stores if _is_pilot_store(store)}

    products = db.query(models.Product).all()
    pilot_product_ids = {
        product.id
        for product in products
        if product.store_id in pilot_store_ids or _is_pilot_product(product, store_map.get(product.store_id))
    }

    customers = db.query(models.Customer).all()
    pilot_customer_ids = {customer.id for customer in customers if _is_pilot_customer(customer)}

    reservations = db.query(models.Reservation).all()
    pilot_reservation_ids = set()
    for reservation in reservations:
        if (
            reservation.product_id in pilot_product_ids
            or _is_pilot_reservation(reservation, None)
            or reservation.customer_phone in {customer.phone for customer in customers if customer.id in pilot_customer_ids}
        ):
            pilot_reservation_ids.add(reservation.id)

    sources = db.query(models.Source).all()
    pilot_source_ids = {source.id for source in sources if _is_pilot_source(source)}

    crawl_job_ids = {
        row.id
        for row in db.query(models.CrawlJob).filter(models.CrawlJob.source_id.in_(pilot_source_ids)).all()
    } if pilot_source_ids else set()

    invoice_ids = {
        row.id
        for row in db.query(finance_models.SellerInvoice).filter(finance_models.SellerInvoice.seller_id.in_(pilot_store_ids)).all()
    } if pilot_store_ids else set()

    payment_request_ids = {
        row.id
        for row in db.query(finance_models.SellerInvoicePaymentRequest).filter(
            or_(
                finance_models.SellerInvoicePaymentRequest.seller_id.in_(pilot_store_ids),
                finance_models.SellerInvoicePaymentRequest.seller_invoice_id.in_(invoice_ids),
            )
        ).all()
    } if pilot_store_ids or invoice_ids else set()

    payment_ids = {
        row.id
        for row in db.query(finance_models.SellerInvoicePayment).filter(
            or_(
                finance_models.SellerInvoicePayment.seller_id.in_(pilot_store_ids),
                finance_models.SellerInvoicePayment.seller_invoice_id.in_(invoice_ids),
            )
        ).all()
    } if pilot_store_ids or invoice_ids else set()

    invoice_line_ids = {
        row.id
        for row in db.query(finance_models.SellerInvoiceLine).filter(
            or_(
                finance_models.SellerInvoiceLine.invoice_id.in_(invoice_ids),
                finance_models.SellerInvoiceLine.order_id.in_(pilot_reservation_ids),
            )
        ).all()
    } if invoice_ids or pilot_reservation_ids else set()

    ledger_ids = {
        row.id
        for row in db.query(finance_models.SellerCommissionLedger).filter(
            or_(
                finance_models.SellerCommissionLedger.seller_id.in_(pilot_store_ids),
                finance_models.SellerCommissionLedger.order_id.in_(pilot_reservation_ids),
                finance_models.SellerCommissionLedger.invoice_id.in_(invoice_ids),
            )
        ).all()
    } if pilot_store_ids or pilot_reservation_ids or invoice_ids else set()

    reconciliation_ids = {
        row.id
        for row in db.query(finance_models.FinanceReconciliationException).filter(
            or_(
                finance_models.FinanceReconciliationException.seller_id.in_(pilot_store_ids),
                finance_models.FinanceReconciliationException.invoice_id.in_(invoice_ids),
            )
        ).all()
    } if pilot_store_ids or invoice_ids else set()

    webhook_ids = {
        row.id
        for row in db.query(finance_models.ProviderWebhookEvent).all()
        if _contains_pilot_marker(row.provider, row.event_type, row.provider_event_id)
        or _contains_pilot_url(row.payload_json)
    }

    audit_log_ids = {
        row.id
        for row in db.query(finance_models.FinanceAuditLog).all()
        if _contains_pilot_marker(row.action, row.entity_type, row.reason, row.before_json, row.after_json)
        or (
            row.entity_id in pilot_store_ids
            or row.entity_id in pilot_reservation_ids
            or row.entity_id in invoice_ids
            or row.entity_id in payment_ids
            or row.entity_id in payment_request_ids
        )
    }

    counts = {
        "stores": len(pilot_store_ids),
        "products": len(pilot_product_ids),
        "customers": len(pilot_customer_ids),
        "reservations": len(pilot_reservation_ids),
        "sources": len(pilot_source_ids),
        "crawl_jobs": len(crawl_job_ids),
        "seller_invoices": len(invoice_ids),
        "seller_invoice_lines": len(invoice_line_ids),
        "seller_invoice_payment_requests": len(payment_request_ids),
        "seller_invoice_payments": len(payment_ids),
        "seller_commission_ledger": len(ledger_ids),
        "finance_reconciliation_exceptions": len(reconciliation_ids),
        "provider_webhook_events": len(webhook_ids),
        "finance_audit_log": len(audit_log_ids),
    }
    samples = {
        "stores": [store.name for store in stores if store.id in pilot_store_ids][:10],
        "products": [product.name for product in products if product.id in pilot_product_ids][:10],
        "customers": [customer.name or customer.phone for customer in customers if customer.id in pilot_customer_ids][:10],
        "sources": [source.url for source in sources if source.id in pilot_source_ids][:10],
    }

    if dry_run:
        json_preview = {
            "growth_leads": _purge_pilot_rows("growth_leads.json", dry_run=True),
            "seller_discovery_runs": _purge_pilot_rows("seller_discovery_runs.json", dry_run=True),
            "customer_demand_requests": _purge_pilot_rows("customer_demand_requests.json", dry_run=True),
        }
        return {
            "ok": True,
            "dry_run": True,
            "counts": counts,
            "samples": samples,
            "json_preview": json_preview,
            "message": "Pronađeni su pilot/test/demo podaci za bezbedno čišćenje. Ništa još nije obrisano.",
        }

    if invoice_line_ids:
        db.query(finance_models.SellerInvoiceLine).filter(finance_models.SellerInvoiceLine.id.in_(invoice_line_ids)).delete(synchronize_session=False)
    if payment_request_ids:
        db.query(finance_models.SellerInvoicePaymentRequest).filter(finance_models.SellerInvoicePaymentRequest.id.in_(payment_request_ids)).delete(synchronize_session=False)
    if payment_ids:
        db.query(finance_models.SellerInvoicePayment).filter(finance_models.SellerInvoicePayment.id.in_(payment_ids)).delete(synchronize_session=False)
    if ledger_ids:
        db.query(finance_models.SellerCommissionLedger).filter(finance_models.SellerCommissionLedger.id.in_(ledger_ids)).delete(synchronize_session=False)
    if reconciliation_ids:
        db.query(finance_models.FinanceReconciliationException).filter(finance_models.FinanceReconciliationException.id.in_(reconciliation_ids)).delete(synchronize_session=False)
    if audit_log_ids:
        db.query(finance_models.FinanceAuditLog).filter(finance_models.FinanceAuditLog.id.in_(audit_log_ids)).delete(synchronize_session=False)
    if webhook_ids:
        db.query(finance_models.ProviderWebhookEvent).filter(finance_models.ProviderWebhookEvent.id.in_(webhook_ids)).delete(synchronize_session=False)
    if invoice_ids:
        db.query(finance_models.SellerInvoice).filter(finance_models.SellerInvoice.id.in_(invoice_ids)).delete(synchronize_session=False)
    if pilot_reservation_ids:
        db.query(models.Reservation).filter(models.Reservation.id.in_(pilot_reservation_ids)).delete(synchronize_session=False)
    if pilot_product_ids:
        db.query(models.Product).filter(models.Product.id.in_(pilot_product_ids)).delete(synchronize_session=False)
    if pilot_customer_ids:
        db.query(models.Customer).filter(models.Customer.id.in_(pilot_customer_ids)).delete(synchronize_session=False)
    if crawl_job_ids:
        db.query(models.CrawlJob).filter(models.CrawlJob.id.in_(crawl_job_ids)).delete(synchronize_session=False)
    if pilot_source_ids:
        db.query(models.Source).filter(models.Source.id.in_(pilot_source_ids)).delete(synchronize_session=False)
    if pilot_store_ids:
        db.query(models.Store).filter(models.Store.id.in_(pilot_store_ids)).delete(synchronize_session=False)
    db.commit()

    json_cleanup = {
        "growth_leads": _purge_pilot_rows("growth_leads.json", dry_run=False),
        "seller_discovery_runs": _purge_pilot_rows("seller_discovery_runs.json", dry_run=False),
        "customer_demand_requests": _purge_pilot_rows("customer_demand_requests.json", dry_run=False),
    }

    return {
        "ok": True,
        "dry_run": False,
        "counts": counts,
        "samples": samples,
        "json_cleanup": json_cleanup,
        "message": "Pilot/test/demo podaci su obrisani. Baza je očišćena i spremna za stvarne kupce i prodavce.",
    }
