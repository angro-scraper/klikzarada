from __future__ import annotations

import json
import os
import random
import secrets
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services.pricing import normalize_phone, loyalty_percent_for_completed_pickups
from ..services.notifications import send_sms, otp_message
from ..services.admin_auth import is_request_admin
from ..services.customers import (
    customer_to_public,
    find_customer_by_phone,
    rebuild_customer_database,
)

router = APIRouter(prefix="/customers", tags=["customers"])

DATA_DIR = Path(__file__).resolve().parents[1].parent / "data"
OTP_FILE = DATA_DIR / "customer_otp_sessions.json"
OTP_TTL_MINUTES = int(os.getenv("CUSTOMER_OTP_TTL_MINUTES", "10"))
TOKEN_TTL_DAYS = int(os.getenv("CUSTOMER_TOKEN_TTL_DAYS", "30"))
DEV_SHOW_OTP = os.getenv("DEV_SHOW_OTP", "true").lower() in {"1", "true", "yes", "da"}


def _admin_guard_active() -> bool:
    return os.getenv("ADMIN_GUARD_ENABLED", "false").lower() in {"1", "true", "yes", "da", "on"}


def _require_customer_admin(request: Request) -> None:
    if _admin_guard_active() and not is_request_admin(request):
        raise HTTPException(status_code=401, detail="Admin prijava je potrebna")


class OtpRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=40)


class OtpVerifyRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=40)
    code: str = Field(..., min_length=4, max_length=10)


def _money(value) -> float:
    return round(float(value or 0), 2)


def _now() -> datetime:
    return datetime.utcnow()


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat() + "Z"


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", ""))
    except Exception:
        return None


def _load_otp_store() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not OTP_FILE.exists():
        return {"otps": {}, "tokens": {}}
    try:
        data = json.loads(OTP_FILE.read_text(encoding="utf-8"))
        return {"otps": data.get("otps", {}), "tokens": data.get("tokens", {})}
    except Exception:
        return {"otps": {}, "tokens": {}}


def _save_otp_store(data: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OTP_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _cleanup_otp_store(data: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    data["otps"] = {
        phone: payload
        for phone, payload in data.get("otps", {}).items()
        if (_parse_iso(payload.get("expires_at")) or now) > now
    }
    data["tokens"] = {
        token: payload
        for token, payload in data.get("tokens", {}).items()
        if (_parse_iso(payload.get("expires_at")) or now) > now
    }
    return data


def _mask_phone(phone: str) -> str:
    normalized = normalize_phone(phone)
    if len(normalized) <= 4:
        return "***"
    return f"***{normalized[-4:]}"


def _matching_reservations(db: Session, phone: str):
    normalized = normalize_phone(phone)
    if len(normalized) < 5:
        raise HTTPException(status_code=400, detail="Unesi ispravan broj telefona")
    suffix = normalized[-6:] if len(normalized) >= 6 else normalized
    # MVP logika: telefon se poredi po poslednjih 6 cifara, kao kod provere rezervacije.
    rows = db.query(models.Reservation).order_by(models.Reservation.created_at.desc()).all()
    return [r for r in rows if normalize_phone(r.customer_phone).endswith(suffix)]


def _next_loyalty_goal(picked_up: int) -> dict:
    tiers = [
        (1, 1.0, "Prvi popust za stalne kupce"),
        (3, 2.0, "Sledeći loyalty nivo"),
        (5, 3.0, "Bronze loyalty nivo"),
        (10, 4.0, "Silver loyalty nivo"),
        (20, 5.0, "Gold loyalty nivo"),
    ]
    current = loyalty_percent_for_completed_pickups(picked_up)
    for required, percent, label in tiers:
        if picked_up < required:
            return {
                "current_discount_percent": current,
                "next_discount_percent": percent,
                "remaining_pickups": required - picked_up,
                "next_label": label,
                "max_reached": False,
            }
    return {
        "current_discount_percent": current,
        "next_discount_percent": current,
        "remaining_pickups": 0,
        "next_label": "Maksimalni loyalty nivo",
        "max_reached": True,
    }


def _profile_payload(db: Session, phone: str, limit: int = 50, secure: bool = False) -> dict:
    reservations = _matching_reservations(db, phone)
    limited = reservations[:limit]
    customer = find_customer_by_phone(db, phone)

    picked_up = sum(1 for r in reservations if r.status == "picked_up")
    active = sum(1 for r in reservations if r.status in {"pending", "confirmed"})
    cancelled = sum(1 for r in reservations if r.status == "cancelled")
    paid = sum(1 for r in reservations if r.payment_status == "paid")
    payment_pending = sum(1 for r in reservations if r.payment_status == "payment_pending")

    category_counter = Counter()
    store_counter = Counter()
    for r in reservations:
        if r.product:
            if r.product.category:
                category_counter[r.product.category] += 1
            if r.product.store:
                store_counter[r.product.store.name] += 1

    items = []
    for r in limited:
        product = r.product
        store = product.store if product and product.store else None
        items.append({
            "reservation_code": r.reservation_code,
            "product_id": r.product_id,
            "product_name": product.name if product else None,
            "category": product.category if product else None,
            "store_name": store.name if store else None,
            "store_city": store.city if store else None,
            "store_address": store.address if store else None,
            "quantity": r.quantity,
            "status": r.status,
            "payment_status": r.payment_status,
            "payable_amount": _money(r.payable_amount),
            "gross_amount": _money(r.gross_amount),
            "loyalty_discount_percent": _money(r.loyalty_discount_percent),
            "loyalty_discount_amount": _money(r.loyalty_discount_amount),
            "currency": r.currency or "RSD",
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "paid_at": r.paid_at.isoformat() if r.paid_at else None,
            "ticket_url": f"/reservation?code={r.reservation_code}",
            "checkout_url": f"/checkout?code={r.reservation_code}",
        })

    goal = _next_loyalty_goal(picked_up)
    total_paid_amount = _money(sum(float(r.payable_amount or 0) for r in reservations if r.payment_status == "paid"))
    total_loyalty_saved = _money(sum(float(r.loyalty_discount_amount or 0) for r in reservations))

    return {
        "phone_masked": _mask_phone(phone),
        "verified": secure,
        "customer": customer_to_public(customer),
        "total_reservations": len(reservations),
        "active_reservations": active,
        "picked_up_count": picked_up,
        "cancelled_count": cancelled,
        "paid_count": paid,
        "payment_pending_count": payment_pending,
        "total_paid_amount": total_paid_amount,
        "total_loyalty_saved": total_loyalty_saved,
        "currency": "RSD",
        "loyalty": goal,
        "top_categories": [{"name": k, "count": v} for k, v in category_counter.most_common(5)],
        "top_stores": [{"name": k, "count": v} for k, v in store_counter.most_common(5)],
        "reservations": items,
        "privacy_note": "Telefon je potvrđen jednokratnim kodom. U V34 OTP može da se šalje preko podešenog SMS providera ili mock loga.",
    }


@router.post("/otp/request", response_model=dict)
def request_customer_otp(payload: OtpRequest):
    normalized = normalize_phone(payload.phone)
    if len(normalized) < 5:
        raise HTTPException(status_code=400, detail="Unesi ispravan broj telefona")

    data = _cleanup_otp_store(_load_otp_store())
    code = f"{random.randint(0, 999999):06d}"
    expires_at = _now() + timedelta(minutes=OTP_TTL_MINUTES)
    data["otps"][normalized] = {
        "code": code,
        "expires_at": _iso(expires_at),
        "attempts": 0,
        "created_at": _iso(_now()),
    }
    _save_otp_store(data)

    notification = send_sms(
        normalized,
        otp_message(code),
        purpose="customer_otp",
        metadata={"expires_in_seconds": OTP_TTL_MINUTES * 60},
    )

    return {
        "ok": True,
        "phone_masked": _mask_phone(normalized),
        "expires_in_seconds": OTP_TTL_MINUTES * 60,
        "delivery": notification.get("provider", "mock"),
        "notification_status": notification.get("status"),
        "message": "Kod je poslat ili upisan u lokalni SMS log, u zavisnosti od SMS_PROVIDER podešavanja.",
        "dev_otp": code if DEV_SHOW_OTP else None,
    }


@router.post("/otp/verify", response_model=dict)
def verify_customer_otp(payload: OtpVerifyRequest):
    normalized = normalize_phone(payload.phone)
    code = "".join(ch for ch in str(payload.code) if ch.isdigit())
    data = _cleanup_otp_store(_load_otp_store())
    otp = data.get("otps", {}).get(normalized)
    if not otp:
        raise HTTPException(status_code=400, detail="Kod je istekao ili nije zatražen")
    if int(otp.get("attempts", 0)) >= 5:
        data["otps"].pop(normalized, None)
        _save_otp_store(data)
        raise HTTPException(status_code=429, detail="Previše pokušaja. Zatraži novi kod")
    if code != str(otp.get("code")):
        otp["attempts"] = int(otp.get("attempts", 0)) + 1
        data["otps"][normalized] = otp
        _save_otp_store(data)
        raise HTTPException(status_code=400, detail="Pogrešan kod")

    token = secrets.token_urlsafe(32)
    data["otps"].pop(normalized, None)
    data["tokens"][token] = {
        "phone": normalized,
        "created_at": _iso(_now()),
        "expires_at": _iso(_now() + timedelta(days=TOKEN_TTL_DAYS)),
    }
    _save_otp_store(data)
    return {
        "ok": True,
        "token": token,
        "phone_masked": _mask_phone(normalized),
        "expires_in_days": TOKEN_TTL_DAYS,
        "message": "Telefon je potvrđen.",
    }


def _require_token(phone: str, token: str) -> str:
    normalized = normalize_phone(phone)
    data = _cleanup_otp_store(_load_otp_store())
    token_payload = data.get("tokens", {}).get(token)
    _save_otp_store(data)
    if not token_payload or token_payload.get("phone") != normalized:
        raise HTTPException(status_code=401, detail="Nalog nije potvrđen. Zatraži novi SMS/OTP kod")
    return normalized


@router.get("/profile-secure", response_model=dict)
def customer_profile_secure(
    phone: str = Query(..., min_length=5),
    token: str = Query(..., min_length=16),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    normalized = _require_token(phone, token)
    return _profile_payload(db, normalized, limit=limit, secure=True)


@router.get("/profile", response_model=dict)
def customer_profile(
    phone: str = Query(..., min_length=5),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    # Backward-compatible MVP endpoint kept for admin/testing.
    payload = _profile_payload(db, phone, limit=limit, secure=False)
    payload["privacy_note"] = "Ovo je nezaštićen MVP prikaz po telefonu. Koristi /customer stranicu sa OTP potvrdom za bezbedniji prikaz naloga."
    return payload


@router.get("/database", response_model=dict)
def customer_database(
    request: Request,
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    _require_customer_admin(request)
    query = db.query(models.Customer)
    if status:
        query = query.filter(models.Customer.status == status)
    total = query.count()
    customers = query.order_by(models.Customer.updated_at.desc()).limit(limit).all()
    blocked_total = db.query(models.Customer).filter(models.Customer.status == "blocked").count()
    return {
        "ok": True,
        "customers_total": total,
        "blocked_customers_total": blocked_total,
        "limit": limit,
        "customers": [customer_to_public(customer) for customer in customers],
    }


@router.post("/database/rebuild", response_model=dict)
def rebuild_customer_database_endpoint(request: Request, db: Session = Depends(get_db)):
    _require_customer_admin(request)
    return rebuild_customer_database(db)


@router.post("/{customer_id}/unblock", response_model=dict)
def unblock_customer(customer_id: int, request: Request, db: Session = Depends(get_db)):
    _require_customer_admin(request)
    customer = db.get(models.Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Korisnik nije pronađen")
    customer.status = "active"
    customer.blocked_at = None
    customer.block_reason = None
    customer.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(customer)
    return {
        "ok": True,
        "message": "Korisnik je odblokiran.",
        "customer": customer_to_public(customer),
    }
