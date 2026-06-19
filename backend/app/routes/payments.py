from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services.pricing import build_price_breakdown, apply_pricing_to_reservation, mark_paid, normalize_phone
from ..services.payment_providers import checkout_for_reservation, active_payment_provider
from .reservations import RESERVABLE_PRODUCT_STATUSES, _reservation_to_out, ACTIVE_RESERVATION_STATUSES

router = APIRouter(prefix="/payments", tags=["payments"])


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


@router.post("/quote", response_model=schemas.PaymentQuoteOut)
def payment_quote(payload: schemas.PaymentQuoteRequest, db: Session = Depends(get_db)):
    product = db.get(models.Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Artikal nije pronađen")
    if product.status not in RESERVABLE_PRODUCT_STATUSES:
        raise HTTPException(status_code=400, detail="Artikal nije dostupan za online plaćanje")
    available = _available_quantity(db, product)
    if available is not None and payload.quantity > available:
        raise HTTPException(status_code=400, detail=f"Nema dovoljno dostupne količine. Dostupno: {available}")
    return build_price_breakdown(db, product, payload.quantity, payload.customer_phone)


@router.post("/reservations/{reservation_code}/pay", response_model=schemas.ReservationOut)
def pay_reservation_demo(reservation_code: str, payload: schemas.PaymentPayRequest, db: Session = Depends(get_db)):
    reservation = db.query(models.Reservation).filter(
        models.Reservation.reservation_code == reservation_code.upper()
    ).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena")
    if reservation.status not in {"pending", "confirmed"}:
        raise HTTPException(status_code=400, detail="Ova rezervacija ne može da se plati")

    expected = normalize_phone(reservation.customer_phone)
    provided = normalize_phone(payload.customer_phone)
    if not provided or provided[-6:] != expected[-6:]:
        raise HTTPException(status_code=401, detail="Telefon se ne poklapa sa rezervacijom")

    apply_pricing_to_reservation(db, reservation)
    if reservation.payment_status != "paid":
        mark_paid(reservation, provider="demo", method=payload.payment_method)
    db.commit()
    db.refresh(reservation)
    return _reservation_to_out(reservation)


@router.post("/reservations/{reservation_code}/pay-on-pickup", response_model=schemas.ReservationOut)
def pay_on_pickup(reservation_code: str, payload: schemas.PaymentPayRequest, db: Session = Depends(get_db)):
    reservation = db.query(models.Reservation).filter(
        models.Reservation.reservation_code == reservation_code.upper()
    ).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena")
    if reservation.status not in {"pending", "confirmed"}:
        raise HTTPException(status_code=400, detail="Ova rezervacija ne može da se označi za plaćanje pri preuzimanju")

    expected = normalize_phone(reservation.customer_phone)
    provided = normalize_phone(payload.customer_phone)
    if not provided or provided[-6:] != expected[-6:]:
        raise HTTPException(status_code=401, detail="Telefon se ne poklapa sa rezervacijom")

    apply_pricing_to_reservation(db, reservation)
    reservation.payment_status = "pay_on_pickup"
    reservation.payment_provider = "pay_on_pickup"
    reservation.payment_method = "pay_on_pickup"
    reservation.payment_reference = reservation.payment_reference or f"PICKUP-{reservation.reservation_code}"
    # Ako kupac plaća prodavcu pri preuzimanju, platforma nije naplatila novac.
    # Provizija 25% se tada vodi kao dug prodavca prema platformi.
    reservation.seller_payout_status = "commission_due"
    reservation.seller_payout_note = "Kupac plaća prodavcu pri preuzimanju; platformsku proviziju prodavac duguje kroz periodični obračun."
    if reservation.status == "pending":
        reservation.status = "confirmed"
    db.commit()
    db.refresh(reservation)
    return _reservation_to_out(reservation)


@router.post("/paypal/ipn", include_in_schema=False)
async def paypal_ipn_stub(request: Request):
    # MVP placeholder: PayPal redirection works without storing card data.
    # Automatic verification is added later with PayPal IPN/webhooks credentials.
    body = await request.body()
    return {"ok": True, "received_bytes": len(body), "mode": "mvp_manual_confirmation"}


@router.get("/reservations/{reservation_code}/checkout", response_model=schemas.PaymentCheckoutOut)
def payment_checkout(reservation_code: str, db: Session = Depends(get_db)):
    reservation = db.query(models.Reservation).filter(
        models.Reservation.reservation_code == reservation_code.upper()
    ).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena")
    apply_pricing_to_reservation(db, reservation)
    data = checkout_for_reservation(reservation)
    if reservation.payment_status == "unpaid" and data.provider not in {"demo", "pay_on_pickup"} and data.provider_ready:
        reservation.payment_status = "payment_pending"
        reservation.payment_provider = data.provider
        reservation.payment_method = data.method
        reservation.payment_reference = reservation.payment_reference or reservation.reservation_code
        db.commit()
        db.refresh(reservation)
    return {
        "reservation_code": reservation.reservation_code,
        "provider": data.provider,
        "provider_ready": data.provider_ready,
        "method": data.method,
        "checkout_url": data.checkout_url,
        "reservation_url": data.reservation_url,
        "reservation_qr_url": data.reservation_qr_url,
        "payment_qr_url": data.payment_qr_url,
        "provider_redirect_url": data.provider_redirect_url,
        "instructions": data.instructions,
        "provider_message": data.provider_message,
        "ips_payload": data.ips_payload,
        "amount": float(reservation.payable_amount or 0),
        "currency": reservation.currency or "RSD",
        "provider_amount": data.provider_amount,
        "provider_currency": data.provider_currency,
        "can_pay_on_pickup": data.can_pay_on_pickup,
        "platform_fee_percent": float(reservation.platform_fee_percent or 25),
        "platform_fee_amount": float(reservation.platform_fee_amount or 0),
        "seller_net_amount": float(reservation.seller_net_amount or 0),
    }
