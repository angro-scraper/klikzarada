from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services.pricing import apply_pricing_to_reservation, mark_paid
from ..services.admin_auth import require_admin_session
from .reservations import _reservation_to_out

router = APIRouter(prefix="/finance", tags=["finance"], dependencies=[Depends(require_admin_session)])

PAID_PAYMENT_STATUSES = {"paid"}
PAYOUT_STATUSES = {"not_ready", "pending", "paid", "blocked", "commission_due", "invoice_sent", "commission_paid"}


def _money(value) -> float:
    return round(float(value or 0), 2)


def _base_paid_query(db: Session):
    return db.query(models.Reservation).join(models.Product).filter(models.Reservation.payment_status == "paid")


@router.get("/summary", response_model=dict)
def finance_summary(db: Session = Depends(get_db)):
    total_reservations = db.query(models.Reservation).count()
    paid_q = db.query(models.Reservation).filter(models.Reservation.payment_status == "paid")
    pending_q = db.query(models.Reservation).filter(models.Reservation.payment_status == "payment_pending")
    refunded_q = db.query(models.Reservation).filter(models.Reservation.payment_status == "refunded")
    pickup_q = db.query(models.Reservation).filter(models.Reservation.payment_status == "pay_on_pickup")
    commission_due_q = pickup_q.filter(models.Reservation.seller_payout_status == "commission_due")

    payout_pending = paid_q.filter(models.Reservation.seller_payout_status == "pending")
    payout_paid = paid_q.filter(models.Reservation.seller_payout_status == "paid")
    payout_blocked = db.query(models.Reservation).filter(models.Reservation.seller_payout_status == "blocked")

    by_payment_status = dict(
        db.query(models.Reservation.payment_status, func.count(models.Reservation.id))
        .group_by(models.Reservation.payment_status).all()
    )
    by_payout_status = dict(
        db.query(models.Reservation.seller_payout_status, func.count(models.Reservation.id))
        .group_by(models.Reservation.seller_payout_status).all()
    )

    return {
        "reservations_total": total_reservations,
        "paid_count": paid_q.count(),
        "payment_pending_count": pending_q.count(),
        "refunded_count": refunded_q.count(),
        "paid_turnover": _money(paid_q.with_entities(func.coalesce(func.sum(models.Reservation.payable_amount), 0)).scalar()),
        "platform_fee_total": _money(paid_q.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
        "seller_net_total": _money(paid_q.with_entities(func.coalesce(func.sum(models.Reservation.seller_net_amount), 0)).scalar()),
        "pay_on_pickup_count": pickup_q.count(),
        "pay_on_pickup_turnover": _money(pickup_q.with_entities(func.coalesce(func.sum(models.Reservation.payable_amount), 0)).scalar()),
        "commission_due_count": commission_due_q.count(),
        "commission_due_total": _money(commission_due_q.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
        "pending_payout_count": payout_pending.count(),
        "pending_payout_amount": _money(payout_pending.with_entities(func.coalesce(func.sum(models.Reservation.seller_net_amount), 0)).scalar()),
        "paid_payout_count": payout_paid.count(),
        "paid_payout_amount": _money(payout_paid.with_entities(func.coalesce(func.sum(models.Reservation.seller_net_amount), 0)).scalar()),
        "blocked_payout_count": payout_blocked.count(),
        "by_payment_status": by_payment_status,
        "by_payout_status": by_payout_status,
    }


@router.get("/seller-settlements", response_model=list[dict])
def seller_settlements(db: Session = Depends(get_db)):
    stores = db.query(models.Store).order_by(models.Store.name.asc()).all()
    result = []
    for store in stores:
        q = db.query(models.Reservation).join(models.Product).filter(models.Product.store_id == store.id)
        paid = q.filter(models.Reservation.payment_status == "paid")
        pending_payout = paid.filter(models.Reservation.seller_payout_status == "pending")
        paid_payout = paid.filter(models.Reservation.seller_payout_status == "paid")
        blocked_payout = q.filter(models.Reservation.seller_payout_status == "blocked")
        commission_due = q.filter(models.Reservation.seller_payout_status == "commission_due")
        if q.count() == 0 and not store.verified:
            continue
        result.append({
            "store_id": store.id,
            "store_name": store.name,
            "city": store.city,
            "reservations_total": q.count(),
            "paid_count": paid.count(),
            "paid_turnover": _money(paid.with_entities(func.coalesce(func.sum(models.Reservation.payable_amount), 0)).scalar()),
            "platform_fee_total": _money(paid.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
            "seller_net_total": _money(paid.with_entities(func.coalesce(func.sum(models.Reservation.seller_net_amount), 0)).scalar()),
            "pending_payout_count": pending_payout.count(),
            "pending_payout_amount": _money(pending_payout.with_entities(func.coalesce(func.sum(models.Reservation.seller_net_amount), 0)).scalar()),
            "paid_payout_count": paid_payout.count(),
            "paid_payout_amount": _money(paid_payout.with_entities(func.coalesce(func.sum(models.Reservation.seller_net_amount), 0)).scalar()),
            "blocked_payout_count": blocked_payout.count(),
            "commission_due_count": commission_due.count(),
            "commission_due_total": _money(commission_due.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
        })
    return result


def _closeout_rows(db: Session) -> list[dict]:
    stores = db.query(models.Store).order_by(models.Store.name.asc()).all()
    rows = []
    for store in stores:
        q = db.query(models.Reservation).join(models.Product).filter(models.Product.store_id == store.id)
        if q.count() == 0 and not store.verified:
            continue
        paid = q.filter(models.Reservation.payment_status == "paid")
        pickup = q.filter(models.Reservation.payment_status == "pay_on_pickup")
        commission_due = q.filter(models.Reservation.seller_payout_status == "commission_due")
        invoice_sent = q.filter(models.Reservation.seller_payout_status == "invoice_sent")
        commission_paid = q.filter(models.Reservation.seller_payout_status == "commission_paid")
        pending_payout = paid.filter(models.Reservation.seller_payout_status == "pending")
        rows.append({
            "store_id": store.id,
            "store_name": store.name,
            "city": store.city,
            "reservations_total": q.count(),
            "picked_up": q.filter(models.Reservation.status == "picked_up").count(),
            "paid_turnover": _money(paid.with_entities(func.coalesce(func.sum(models.Reservation.payable_amount), 0)).scalar()),
            "pay_on_pickup_turnover": _money(pickup.with_entities(func.coalesce(func.sum(models.Reservation.payable_amount), 0)).scalar()),
            "platform_fee_paid": _money(paid.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
            "commission_due": _money(commission_due.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
            "commission_due_count": commission_due.count(),
            "invoice_sent": _money(invoice_sent.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
            "commission_paid": _money(commission_paid.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
            "seller_payout_pending": _money(pending_payout.with_entities(func.coalesce(func.sum(models.Reservation.seller_net_amount), 0)).scalar()),
        })
    return rows


@router.get("/live-closeout", response_model=dict)
def finance_live_closeout(db: Session = Depends(get_db)):
    rows = _closeout_rows(db)
    totals = {
        "reservations_total": sum(r["reservations_total"] for r in rows),
        "picked_up": sum(r["picked_up"] for r in rows),
        "paid_turnover": _money(sum(r["paid_turnover"] for r in rows)),
        "pay_on_pickup_turnover": _money(sum(r["pay_on_pickup_turnover"] for r in rows)),
        "platform_fee_paid": _money(sum(r["platform_fee_paid"] for r in rows)),
        "commission_due": _money(sum(r["commission_due"] for r in rows)),
        "invoice_sent": _money(sum(r["invoice_sent"] for r in rows)),
        "commission_paid": _money(sum(r["commission_paid"] for r in rows)),
        "seller_payout_pending": _money(sum(r["seller_payout_pending"] for r in rows)),
    }
    actions = []
    if totals["commission_due"] > 0:
        actions.append("Pošalji dnevni obračun provizije partnerima sa commission_due iznosom.")
    if totals["seller_payout_pending"] > 0:
        actions.append("Proveri plaćene rezervacije i pripremi isplatu partnerima.")
    if not actions:
        actions.append("Finansijski closeout nema otvorenih kritičnih stavki.")
    return {
        "ok": True,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "totals": totals,
        "partners": rows,
        "actions": actions,
        "csv": "/finance/live-closeout.csv",
    }


@router.get("/live-closeout.csv")
def finance_live_closeout_csv(db: Session = Depends(get_db)):
    rows = _closeout_rows(db)
    header = [
        "store_id", "store_name", "city", "reservations_total", "picked_up",
        "paid_turnover", "pay_on_pickup_turnover", "platform_fee_paid",
        "commission_due", "commission_due_count", "invoice_sent",
        "commission_paid", "seller_payout_pending",
    ]
    lines = [",".join(header)]
    for row in rows:
        values = [str(row.get(key, "")).replace('"', '""') for key in header]
        lines.append(",".join(f'"{value}"' if "," in value else value for value in values))
    return Response("\n".join(lines) + "\n", media_type="text/csv; charset=utf-8")


@router.patch("/stores/{store_id}/commission-sent", response_model=dict)
def mark_store_commission_sent(store_id: int, reference: str | None = None, db: Session = Depends(get_db)):
    store = db.get(models.Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Partner nije pronađen")
    reservations = db.query(models.Reservation).join(models.Product).filter(
        models.Product.store_id == store_id,
        models.Reservation.seller_payout_status == "commission_due",
    ).all()
    total = 0.0
    for reservation in reservations:
        total += float(reservation.platform_fee_amount or 0)
        reservation.seller_payout_status = "invoice_sent"
        reservation.seller_payout_reference = reference or f"COMMISSION-{store_id}-{datetime.utcnow().strftime('%Y%m%d')}"
        reservation.seller_payout_note = "Dnevni obračun provizije je poslat partneru."
        reservation.updated_at = datetime.utcnow()
    db.commit()
    return {
        "ok": True,
        "store_id": store_id,
        "store_name": store.name,
        "updated_reservations": len(reservations),
        "commission_marked_sent": _money(total),
    }


@router.get("/reservations", response_model=list[schemas.ReservationOut])
def finance_reservations(
    payment_status: str | None = None,
    payout_status: str | None = None,
    store_id: int | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    query = db.query(models.Reservation).join(models.Product)
    if payment_status:
        query = query.filter(models.Reservation.payment_status == payment_status)
    if payout_status:
        query = query.filter(models.Reservation.seller_payout_status == payout_status)
    if store_id:
        query = query.filter(models.Product.store_id == store_id)
    reservations = query.order_by(models.Reservation.created_at.desc()).limit(limit).all()
    return [_reservation_to_out(r) for r in reservations]


@router.patch("/reservations/{reservation_code}/confirm-ips", response_model=schemas.ReservationOut)
def confirm_ips_payment(reservation_code: str, payload: schemas.FinanceConfirmPaymentRequest, db: Session = Depends(get_db)):
    reservation = db.query(models.Reservation).filter(models.Reservation.reservation_code == reservation_code.upper()).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena")
    if reservation.status in {"cancelled", "expired"}:
        raise HTTPException(status_code=400, detail="Otkazana ili istekla rezervacija ne može da se potvrdi kao plaćena")
    apply_pricing_to_reservation(db, reservation)
    if reservation.payment_status != "paid":
        mark_paid(reservation, provider=payload.provider or "ips_qr", method="IPS QR / ručna potvrda")
    if payload.reference:
        reservation.payment_reference = payload.reference.strip()
    elif not reservation.payment_reference:
        reservation.payment_reference = f"IPS-{reservation.reservation_code}"
    if payload.note:
        reservation.note = ((reservation.note or "") + f"\n[FINANCE] {payload.note.strip()}").strip()
    reservation.seller_payout_status = "pending"
    reservation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(reservation)
    return _reservation_to_out(reservation)


@router.patch("/reservations/{reservation_code}/payout", response_model=schemas.ReservationOut)
def update_seller_payout(reservation_code: str, payload: schemas.FinancePayoutUpdateRequest, db: Session = Depends(get_db)):
    reservation = db.query(models.Reservation).filter(models.Reservation.reservation_code == reservation_code.upper()).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena")
    if reservation.payment_status != "paid" and payload.seller_payout_status == "paid":
        raise HTTPException(status_code=400, detail="Ne može isplata prodavcu dok rezervacija nije plaćena")
    reservation.seller_payout_status = payload.seller_payout_status
    reservation.seller_payout_reference = payload.reference.strip() if payload.reference else reservation.seller_payout_reference
    reservation.seller_payout_note = payload.note.strip() if payload.note else reservation.seller_payout_note
    if payload.seller_payout_status == "paid":
        reservation.seller_payout_at = datetime.utcnow()
    elif payload.seller_payout_status in {"pending", "blocked", "not_ready", "commission_due", "invoice_sent"}:
        reservation.seller_payout_at = None
    reservation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(reservation)
    return _reservation_to_out(reservation)
