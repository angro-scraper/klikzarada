from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services.pricing import apply_pricing_to_reservation
from .reservations import _reservation_to_out, ACTIVE_RESERVATION_STATUSES

router = APIRouter(prefix="/flow", tags=["final-product-flow"])

VISIBLE_PRODUCT_STATUSES = ["public_discount", "seller_verified", "near_expiry"]


def _active_offer(db: Session) -> models.Product | None:
    return (
        db.query(models.Product)
        .outerjoin(models.Store)
        .filter(models.Product.status.in_(VISIBLE_PRODUCT_STATUSES))
        .filter(models.Product.quantity.is_(None) | (models.Product.quantity > 0))
        .order_by(models.Product.updated_at.desc())
        .first()
    )


def _ensure_demo_offer(db: Session) -> models.Product:
    offer = _active_offer(db)
    if offer and offer.store:
        return offer

    store = (
        db.query(models.Store)
        .filter(models.Store.name == "Sačuvaj Hranu Demo Partner")
        .first()
    )
    if not store:
        store = models.Store(
            name="Sačuvaj Hranu Demo Partner",
            city="Beograd",
            address="Vojvode Stepe 123, Beograd",
            latitude=44.7796,
            longitude=20.4786,
            website="https://example.com/sacuvaj-hranu-demo",
            phone="0601234567",
            seller_pin="123456",
            verified=True,
        )
        db.add(store)
        db.flush()

    product = (
        db.query(models.Product)
        .filter(models.Product.source_url == "seed://v57/final-product-flow-demo")
        .first()
    )
    if not product:
        product = models.Product(
            store_id=store.id,
            name="Domaći ručak — demo rezervacija",
            category="gotova jela",
            original_price=600,
            discounted_price=360,
            discount_percent=40,
            currency="RSD",
            expiry_date=date.today() + timedelta(days=1),
            expiry_type="use_by",
            quantity=12,
            pickup_window="danas 18:30–19:00",
            image_url="/admin-assets/seed-images/dnevni-meni.svg",
            source_url="seed://v57/final-product-flow-demo",
            confidence_score=0.98,
            status="seller_verified",
        )
        db.add(product)
    else:
        product.status = "seller_verified"
        product.quantity = max(product.quantity or 0, 12)
        product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)
    return product


def _sum_payable(query) -> float:
    return float(query.with_entities(func.coalesce(func.sum(models.Reservation.payable_amount), 0)).scalar() or 0)


@router.get("/status", response_model=dict)
def flow_status(db: Session = Depends(get_db)):
    active_products = db.query(models.Product).filter(models.Product.status.in_(VISIBLE_PRODUCT_STATUSES)).count()
    stores = db.query(models.Store).count()
    verified_stores = db.query(models.Store).filter(models.Store.verified.is_(True)).count()
    reservations = db.query(models.Reservation).count()
    pending = db.query(models.Reservation).filter(models.Reservation.status.in_(["pending", "confirmed"])).count()
    picked_up = db.query(models.Reservation).filter(models.Reservation.status == "picked_up").count()
    unpaid = db.query(models.Reservation).filter(models.Reservation.payment_status == "unpaid").count()
    paid = db.query(models.Reservation).filter(models.Reservation.payment_status.in_(["paid", "demo_paid"])).count()
    pay_on_pickup = db.query(models.Reservation).filter(models.Reservation.payment_status == "pay_on_pickup").count()
    commission_due_q = db.query(models.Reservation).filter(models.Reservation.seller_payout_status == "commission_due")
    commission_due_count = commission_due_q.count()
    commission_due_total = float(commission_due_q.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar() or 0)
    latest = db.query(models.Reservation).order_by(models.Reservation.created_at.desc()).first()

    flow_checks = [
        {"key": "offers", "label": "Kupac vidi ponude", "ok": active_products > 0, "detail": f"{active_products} aktivnih ponuda"},
        {"key": "stores", "label": "Postoje prodavci", "ok": stores > 0, "detail": f"{verified_stores}/{stores} verifikovanih"},
        {"key": "reservations", "label": "Rezervacije postoje", "ok": reservations > 0, "detail": f"{reservations} ukupno"},
        {"key": "payment", "label": "Plaćanje / plaćanje pri preuzimanju", "ok": (paid + pay_on_pickup) > 0, "detail": f"online/demo: {paid}, pri preuzimanju: {pay_on_pickup}"},
        {"key": "pickup", "label": "Preuzimanje potvrđeno", "ok": picked_up > 0, "detail": f"{picked_up} preuzimanja"},
        {"key": "commission", "label": "Provizija se evidentira", "ok": commission_due_count > 0 or paid > 0, "detail": f"za naplatu: {commission_due_total:.0f} RSD"},
    ]
    ready_percent = round(sum(1 for c in flow_checks if c["ok"]) / len(flow_checks) * 100)
    return {
        "ready_percent": ready_percent,
        "checks": flow_checks,
        "counts": {
            "active_products": active_products,
            "stores": stores,
            "verified_stores": verified_stores,
            "reservations": reservations,
            "pending_or_confirmed": pending,
            "unpaid": unpaid,
            "paid": paid,
            "pay_on_pickup": pay_on_pickup,
            "picked_up": picked_up,
            "commission_due_count": commission_due_count,
            "commission_due_total": commission_due_total,
            "turnover_total": _sum_payable(db.query(models.Reservation)),
        },
        "latest_reservation": _reservation_to_out(latest) if latest else None,
        "message": "End-to-end tok je spreman za pilot test" if ready_percent >= 80 else "Pokreni demo tok ili napravi test rezervaciju da proveriš ceo proces",
    }


@router.post("/demo-reservation", response_model=dict)
def create_demo_reservation(db: Session = Depends(get_db)):
    product = _ensure_demo_offer(db)
    code = uuid4().hex[:8].upper()
    reservation = models.Reservation(
        product_id=product.id,
        customer_name="Demo Kupac",
        customer_phone="0601234567",
        customer_email="demo@sacuvajhranu.rs",
        quantity=1,
        status="pending",
        payment_status="unpaid",
        reservation_code=code,
        note="V57 end-to-end demo rezervacija",
    )
    db.add(reservation)
    db.flush()
    apply_pricing_to_reservation(db, reservation)
    db.commit()
    db.refresh(reservation)
    store = product.store
    return {
        "ok": True,
        "message": "Demo rezervacija je kreirana. Sada testiraj checkout, digitalnu kartu i seller QR/preuzimanje.",
        "reservation": _reservation_to_out(reservation),
        "links": {
            "app": "/app",
            "checkout": f"/checkout?code={reservation.reservation_code}",
            "reservation": f"/reservation?code={reservation.reservation_code}",
            "seller": "/seller",
            "finance": "/finance",
            "command": "/command",
        },
        "seller_test": {
            "store_id": store.id if store else None,
            "store_name": store.name if store else None,
            "pin": store.seller_pin if store else None,
            "reservation_code": reservation.reservation_code,
        },
    }


@router.post("/demo-reservation/{reservation_code}/pay-on-pickup", response_model=dict)
def demo_pay_on_pickup(reservation_code: str, db: Session = Depends(get_db)):
    reservation = db.query(models.Reservation).filter(models.Reservation.reservation_code == reservation_code.upper()).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena")
    apply_pricing_to_reservation(db, reservation)
    reservation.payment_status = "pay_on_pickup"
    reservation.payment_provider = "pay_on_pickup"
    reservation.payment_method = "pay_on_pickup"
    reservation.payment_reference = reservation.payment_reference or f"PICKUP-{reservation.reservation_code}"
    reservation.seller_payout_status = "commission_due"
    reservation.seller_payout_note = "Kupac plaća prodavcu pri preuzimanju; platformsku proviziju prodavac duguje kroz periodični obračun."
    reservation.status = "confirmed"
    db.commit()
    db.refresh(reservation)
    return {"ok": True, "message": "Rezervacija je podešena na plaćanje pri preuzimanju.", "reservation": _reservation_to_out(reservation)}


@router.post("/demo-reservation/{reservation_code}/picked-up", response_model=dict)
def demo_mark_picked_up(reservation_code: str, db: Session = Depends(get_db)):
    reservation = db.query(models.Reservation).filter(models.Reservation.reservation_code == reservation_code.upper()).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena")
    if reservation.status not in ACTIVE_RESERVATION_STATUSES:
        raise HTTPException(status_code=400, detail="Rezervacija nije u statusu koji može da se preuzme")
    reservation.status = "picked_up"
    if reservation.payment_status == "pay_on_pickup":
        reservation.seller_payout_status = "commission_due"
    elif reservation.payment_status in {"paid", "demo_paid"}:
        reservation.seller_payout_status = "ready"
    reservation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(reservation)
    return {"ok": True, "message": "Preuzimanje je potvrđeno. Proveri finance/proviziju.", "reservation": _reservation_to_out(reservation)}
