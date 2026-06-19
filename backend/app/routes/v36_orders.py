
from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..routes.reservations import _reservation_to_out
from ..services.admin_auth import require_admin_session
from ..services.json_store import append_json_row, read_json, update_json_row
from ..services.pricing import mark_refunded_if_paid, normalize_phone
from ..services.notifications import send_sms, customer_notifications_enabled, reservation_status_message

router = APIRouter(prefix="/order-workflow", tags=["v36-order-workflow"])

ORDER_STATUSES = {
    "reserved", "awaiting_payment", "paid", "confirmed_by_seller", "ready_for_pickup", "picked_up",
    "no_show", "cancelled_by_customer", "cancelled_by_seller", "refunded", "expired", "pending", "confirmed", "cancelled",
}

class OrderStatusUpdate(BaseModel):
    status: str = Field(..., max_length=80)
    note: str | None = Field(default=None, max_length=1000)

class RefundRequestCreate(BaseModel):
    reservation_code: str = Field(..., min_length=4, max_length=40)
    phone: str = Field(..., min_length=5, max_length=80)
    reason: str = Field(..., min_length=5, max_length=2000)

class RefundUpdate(BaseModel):
    status: str = Field(..., pattern="^(open|review|approved|rejected|paid|closed)$")
    admin_note: str | None = Field(default=None, max_length=2000)


def _find_reservation(db: Session, code: str) -> models.Reservation:
    reservation = db.query(models.Reservation).filter(models.Reservation.reservation_code == code.upper()).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena")
    return reservation

@router.patch("/reservation/{reservation_code}/status", response_model=dict)
def update_order_status(reservation_code: str, payload: OrderStatusUpdate, request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    if payload.status not in ORDER_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status nije podržan. Dozvoljeno: {', '.join(sorted(ORDER_STATUSES))}")
    reservation = _find_reservation(db, reservation_code)
    reservation.status = payload.status
    if payload.status in {"cancelled", "cancelled_by_customer", "cancelled_by_seller", "refunded", "expired"}:
        mark_refunded_if_paid(reservation)
    if payload.note:
        reservation.note = ((reservation.note or "") + f"\n[STATUS] {payload.note.strip()}").strip()
    reservation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(reservation)
    if customer_notifications_enabled():
        try:
            send_sms(reservation.customer_phone, reservation_status_message(reservation.reservation_code, payload.status), purpose="order_workflow_status", metadata={"reservation_code": reservation.reservation_code, "status": payload.status})
        except Exception:
            pass
    return {"ok": True, "reservation": _reservation_to_out(reservation)}

@router.post("/refund-requests", response_model=dict)
def create_refund_request(payload: RefundRequestCreate, db: Session = Depends(get_db)):
    reservation = _find_reservation(db, payload.reservation_code)
    expected = normalize_phone(reservation.customer_phone)
    provided = normalize_phone(payload.phone)
    if not provided or not expected.endswith(provided[-6:]):
        raise HTTPException(status_code=401, detail="Telefon se ne poklapa sa rezervacijom")
    row = append_json_row("refund_requests.json", {
        "reservation_code": reservation.reservation_code,
        "phone": provided,
        "reason": payload.reason.strip(),
        "status": "open",
        "admin_note": None,
        "payment_status": reservation.payment_status,
        "amount": float(reservation.payable_amount or 0),
    })
    return {"ok": True, "refund_request": row, "message": "Zahtev je primljen. Podrška će proveriti rezervaciju."}

@router.get("/refund-requests", response_model=list[dict])
def list_refund_requests(request: Request, status: str | None = None, limit: int = Query(default=200, ge=1, le=1000), _: bool = Depends(require_admin_session)):
    rows = list(reversed(read_json("refund_requests.json", [])))
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return rows[:limit]

@router.patch("/refund-requests/{request_id}", response_model=dict)
def update_refund_request(request_id: str, payload: RefundUpdate, request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    updated = update_json_row("refund_requests.json", request_id, payload.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Zahtev nije pronađen")
    if payload.status in {"approved", "paid"}:
        reservation = db.query(models.Reservation).filter(models.Reservation.reservation_code == str(updated.get("reservation_code", "")).upper()).first()
        if reservation:
            mark_refunded_if_paid(reservation)
            reservation.status = "refunded" if payload.status == "paid" else reservation.status
            reservation.updated_at = datetime.utcnow()
            db.commit()
    return {"ok": True, "refund_request": updated}
