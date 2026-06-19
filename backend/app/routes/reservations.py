from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..services.pricing import apply_pricing_to_reservation, mark_refunded_if_paid
from ..services.notifications import customer_notifications_enabled, reservation_created_message, reservation_status_message, send_sms
from ..services.customers import (
    apply_reservation_status_transition,
    enforce_customer_block,
    find_customer_by_phone,
    get_or_create_customer,
    register_reservation_created,
    customer_to_public,
)

router = APIRouter(prefix="/reservations", tags=["reservations"])
ACTIVE_RESERVATION_STATUSES = ["pending", "confirmed"]
RESERVABLE_PRODUCT_STATUSES = ["public_discount", "seller_verified", "near_expiry"]


def _reservation_to_out(reservation: models.Reservation) -> dict:
    return {
        "id": reservation.id,
        "product_id": reservation.product_id,
        "product_name": reservation.product.name if reservation.product else None,
        "store_name": reservation.product.store.name if reservation.product and reservation.product.store else None,
        "customer_name": reservation.customer_name,
        "customer_phone": reservation.customer_phone,
        "customer_email": reservation.customer_email,
        "quantity": reservation.quantity,
        "status": reservation.status,
        "reservation_code": reservation.reservation_code,
        "note": reservation.note,
        "payment_status": getattr(reservation, "payment_status", "unpaid"),
        "payment_provider": getattr(reservation, "payment_provider", None),
        "payment_method": getattr(reservation, "payment_method", None),
        "payment_reference": getattr(reservation, "payment_reference", None),
        "currency": getattr(reservation, "currency", "RSD"),
        "gross_amount": float(getattr(reservation, "gross_amount", 0) or 0),
        "loyalty_discount_percent": float(getattr(reservation, "loyalty_discount_percent", 0) or 0),
        "loyalty_discount_amount": float(getattr(reservation, "loyalty_discount_amount", 0) or 0),
        "payable_amount": float(getattr(reservation, "payable_amount", 0) or 0),
        "platform_fee_percent": float(getattr(reservation, "platform_fee_percent", 25) or 25),
        "platform_fee_amount": float(getattr(reservation, "platform_fee_amount", 0) or 0),
        "seller_net_amount": float(getattr(reservation, "seller_net_amount", 0) or 0),
        "paid_at": getattr(reservation, "paid_at", None),
        "seller_payout_status": getattr(reservation, "seller_payout_status", "not_ready"),
        "seller_payout_reference": getattr(reservation, "seller_payout_reference", None),
        "seller_payout_note": getattr(reservation, "seller_payout_note", None),
        "seller_payout_at": getattr(reservation, "seller_payout_at", None),
        "seller_invoice_due_at": getattr(reservation, "seller_invoice_due_at", None),
        "created_at": reservation.created_at,
        "updated_at": reservation.updated_at,
    }


def _reserved_quantity(db: Session, product_id: int) -> int:
    value = db.query(func.coalesce(func.sum(models.Reservation.quantity), 0)).filter(
        models.Reservation.product_id == product_id,
        models.Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
    ).scalar()
    return int(value or 0)


def _available_quantity(db: Session, product: models.Product) -> int | None:
    if product.quantity is None:
        return None
    return max(product.quantity - _reserved_quantity(db, product.id), 0)


def _phone_digits(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _customer_reservation_to_out(reservation: models.Reservation) -> dict:
    data = _reservation_to_out(reservation)
    product = reservation.product
    store = product.store if product else None
    data.update({
        "store_id": store.id if store else None,
        "store_address": store.address if store else None,
        "store_city": store.city if store else None,
        "pickup_window": product.pickup_window if product else None,
        "ticket_url": f"/reservation?code={reservation.reservation_code}",
        "qr_url": f"/qr/reservation/{reservation.reservation_code}.svg",
        "checkout_url": f"/payments/reservations/{reservation.reservation_code}/checkout",
        "support_url": f"/podrska?code={reservation.reservation_code}",
        "can_cancel": reservation.status in {"pending", "confirmed"},
    })
    return data


@router.post("", response_model=schemas.ReservationOut)
def create_reservation(payload: schemas.ReservationCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    product = db.get(models.Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Artikal nije pronađen")
    if product.status not in RESERVABLE_PRODUCT_STATUSES:
        raise HTTPException(status_code=400, detail="Artikal trenutno nije dostupan za rezervaciju")

    available = _available_quantity(db, product)
    if available is not None and payload.quantity > available:
        raise HTTPException(status_code=400, detail=f"Nema dovoljno dostupne količine. Dostupno: {available}")

    try:
        customer = get_or_create_customer(
            db,
            name=payload.customer_name,
            phone=payload.customer_phone,
            email=payload.customer_email,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Unesi ispravan broj telefona")
    enforce_customer_block(customer)
    if customer.status == "blocked":
        raise HTTPException(
            status_code=403,
            detail="Korisnik je blokiran zbog 3 otkazivanja rezervacije. Kontaktiraj podršku za proveru naloga.",
        )

    reservation = models.Reservation(
        product_id=payload.product_id,
        customer_name=payload.customer_name.strip(),
        customer_phone=payload.customer_phone.strip(),
        customer_email=payload.customer_email.strip() if payload.customer_email else None,
        quantity=payload.quantity,
        note=payload.note,
        status="pending",
        payment_status="unpaid",
        reservation_code=uuid4().hex[:8].upper(),
    )
    db.add(reservation)
    db.flush()
    apply_pricing_to_reservation(db, reservation)
    register_reservation_created(db, reservation, customer)
    db.commit()
    db.refresh(reservation)
    if customer_notifications_enabled():
        # V52: send notification after response so reservation creation stays instant.
        background_tasks.add_task(
            send_sms,
            reservation.customer_phone,
            reservation_created_message(reservation.reservation_code, product.name, reservation.payable_amount),
            purpose="reservation_created",
            metadata={"reservation_code": reservation.reservation_code, "product_id": product.id},
        )
    return _reservation_to_out(reservation)


@router.get("", response_model=list[schemas.ReservationOut])
def list_reservations(
    status: str | None = None,
    product_id: int | None = None,
    store_id: int | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(models.Reservation).join(models.Product)
    if store_id:
        query = query.filter(models.Product.store_id == store_id)
    if status:
        query = query.filter(models.Reservation.status == status)
    if product_id:
        query = query.filter(models.Reservation.product_id == product_id)
    reservations = query.order_by(models.Reservation.created_at.desc()).limit(limit).all()
    return [_reservation_to_out(r) for r in reservations]


@router.get("/customer", response_model=dict)
def customer_reservations(phone: str, limit: int = 50, db: Session = Depends(get_db)):
    provided = _phone_digits(phone)
    if len(provided) < 5:
        raise HTTPException(status_code=400, detail="Unesi telefon sa najmanje 5 cifara")
    rows = db.query(models.Reservation).join(models.Product).order_by(models.Reservation.created_at.desc()).limit(500).all()
    matches = [
        r for r in rows
        if _phone_digits(r.customer_phone).endswith(provided[-6:]) or _phone_digits(r.customer_phone) == provided
    ][:limit]
    active = [r for r in matches if r.status in {"pending", "confirmed"}]
    picked_up = [r for r in matches if r.status == "picked_up"]
    cancelled = [r for r in matches if r.status == "cancelled"]
    total_saved = sum(max(0, (r.gross_amount or 0) - (r.payable_amount or 0)) for r in matches if r.status != "cancelled")
    total_paid = sum((r.payable_amount or 0) for r in matches if r.payment_status in {"paid", "pay_on_pickup"})
    customer = find_customer_by_phone(db, phone)
    return {
        "ok": True,
        "phone_tail": provided[-4:],
        "customer": customer_to_public(customer),
        "stats": {
            "total": len(matches),
            "active": len(active),
            "picked_up": len(picked_up),
            "cancelled": len(cancelled),
            "total_saved": round(float(total_saved or 0), 2),
            "total_paid_or_due": round(float(total_paid or 0), 2),
        },
        "reservations": [_customer_reservation_to_out(r) for r in matches],
    }


@router.patch("/{reservation_id}/status", response_model=schemas.ReservationOut)
def update_reservation_status(reservation_id: int, status: str, db: Session = Depends(get_db)):
    allowed = {"pending", "confirmed", "picked_up", "cancelled", "expired"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status mora biti jedan od: {', '.join(sorted(allowed))}")
    reservation = db.get(models.Reservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena")
    previous_status = reservation.status
    reservation.status = status
    if status in {"cancelled", "expired"}:
        mark_refunded_if_paid(reservation)
    apply_reservation_status_transition(db, reservation, previous_status, status)
    reservation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(reservation)
    if customer_notifications_enabled() and status in {"confirmed", "picked_up", "cancelled", "expired"}:
        try:
            send_sms(
                reservation.customer_phone,
                reservation_status_message(reservation.reservation_code, status),
                purpose="reservation_status",
                metadata={"reservation_code": reservation.reservation_code, "status": status},
            )
        except Exception:
            pass
    return _reservation_to_out(reservation)


@router.get("/code/{reservation_code}", response_model=schemas.ReservationOut)
def get_reservation_by_code(reservation_code: str, db: Session = Depends(get_db)):
    reservation = db.query(models.Reservation).filter(
        models.Reservation.reservation_code == reservation_code.upper()
    ).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena")
    return _reservation_to_out(reservation)


@router.patch("/code/{reservation_code}/cancel", response_model=schemas.ReservationOut)
def cancel_reservation_by_code(reservation_code: str, phone: str, db: Session = Depends(get_db)):
    reservation = db.query(models.Reservation).filter(
        models.Reservation.reservation_code == reservation_code.upper()
    ).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena")
    expected = ''.join(ch for ch in (reservation.customer_phone or '') if ch.isdigit())
    provided = ''.join(ch for ch in (phone or '') if ch.isdigit())
    if not provided or provided[-6:] != expected[-6:]:
        raise HTTPException(status_code=401, detail="Telefon se ne poklapa sa rezervacijom")
    if reservation.status not in {"pending", "confirmed"}:
        raise HTTPException(status_code=400, detail="Ova rezervacija više ne može da se otkaže")
    previous_status = reservation.status
    reservation.status = "cancelled"
    mark_refunded_if_paid(reservation)
    apply_reservation_status_transition(db, reservation, previous_status, "cancelled")
    reservation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(reservation)
    if customer_notifications_enabled():
        try:
            send_sms(
                reservation.customer_phone,
                reservation_status_message(reservation.reservation_code, "cancelled"),
                purpose="reservation_status",
                metadata={"reservation_code": reservation.reservation_code, "status": "cancelled", "source": "customer_cancel"},
            )
        except Exception:
            pass
    return _reservation_to_out(reservation)
