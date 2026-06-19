from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models

SELLER_AGREEMENT_VERSION = "seller-v1-2026-06"
VISIBLE_PRODUCT_STATUSES = {"public_discount", "seller_verified", "near_expiry"}
SELLER_TYPES = {"business", "home_producer", "individual", "farm", "other"}


def seller_type_label(value: str | None) -> str:
    labels = {
        "business": "Firma / registrovana delatnost",
        "home_producer": "Domaća radinost",
        "individual": "Fizičko lice",
        "farm": "Gazdinstvo / mali proizvođač",
        "other": "Drugo",
    }
    return labels.get(value or "business", "Firma / registrovana delatnost")


def product_quality_issues(data: Any) -> list[str]:
    def get(name: str):
        if isinstance(data, dict):
            return data.get(name)
        return getattr(data, name, None)

    issues: list[str] = []
    if not str(get("image_url") or "").strip():
        issues.append("Artikal mora imati sliku.")
    if not str(get("description") or "").strip() or len(str(get("description") or "").strip()) < 10:
        issues.append("Artikal mora imati jasan opis od najmanje 10 karaktera.")
    if not get("expiry_date"):
        issues.append("Artikal mora imati rok trajanja.")
    if not str(get("pickup_window") or "").strip():
        issues.append("Artikal mora imati vreme preuzimanja.")
    return issues


def require_product_quality(data: Any, *, status: str | None = None) -> None:
    if status and status not in VISIBLE_PRODUCT_STATUSES and status != "candidate":
        return
    issues = product_quality_issues(data)
    if issues:
        raise HTTPException(status_code=400, detail=" ".join(issues))


def overdue_invoice_count(db: Session, store_id: int, now: datetime | None = None) -> int:
    now = now or datetime.utcnow()
    rows = (
        db.query(models.Reservation.seller_payout_reference)
        .join(models.Product)
        .filter(
            models.Product.store_id == store_id,
            models.Reservation.seller_payout_status == "invoice_sent",
            models.Reservation.seller_invoice_due_at.is_not(None),
            models.Reservation.seller_invoice_due_at < now,
        )
        .group_by(models.Reservation.seller_payout_reference)
        .all()
    )
    return len(rows)


def open_invoice_total(db: Session, store_id: int) -> float:
    value = (
        db.query(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0))
        .join(models.Product)
        .filter(
            models.Product.store_id == store_id,
            models.Reservation.seller_payout_status == "invoice_sent",
        )
        .scalar()
    )
    return round(float(value or 0), 2)


def recompute_seller_loyalty(db: Session, store: models.Store) -> dict[str, Any]:
    picked_up = (
        db.query(func.count(models.Reservation.id))
        .join(models.Product)
        .filter(models.Product.store_id == store.id, models.Reservation.status == "picked_up")
        .scalar()
        or 0
    )
    active_products = (
        db.query(func.count(models.Product.id))
        .filter(models.Product.store_id == store.id, models.Product.status.in_(VISIBLE_PRODUCT_STATUSES))
        .scalar()
        or 0
    )
    image_products = (
        db.query(func.count(models.Product.id))
        .filter(
            models.Product.store_id == store.id,
            models.Product.status.in_(VISIBLE_PRODUCT_STATUSES),
            models.Product.image_url.is_not(None),
            models.Product.image_url != "",
        )
        .scalar()
        or 0
    )
    points = int(picked_up) * 10 + int(active_products) * 2 + int(image_products) * 3 - int(store.late_payment_count or 0) * 25
    points = max(0, points)
    if points >= 500 and not store.blocked:
        tier = "gold"
    elif points >= 180 and not store.blocked:
        tier = "silver"
    elif points >= 60 and not store.blocked:
        tier = "bronze"
    else:
        tier = "start"
    store.loyalty_points = points
    store.loyalty_tier = tier
    return {"points": points, "tier": tier, "picked_up": int(picked_up), "active_products": int(active_products)}


def enforce_seller_billing_rules(db: Session, store: models.Store) -> dict[str, Any]:
    overdue = overdue_invoice_count(db, store.id)
    late = int(store.late_payment_count or 0)
    should_block = overdue >= 2 or late >= 3
    if should_block and not store.blocked:
        store.blocked = True
        store.blocked_at = datetime.utcnow()
        store.blocked_reason = (
            "Automatska blokada: 2 neplaćene fakture za proviziju ili 3 kašnjenja sa plaćanjem."
        )
    recompute_seller_loyalty(db, store)
    return {
        "blocked": bool(store.blocked),
        "blocked_reason": store.blocked_reason,
        "overdue_invoice_count": overdue,
        "late_payment_count": late,
        "open_invoice_total": open_invoice_total(db, store.id),
        "loyalty_points": store.loyalty_points,
        "loyalty_tier": store.loyalty_tier,
    }


def require_seller_ready(db: Session, store: models.Store) -> None:
    status = enforce_seller_billing_rules(db, store)
    if store.blocked:
        raise HTTPException(status_code=403, detail=store.blocked_reason or "Prodavac je blokiran.")
    if not store.agreement_accepted or not store.liability_accepted or not store.commission_terms_accepted:
        raise HTTPException(
            status_code=403,
            detail="Pre dodavanja proizvoda prodavac mora da prihvati ugovor, odgovornost za ponude i uslove provizije.",
        )
    if status["overdue_invoice_count"] >= 2:
        raise HTTPException(status_code=403, detail="Prodavac ima 2 neplaćene fakture i mora kontaktirati administraciju.")
