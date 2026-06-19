from __future__ import annotations

from datetime import datetime
import os
from uuid import uuid4
from sqlalchemy.orm import Session

from .. import models

PLATFORM_FEE_PERCENT = 25.0


def platform_fee_percent() -> float:
    try:
        return float(os.getenv("PLATFORM_COMMISSION_PERCENT", str(PLATFORM_FEE_PERCENT)))
    except Exception:
        return PLATFORM_FEE_PERCENT


def normalize_phone(phone: str | None) -> str:
    return ''.join(ch for ch in str(phone or '') if ch.isdigit())


def loyalty_percent_for_completed_pickups(count: int) -> float:
    """Loyalty popust za stalne kupce: 1–5% na osnovu ranijih uspešnih preuzimanja."""
    if count >= 20:
        return 5.0
    if count >= 10:
        return 4.0
    if count >= 5:
        return 3.0
    if count >= 3:
        return 2.0
    if count >= 1:
        return 1.0
    return 0.0


def successful_pickups_count(db: Session, customer_phone: str | None) -> int:
    normalized = normalize_phone(customer_phone)
    if len(normalized) < 5:
        return 0
    suffix = normalized[-6:]
    count = 0
    reservations = db.query(models.Reservation).filter(models.Reservation.status == "picked_up").all()
    for r in reservations:
        if normalize_phone(r.customer_phone).endswith(suffix):
            count += 1
    return count


def unit_price_for_product(product: models.Product) -> float:
    if product.discounted_price is not None:
        return float(product.discounted_price)
    if product.original_price is not None:
        return float(product.original_price)
    return 0.0


def build_price_breakdown(db: Session, product: models.Product, quantity: int, customer_phone: str | None) -> dict:
    qty = max(int(quantity or 1), 1)
    currency = product.currency or "RSD"
    gross = round(unit_price_for_product(product) * qty, 2)
    previous = successful_pickups_count(db, customer_phone)
    loyalty_percent = loyalty_percent_for_completed_pickups(previous)
    loyalty_discount = round(gross * loyalty_percent / 100, 2)
    payable = round(max(gross - loyalty_discount, 0), 2)
    fee_percent = platform_fee_percent()
    fee = round(payable * fee_percent / 100, 2)
    seller_net = round(max(payable - fee, 0), 2)
    message = (
        f"Popust za stalne kupce: {loyalty_percent:.0f}%" if loyalty_percent > 0
        else "Popust za stalne kupce kreće od 1% nakon prve uspešno preuzete rezervacije."
    )
    return {
        "product_id": product.id,
        "quantity": qty,
        "currency": currency,
        "gross_amount": gross,
        "loyalty_discount_percent": loyalty_percent,
        "loyalty_discount_amount": loyalty_discount,
        "payable_amount": payable,
        "platform_fee_percent": fee_percent,
        "platform_fee_amount": fee,
        "seller_net_amount": seller_net,
        "previous_successful_pickups": previous,
        "message": message,
    }


def apply_pricing_to_reservation(db: Session, reservation: models.Reservation) -> dict:
    product = reservation.product or db.get(models.Product, reservation.product_id)
    if not product:
        return {}
    breakdown = build_price_breakdown(db, product, reservation.quantity, reservation.customer_phone)
    reservation.currency = breakdown["currency"]
    reservation.gross_amount = breakdown["gross_amount"]
    reservation.loyalty_discount_percent = breakdown["loyalty_discount_percent"]
    reservation.loyalty_discount_amount = breakdown["loyalty_discount_amount"]
    reservation.payable_amount = breakdown["payable_amount"]
    reservation.platform_fee_percent = breakdown["platform_fee_percent"]
    reservation.platform_fee_amount = breakdown["platform_fee_amount"]
    reservation.seller_net_amount = breakdown["seller_net_amount"]
    return breakdown


def mark_paid(reservation: models.Reservation, *, provider: str = "demo", method: str = "online_card_demo") -> None:
    reservation.payment_status = "paid"
    reservation.payment_provider = provider
    reservation.payment_method = method
    reservation.payment_reference = f"PAY-{uuid4().hex[:10].upper()}"
    reservation.paid_at = datetime.utcnow()
    # Plaćena online rezervacija se automatski potvrđuje.
    if reservation.status == "pending":
        reservation.status = "confirmed"
    if not getattr(reservation, "seller_payout_status", None) or reservation.seller_payout_status in {"not_ready", "blocked"}:
        reservation.seller_payout_status = "pending"
    reservation.updated_at = datetime.utcnow()


def mark_refunded_if_paid(reservation: models.Reservation) -> None:
    if reservation.payment_status == "paid":
        reservation.payment_status = "refunded"
        if getattr(reservation, "seller_payout_status", None) != "paid":
            reservation.seller_payout_status = "blocked"
        reservation.updated_at = datetime.utcnow()
