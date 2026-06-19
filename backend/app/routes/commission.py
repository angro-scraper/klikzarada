from __future__ import annotations

from datetime import datetime
from io import StringIO
import csv

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services.admin_auth import require_admin_session
from ..services.pricing import apply_pricing_to_reservation

router = APIRouter(prefix="/commission", tags=["commission"], dependencies=[Depends(require_admin_session)])

OPEN_COMMISSION_STATUSES = {"commission_due", "invoice_sent"}
PAID_COMMISSION_STATUS = "commission_paid"


def _money(value) -> float:
    return round(float(value or 0), 2)


def _reservation_row(reservation: models.Reservation) -> dict:
    product = reservation.product
    store = product.store if product else None
    return {
        "reservation_code": reservation.reservation_code,
        "store_id": store.id if store else None,
        "store_name": store.name if store else "Nepoznat partner",
        "customer_name": reservation.customer_name,
        "customer_phone": reservation.customer_phone,
        "payment_status": reservation.payment_status,
        "commission_status": reservation.seller_payout_status,
        "invoice_reference": reservation.seller_payout_reference,
        "gross_amount": _money(reservation.gross_amount),
        "payable_amount": _money(reservation.payable_amount),
        "platform_fee_amount": _money(reservation.platform_fee_amount),
        "seller_net_amount": _money(reservation.seller_net_amount),
        "created_at": reservation.created_at.isoformat() if reservation.created_at else None,
        "paid_at": reservation.paid_at.isoformat() if reservation.paid_at else None,
        "seller_payout_at": reservation.seller_payout_at.isoformat() if reservation.seller_payout_at else None,
    }


def _commission_query(db: Session):
    return db.query(models.Reservation).join(models.Product).join(models.Store).filter(
        models.Reservation.payment_status == "pay_on_pickup",
        models.Reservation.seller_payout_status.in_(OPEN_COMMISSION_STATUSES | {PAID_COMMISSION_STATUS}),
    )


@router.get("/summary", response_model=dict)
def commission_summary(db: Session = Depends(get_db)):
    open_q = _commission_query(db).filter(models.Reservation.seller_payout_status.in_(OPEN_COMMISSION_STATUSES))
    paid_q = _commission_query(db).filter(models.Reservation.seller_payout_status == PAID_COMMISSION_STATUS)
    invoice_sent_q = _commission_query(db).filter(models.Reservation.seller_payout_status == "invoice_sent")
    return {
        "open_count": open_q.count(),
        "open_amount": _money(open_q.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
        "invoice_sent_count": invoice_sent_q.count(),
        "invoice_sent_amount": _money(invoice_sent_q.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
        "paid_count": paid_q.count(),
        "paid_amount": _money(paid_q.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
        "model": "PayPal/online: platforma zadržava 25%. Plaćanje pri preuzimanju: prodavac duguje 25% kroz obračun.",
    }


@router.get("/sellers", response_model=list[dict])
def commission_sellers(db: Session = Depends(get_db)):
    stores = db.query(models.Store).order_by(models.Store.name.asc()).all()
    result = []
    for store in stores:
        q = db.query(models.Reservation).join(models.Product).filter(
            models.Product.store_id == store.id,
            models.Reservation.payment_status == "pay_on_pickup",
            models.Reservation.seller_payout_status.in_(OPEN_COMMISSION_STATUSES | {PAID_COMMISSION_STATUS}),
        )
        open_q = q.filter(models.Reservation.seller_payout_status.in_(OPEN_COMMISSION_STATUSES))
        invoice_sent_q = q.filter(models.Reservation.seller_payout_status == "invoice_sent")
        paid_q = q.filter(models.Reservation.seller_payout_status == PAID_COMMISSION_STATUS)
        if q.count() == 0:
            continue
        latest_ref = (
            q.filter(models.Reservation.seller_payout_reference.isnot(None))
            .order_by(models.Reservation.updated_at.desc())
            .first()
        )
        result.append({
            "store_id": store.id,
            "store_name": store.name,
            "city": store.city,
            "seller_pin": store.seller_pin,
            "open_count": open_q.count(),
            "open_amount": _money(open_q.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
            "invoice_sent_count": invoice_sent_q.count(),
            "invoice_sent_amount": _money(invoice_sent_q.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
            "paid_count": paid_q.count(),
            "paid_amount": _money(paid_q.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
            "latest_invoice_reference": latest_ref.seller_payout_reference if latest_ref else None,
        })
    return result


@router.get("/sellers/{store_id}/items", response_model=list[dict])
def commission_items(store_id: int, include_paid: bool = False, db: Session = Depends(get_db)):
    store = db.get(models.Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Partner nije pronađen")
    statuses = OPEN_COMMISSION_STATUSES | ({PAID_COMMISSION_STATUS} if include_paid else set())
    rows = db.query(models.Reservation).join(models.Product).filter(
        models.Product.store_id == store_id,
        models.Reservation.payment_status == "pay_on_pickup",
        models.Reservation.seller_payout_status.in_(statuses),
    ).order_by(models.Reservation.created_at.desc()).all()
    for r in rows:
        apply_pricing_to_reservation(db, r)
    db.commit()
    return [_reservation_row(r) for r in rows]


@router.post("/sellers/{store_id}/invoice", response_model=dict)
def create_commission_invoice(store_id: int, db: Session = Depends(get_db)):
    store = db.get(models.Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Partner nije pronađen")
    rows = db.query(models.Reservation).join(models.Product).filter(
        models.Product.store_id == store_id,
        models.Reservation.payment_status == "pay_on_pickup",
        models.Reservation.seller_payout_status == "commission_due",
    ).order_by(models.Reservation.created_at.asc()).all()
    if not rows:
        raise HTTPException(status_code=400, detail="Nema otvorene provizije za fakturisanje")
    for r in rows:
        apply_pricing_to_reservation(db, r)
    total = _money(sum(float(r.platform_fee_amount or 0) for r in rows))
    reference = f"SH-COM-{datetime.utcnow():%Y%m%d}-{store_id:04d}-{len(rows):02d}"
    note = f"Obračun provizije {reference}: {len(rows)} rezervacija, ukupno {total:.2f} RSD."
    for r in rows:
        r.seller_payout_status = "invoice_sent"
        r.seller_payout_reference = reference
        r.seller_payout_note = note
        r.updated_at = datetime.utcnow()
    db.commit()
    return {
        "invoice_reference": reference,
        "store_id": store.id,
        "store_name": store.name,
        "items_count": len(rows),
        "commission_total": total,
        "status": "invoice_sent",
        "message": "Obračun je kreiran i označen kao poslat partneru.",
    }


@router.patch("/invoices/{invoice_reference}/mark-paid", response_model=dict)
def mark_invoice_paid(invoice_reference: str, db: Session = Depends(get_db)):
    rows = db.query(models.Reservation).filter(
        models.Reservation.seller_payout_reference == invoice_reference,
        models.Reservation.seller_payout_status == "invoice_sent",
    ).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Obračun nije pronađen ili je već zatvoren")
    total = _money(sum(float(r.platform_fee_amount or 0) for r in rows))
    now = datetime.utcnow()
    for r in rows:
        r.seller_payout_status = PAID_COMMISSION_STATUS
        r.seller_payout_at = now
        r.seller_payout_note = ((r.seller_payout_note or "") + f"\nProvizija naplaćena {now:%Y-%m-%d %H:%M}.").strip()
        r.updated_at = now
    db.commit()
    return {
        "invoice_reference": invoice_reference,
        "items_count": len(rows),
        "commission_total": total,
        "status": PAID_COMMISSION_STATUS,
        "message": "Provizija je označena kao naplaćena.",
    }


@router.get("/export.csv")
def export_commission_csv(db: Session = Depends(get_db)):
    rows = _commission_query(db).order_by(models.Store.name.asc(), models.Reservation.created_at.desc()).all()
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=[
        "reservation_code", "store_id", "store_name", "customer_name", "customer_phone",
        "payment_status", "commission_status", "invoice_reference", "payable_amount",
        "platform_fee_amount", "seller_net_amount", "created_at", "seller_payout_at",
    ])
    writer.writeheader()
    for r in rows:
        data = _reservation_row(r)
        writer.writerow({k: data.get(k) for k in writer.fieldnames})
    buffer.seek(0)
    headers = {"Content-Disposition": "attachment; filename=sacuvaj-hranu-commission.csv"}
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)
