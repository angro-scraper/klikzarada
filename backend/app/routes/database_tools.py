from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models
from ..database import get_db

router = APIRouter(prefix="/database", tags=["database tools"])


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
