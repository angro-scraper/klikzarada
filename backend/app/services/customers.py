from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy.orm import Session

from .. import models
from .pricing import normalize_phone

CUSTOMER_CANCEL_BLOCK_THRESHOLD = int(os.getenv("CUSTOMER_CANCEL_BLOCK_THRESHOLD", "3"))
CANCELLATION_STATUSES = {"cancelled", "cancelled_by_customer", "cancelled_by_seller"}
COMPLETED_STATUSES = {"picked_up"}
BLOCK_REASON = f"Automatska blokada: {CUSTOMER_CANCEL_BLOCK_THRESHOLD} otkazivanja rezervacije."


def customer_phone_digits(phone: str | None) -> str:
    return normalize_phone(phone or "")


def customer_to_public(customer: models.Customer | None) -> dict | None:
    if not customer:
        return None
    return {
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone,
        "phone_tail": customer.phone_digits[-4:] if customer.phone_digits else None,
        "email": customer.email,
        "status": customer.status,
        "is_blocked": customer.status == "blocked",
        "total_reservations": int(customer.total_reservations or 0),
        "cancelled_reservations": int(customer.cancelled_reservations or 0),
        "completed_reservations": int(customer.completed_reservations or 0),
        "cancel_block_threshold": CUSTOMER_CANCEL_BLOCK_THRESHOLD,
        "remaining_cancellations_before_block": max(
            CUSTOMER_CANCEL_BLOCK_THRESHOLD - int(customer.cancelled_reservations or 0),
            0,
        ),
        "blocked_at": customer.blocked_at.isoformat() if customer.blocked_at else None,
        "block_reason": customer.block_reason,
        "last_reservation_at": customer.last_reservation_at.isoformat() if customer.last_reservation_at else None,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
        "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
    }


def find_customer_by_phone(db: Session, phone: str | None) -> models.Customer | None:
    digits = customer_phone_digits(phone)
    if len(digits) < 5:
        return None
    return db.query(models.Customer).filter(models.Customer.phone_digits == digits).first()


def get_or_create_customer(
    db: Session,
    *,
    name: str | None,
    phone: str,
    email: str | None = None,
) -> models.Customer:
    digits = customer_phone_digits(phone)
    if len(digits) < 5:
        raise ValueError("Telefon mora imati najmanje 5 cifara")
    customer = db.query(models.Customer).filter(models.Customer.phone_digits == digits).first()
    now = datetime.utcnow()
    clean_name = (name or "").strip() or None
    clean_email = (email or "").strip() or None
    clean_phone = (phone or "").strip()
    if not customer:
        customer = models.Customer(
            name=clean_name,
            phone=clean_phone,
            phone_digits=digits,
            email=clean_email,
            status="active",
            created_at=now,
            updated_at=now,
        )
        db.add(customer)
        db.flush()
        return customer
    if clean_name:
        customer.name = clean_name
    if clean_phone:
        customer.phone = clean_phone
    if clean_email:
        customer.email = clean_email
    customer.updated_at = now
    return customer


def enforce_customer_block(customer: models.Customer) -> models.Customer:
    if int(customer.cancelled_reservations or 0) >= CUSTOMER_CANCEL_BLOCK_THRESHOLD:
        customer.status = "blocked"
        if not customer.blocked_at:
            customer.blocked_at = datetime.utcnow()
        customer.block_reason = BLOCK_REASON
    return customer


def register_reservation_created(
    db: Session,
    reservation: models.Reservation,
    customer: models.Customer | None = None,
) -> models.Customer:
    customer = customer or get_or_create_customer(
        db,
        name=reservation.customer_name,
        phone=reservation.customer_phone,
        email=reservation.customer_email,
    )
    customer.total_reservations = int(customer.total_reservations or 0) + 1
    customer.last_reservation_at = reservation.created_at or datetime.utcnow()
    customer.updated_at = datetime.utcnow()
    enforce_customer_block(customer)
    return customer


def apply_reservation_status_transition(
    db: Session,
    reservation: models.Reservation,
    previous_status: str | None,
    new_status: str | None,
) -> models.Customer | None:
    if not new_status or previous_status == new_status:
        return None
    customer = get_or_create_customer(
        db,
        name=reservation.customer_name,
        phone=reservation.customer_phone,
        email=reservation.customer_email,
    )
    if new_status in CANCELLATION_STATUSES and previous_status not in CANCELLATION_STATUSES:
        customer.cancelled_reservations = int(customer.cancelled_reservations or 0) + 1
    if new_status in COMPLETED_STATUSES and previous_status not in COMPLETED_STATUSES:
        customer.completed_reservations = int(customer.completed_reservations or 0) + 1
    customer.updated_at = datetime.utcnow()
    enforce_customer_block(customer)
    return customer


def rebuild_customer_database(db: Session) -> dict:
    customers = db.query(models.Customer).all()
    for customer in customers:
        customer.total_reservations = 0
        customer.cancelled_reservations = 0
        customer.completed_reservations = 0
        customer.last_reservation_at = None
        if customer.status == "blocked" and customer.block_reason == BLOCK_REASON:
            customer.status = "active"
            customer.blocked_at = None
            customer.block_reason = None

    reservations = db.query(models.Reservation).order_by(models.Reservation.created_at.asc()).all()
    for reservation in reservations:
        customer = get_or_create_customer(
            db,
            name=reservation.customer_name,
            phone=reservation.customer_phone,
            email=reservation.customer_email,
        )
        customer.total_reservations = int(customer.total_reservations or 0) + 1
        if reservation.status in CANCELLATION_STATUSES:
            customer.cancelled_reservations = int(customer.cancelled_reservations or 0) + 1
        if reservation.status in COMPLETED_STATUSES:
            customer.completed_reservations = int(customer.completed_reservations or 0) + 1
        created_at = reservation.created_at or datetime.utcnow()
        if not customer.last_reservation_at or created_at > customer.last_reservation_at:
            customer.last_reservation_at = created_at
        customer.updated_at = datetime.utcnow()
        enforce_customer_block(customer)

    db.commit()
    total_customers = db.query(models.Customer).count()
    blocked_customers = db.query(models.Customer).filter(models.Customer.status == "blocked").count()
    return {
        "ok": True,
        "customers_total": int(total_customers or 0),
        "blocked_customers": int(blocked_customers or 0),
        "reservations_scanned": len(reservations),
        "cancel_block_threshold": CUSTOMER_CANCEL_BLOCK_THRESHOLD,
        "message": "Korisnička baza je obnovljena iz rezervacija.",
    }
