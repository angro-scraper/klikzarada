"""JSON API consumed by the React interface.

The legacy HTML routes intentionally remain available for operations and
backwards compatibility.  This module is the single browser-facing contract
for the new UI, so business data still lives in the existing database.
"""

from __future__ import annotations

import ipaddress
import hashlib
import hmac
import json
import os
import re
import socket
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Literal
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import get_db
from .models import (
    AdvertiserBudgetTransaction,
    AntiFraudDeviceV1,
    AuditLog,
    FraudSignalV11,
    HomeBannerSlotV111,
    PayPalCheckout,
    PayPalPayoutAttempt,
    PaidAdBannerV111,
    SystemSetting,
    SupportMessage,
    SupportTicket,
    Task,
    TaskSourceV11,
    TaskSubmission,
    TaskVerificationSessionV1,
    User,
    WalletTransaction,
    Withdrawal,
)
from .security import create_session_token, hash_password, make_referral_code, read_session_token, verify_password


router = APIRouter(prefix="/api/ui", tags=["KlikZarada UI"])

PLATFORM_FEE_PERCENT = 20.0
MIN_WITHDRAWAL_RSD = 1000.0
ANTI_FRAUD_DAILY_TASK_LIMIT = 20
ANTI_FRAUD_DAILY_EARNINGS_RSD = 2000.0
ANTI_FRAUD_MIN_ACTIVITY_EVENTS = 8
ANTI_FRAUD_HIGH_RISK_SCORE = 70.0

REQUIRED_SYSTEM_SETTINGS = {
    "advertiser_payment_account": "Poslovni račun na koji oglašivači uplaćuju budžet.",
    "advertiser_payment_holder": "Naziv primaoca za uplate oglašivača.",
    "payment_reference": "Svrha uplate ili poziv na broj za budžet oglašivača.",
    "user_payout_account": "Poslovni račun sa kog se korisnicima isplaćuju sredstva.",
    "user_payout_holder": "Naziv pošiljaoca za korisničke isplate.",
    "payout_reference": "Svrha isplate ili poziv na broj za korisnike.",
    "payment_provider_name": "Naziv ugovorenog provajdera za online naplatu.",
    "payment_provider_checkout_base": "Checkout URL provajdera za online naplatu.",
    "payment_provider_webhook_secret": "Tajni ključ za proveru webhook potvrda provajdera.",
    "payment_provider_success_url": "URL nakon uspešne online uplate.",
    "payment_provider_cancel_url": "URL nakon otkazane online uplate.",
}


class Credentials(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=200)


class Registration(Credentials):
    full_name: str = Field(min_length=2, max_length=160)
    role: Literal["korisnik", "oglasivac"] = "korisnik"
    advertiser_type: Literal["business", "private"] = "business"
    referral_code: str | None = Field(default=None, max_length=40)
    phone: str | None = Field(default=None, max_length=80)
    device_fingerprint: str | None = Field(default=None, max_length=300)


class ProofPayload(BaseModel):
    proof: str = Field(min_length=3, max_length=5000)
    verification_token: str = Field(min_length=20, max_length=80)


class VerificationStartPayload(BaseModel):
    device_fingerprint: str = Field(min_length=12, max_length=300)
    device_label: str | None = Field(default=None, max_length=180)


class VerificationHeartbeatPayload(BaseModel):
    token: str = Field(min_length=20, max_length=80)
    activity_events: int = Field(default=0, ge=0, le=2000)
    visible: bool = True
    focus_lost: bool = False


class WithdrawalPayload(BaseModel):
    amount_rsd: float = Field(gt=0)
    payment_method: str = Field(min_length=2, max_length=80)
    payment_details: str = Field(min_length=3, max_length=2000)


class ProfilePayload(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=100)
    payment_method: str | None = Field(default=None, max_length=80)
    payment_details: str | None = Field(default=None, max_length=2000)


class CampaignPayload(BaseModel):
    title: str = Field(min_length=3, max_length=220)
    category: str = Field(default="Promo", max_length=80)
    task_type: str = Field(min_length=2, max_length=80)
    target_url: str | None = Field(default=None, max_length=500)
    description: str = Field(min_length=5, max_length=5000)
    instructions: str = Field(min_length=5, max_length=5000)
    proof_required: str = Field(min_length=2, max_length=5000)
    reward_rsd: float = Field(gt=0)
    total_slots: int = Field(gt=0, le=100000)
    target_city: str | None = Field(default="Srbija", max_length=100)
    target_age_group: str | None = Field(default="18+", max_length=40)
    target_interests: str | None = Field(default=None, max_length=2000)


class BannerReservationPayload(BaseModel):
    slot_id: int
    title: str = Field(min_length=3, max_length=180)
    body: str | None = Field(default=None, max_length=1000)
    image_url: str | None = Field(default=None, max_length=500)
    target_url: str = Field(min_length=1, max_length=500)
    days_count: int = Field(default=7, ge=1, le=31)


class AdminBannerStatusPayload(BaseModel):
    status: Literal["active", "rejected"]
    note: str | None = Field(default=None, max_length=1000)


class PayPalTopupPayload(BaseModel):
    amount_rsd: float = Field(ge=200, le=1_000_000)
    checkout_flow: Literal["redirect", "smart_button"] = "redirect"


class AdminStatusPayload(BaseModel):
    status: str = Field(min_length=2, max_length=40)
    note: str | None = Field(default=None, max_length=2000)


class PayPalPayoutPayload(BaseModel):
    """An explicit phrase prevents an accidental API call from sending money."""
    confirmation_code: str = Field(min_length=8, max_length=160)


class SourcePayload(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    endpoint_url: str = Field(min_length=8, max_length=500)
    api_key: str | None = Field(default=None, max_length=250)
    import_mode: Literal["review", "sync", "manual"] = "review"


class SupportTicketPayload(BaseModel):
    subject: str = Field(min_length=3, max_length=220)
    body: str = Field(min_length=5, max_length=5000)
    category: str = Field(default="Opšte", max_length=80)


class SettingPayload(BaseModel):
    value: str = Field(default="", max_length=5000)


def _money(value: float | None) -> float:
    return round(float(value or 0), 2)


def _limit_from_env(name: str, default: int | float) -> int | float:
    """Keep operational limits configurable without trusting browser input."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return int(value) if isinstance(default, int) else value


def _fraud_pepper() -> bytes:
    secret = os.getenv("KLIKZARADA_FRAUD_PEPPER") or os.getenv("KLIKZARADA_SECRET_KEY")
    if secret:
        return secret.encode("utf-8")
    # Local development stays usable; production must set the application secret.
    return b"klikzarada-local-development-fraud-pepper"


def _hash_fraud_value(value: str | None) -> str | None:
    normalized = (value or "").strip()
    if not normalized:
        return None
    return hmac.new(_fraud_pepper(), normalized.encode("utf-8"), hashlib.sha256).hexdigest()


def _request_client_ip(request: Request) -> str | None:
    """Return the connection IP, using the Render proxy header when present."""
    forwarded = request.headers.get("x-forwarded-for", "").split(",")
    candidates = [item.strip() for item in forwarded if item.strip()]
    if request.client and request.client.host:
        candidates.append(request.client.host)
    for candidate in candidates:
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    return None


def _request_ip_context(request: Request) -> tuple[str | None, str | None, str | None]:
    """Return HMAC hashes plus a masked network for admin review.

    Forwarded headers are used only as a risk signal and never as identity or
    a reason to credit a task automatically.
    """
    client_ip = _request_client_ip(request)
    if not client_ip:
        return None, None, None
    address = ipaddress.ip_address(client_ip)
    if address.version == 4:
        network = ipaddress.ip_network(f"{address}/24", strict=False)
    else:
        network = ipaddress.ip_network(f"{address}/56", strict=False)
    return _hash_fraud_value(str(address)), _hash_fraud_value(str(network)), str(network)


def _device_label(request: Request, submitted_label: str | None = None) -> str:
    label = (submitted_label or "").strip()
    if label:
        return label[:180]
    return (request.headers.get("user-agent") or "Nepoznat uređaj")[:180]


def _record_fraud_device(
    db: Session,
    user: User,
    request: Request,
    fingerprint: str | None,
    device_label: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    _, network_hash, network_label = _request_ip_context(request)
    fingerprint_hash = _hash_fraud_value(fingerprint)
    now = datetime.utcnow()
    if fingerprint_hash:
        row = db.query(AntiFraudDeviceV1).filter(
            AntiFraudDeviceV1.user_id == user.id,
            AntiFraudDeviceV1.fingerprint_hash == fingerprint_hash,
        ).first()
        if row:
            row.network_hash = network_hash
            row.network_label = network_label
            row.device_label = _device_label(request, device_label)
            row.last_seen_at = now
        else:
            db.add(AntiFraudDeviceV1(
                user_id=user.id,
                fingerprint_hash=fingerprint_hash,
                network_hash=network_hash,
                network_label=network_label,
                device_label=_device_label(request, device_label),
            ))
    return fingerprint_hash, network_hash, network_label


def _add_fraud_signal(
    db: Session,
    user_id: int,
    signal_type: str,
    risk_score: float,
    details: dict,
) -> FraudSignalV11:
    """De-duplicate open signals so one bad browser cannot flood the queue."""
    recent = datetime.utcnow() - timedelta(hours=24)
    existing = db.query(FraudSignalV11).filter(
        FraudSignalV11.user_id == user_id,
        FraudSignalV11.signal_type == signal_type,
        FraudSignalV11.status == "open",
        FraudSignalV11.created_at >= recent,
    ).first()
    encoded = json.dumps(details, ensure_ascii=False, separators=(",", ":"))
    if existing:
        existing.risk_score = max(float(existing.risk_score or 0), risk_score)
        existing.details = encoded
        return existing
    signal = FraudSignalV11(user_id=user_id, signal_type=signal_type, risk_score=risk_score, details=encoded)
    db.add(signal)
    return signal


def _open_risk_score(db: Session, user_id: int) -> float:
    return float(db.query(func.coalesce(func.max(FraudSignalV11.risk_score), 0)).filter(
        FraudSignalV11.user_id == user_id,
        FraudSignalV11.status == "open",
    ).scalar() or 0)


def _verification_data(session: TaskVerificationSessionV1) -> dict:
    return {
        "token": session.token,
        "status": _status(session.status),
        "required_seconds": session.required_seconds,
        "active_seconds": session.active_seconds,
        "activity_events": session.activity_events,
        "risk_score": _money(session.risk_score),
        "remaining_seconds": max(0, int(session.required_seconds or 0) - int(session.active_seconds or 0)),
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _status(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "_")


def _user_data(user: User) -> dict:
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "level": user.level or "Bronza",
        "balance_rsd": _money(user.balance_rsd),
        "pending_rsd": _money(user.pending_rsd),
        "lifetime_earned_rsd": _money(user.lifetime_earned_rsd),
        "payment_method": user.payment_method,
        "payment_details": user.payment_details,
        "company_name": user.company_name,
        "advertiser_budget_rsd": _money(user.advertiser_budget_rsd),
        "advertiser_reserved_rsd": _money(user.advertiser_reserved_rsd),
        "advertiser_spent_rsd": _money(user.advertiser_spent_rsd),
        "referral_code": user.referral_code,
    }


def _task_data(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "category": task.category,
        "task_type": task.task_type,
        "target_url": task.target_url,
        "description": task.description,
        "instructions": task.instructions,
        "proof_required": task.proof_required,
        "reward_rsd": _money(task.reward_rsd),
        "total_slots": task.total_slots,
        "used_slots": task.used_slots,
        "estimated_minutes": task.estimated_minutes,
        "min_user_level": task.min_user_level or "Bronza",
        "featured": bool(task.featured),
        "status": _status(task.status),
        "moderation_note": task.moderation_note,
        "target_city": task.target_city,
        "target_age_group": task.target_age_group,
        "target_interests": task.target_interests,
        "created_at": _iso(task.created_at),
    }


def _submission_data(submission: TaskSubmission) -> dict:
    return {
        "id": submission.id,
        "task_id": submission.task_id,
        "task_title": submission.task.title if submission.task else "Zadatak",
        "proof": submission.proof,
        "status": _status(submission.status),
        "reward_rsd": _money(submission.reward_rsd),
        "review_note": submission.review_note,
        "created_at": _iso(submission.created_at),
    }


def _ticket_data(ticket: SupportTicket) -> dict:
    return {
        "id": ticket.id,
        "subject": ticket.subject,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": _status(ticket.status),
        "created_at": _iso(ticket.created_at),
        "updated_at": _iso(ticket.updated_at),
        "user_name": ticket.user.full_name if ticket.user else "Korisnik",
    }


def _paypal_email(value: str | None) -> str:
    """Normalize the only payout destination the platform accepts."""
    recipient = (value or "").strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", recipient):
        raise HTTPException(400, "Unesi važeću PayPal email adresu za isplatu.")
    return recipient


_BANNER_SLOT_DEFAULTS = (
    ("home_top_left", "Početna — gornji levi premium banner", "home_top", "half", 5000),
    ("home_top_right", "Početna — gornji desni premium banner", "home_top", "half", 5000),
    ("home_sponsor_1", "Početna — sponzorski banner 1", "home_sponsor", "quarter", 3000),
    ("home_sponsor_2", "Početna — sponzorski banner 2", "home_sponsor", "quarter", 3000),
    ("home_sponsor_3", "Početna — sponzorski banner 3", "home_sponsor", "quarter", 3000),
    ("home_sponsor_4", "Početna — sponzorski banner 4", "home_sponsor", "quarter", 3000),
    ("home_dashboard_banner", "Početna — banner ispod isplate", "home_dashboard", "wide", 4500),
    ("home_bottom_1", "Početna — donji banner 1", "home_bottom", "third", 2500),
    ("home_bottom_2", "Početna — donji banner 2", "home_bottom", "third", 2500),
    ("home_bottom_3", "Početna — donji banner 3", "home_bottom", "third", 2500),
)

# These are the only campaign categories offered at launch. They are designed
# around verifiable work rather than incentivized clicks, reviews, or follows.
_SAFE_CAMPAIGN_CATEGORIES = {
    "Ankete i testiranja",
    "Testiranje sajta ili aplikacije",
    "Provera podataka",
    "Kratak feedback",
    "Lokalna provera",
    "Označavanje podataka",
}


def _ensure_banner_slots(db: Session) -> None:
    existing_codes = {code for (code,) in db.query(HomeBannerSlotV111.code).all()}
    missing = [
        HomeBannerSlotV111(
            code=code,
            title=title,
            placement=placement,
            width_label=width_label,
            price_rsd=price_rsd,
            is_active=True,
        )
        for code, title, placement, width_label, price_rsd in _BANNER_SLOT_DEFAULTS
        if code not in existing_codes
    ]
    if missing:
        db.add_all(missing)
        db.commit()


def _banner_status(value: str | None) -> str:
    return {
        "active": "aktivno",
        "pending": "na_cekanju",
        "rejected": "odbijeno",
        "expired": "obustavljeno",
    }.get(_status(value), _status(value))


def _is_legacy_demo_banner(banner: PaidAdBannerV111) -> bool:
    return banner.title == "Demo plaćeni banner" and banner.target_url == "/registracija"


def _banner_data(banner: PaidAdBannerV111) -> dict:
    return {
        "id": banner.id,
        "slot_id": banner.slot_id,
        "slot_title": banner.slot.title if banner.slot else "Banner slot",
        "slot_code": banner.slot.code if banner.slot else None,
        "advertiser_id": banner.advertiser_id,
        "advertiser_name": banner.advertiser.company_name or banner.advertiser.full_name if banner.advertiser else "Oglašivač",
        "title": banner.title,
        "body": banner.body,
        "image_url": banner.image_url,
        "target_url": banner.target_url,
        "price_rsd": _money(banner.price_rsd),
        "days_count": banner.days_count,
        "status": _banner_status(banner.status),
        "admin_note": banner.admin_note,
        "starts_at": _iso(banner.starts_at),
        "ends_at": _iso(banner.ends_at),
        "views_count": int(banner.views_count or 0),
        "created_at": _iso(banner.created_at),
    }


def _banner_slot_data(slot: HomeBannerSlotV111, banners: list[PaidAdBannerV111]) -> dict:
    slot_banners = [banner for banner in banners if banner.slot_id == slot.id]
    active = next((banner for banner in slot_banners if banner.status == "active"), None)
    now = datetime.utcnow()
    schedule = [
        _banner_data(banner)
        for banner in sorted(slot_banners, key=lambda item: item.starts_at or item.created_at or now)
        if banner.status in {"active", "pending"}
        and (banner.ends_at is None or banner.ends_at > now)
    ]
    return {
        "id": slot.id,
        "code": slot.code,
        "title": slot.title,
        "placement": slot.placement,
        "width_label": slot.width_label,
        "price_rsd": _money(slot.price_rsd),
        "is_active": bool(slot.is_active),
        "active_banner": _banner_data(active) if active else None,
        "pending_count": sum(1 for banner in slot_banners if banner.status == "pending"),
        "schedule": schedule,
    }


def _validate_banner_target_url(value: str) -> str:
    url = value.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(400, "Link banera mora biti pun http:// ili https:// URL.")
    return url


def _pricing_data() -> dict:
    """Expose the launch catalogue from the same values used for reservations."""
    return {
        "platform_fee_percent": PLATFORM_FEE_PERCENT,
        "task_categories": sorted(_SAFE_CAMPAIGN_CATEGORIES),
        "banner_price_basis_days": 7,
        "banner_max_days": 31,
    }


def _banner_slot_conflict(
    db: Session,
    slot_id: int,
    starts_at: datetime,
    ends_at: datetime,
) -> bool:
    candidates = db.query(PaidAdBannerV111).filter(
        PaidAdBannerV111.slot_id == slot_id,
        PaidAdBannerV111.status.in_(("pending", "active")),
    ).all()
    for banner in candidates:
        if _is_legacy_demo_banner(banner):
            continue
        existing_start = banner.starts_at or banner.created_at or datetime.utcnow()
        existing_end = banner.ends_at or existing_start + timedelta(days=max(1, banner.days_count or 7))
        if starts_at < existing_end and existing_start < ends_at:
            return True
    return False


def _cookie_is_secure(request: Request) -> bool:
    forced = os.getenv("KLIKZARADA_COOKIE_SECURE", "").strip().lower()
    if forced in {"1", "true", "yes"}:
        return True
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").split(",")[0].strip() == "https"


def _validate_public_https_endpoint(endpoint_url: str) -> None:
    parsed = urlparse(endpoint_url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise HTTPException(400, "Endpoint mora biti javno dostupan HTTPS URL.")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, None, type=socket.SOCK_STREAM)
        resolved_ips = {entry[4][0] for entry in addresses}
    except socket.gaierror as exc:
        raise HTTPException(400, "Endpoint domen ne može da se razreši.") from exc
    if not resolved_ips or any(not ipaddress.ip_address(ip).is_global for ip in resolved_ips):
        raise HTTPException(400, "Endpoint mora voditi na javnu IP adresu.")


def _ensure_required_settings(db: Session) -> None:
    existing = {item.key for item in db.query(SystemSetting.key).all()}
    missing = [
        SystemSetting(key=key, value="", description=description)
        for key, description in REQUIRED_SYSTEM_SETTINGS.items()
        if key not in existing
    ]
    if missing:
        db.add_all(missing)
        db.commit()


def _current_user(request: Request, db: Session) -> User | None:
    user_id = read_session_token(request.cookies.get("kz_session"))
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    return user if user and user.status == "active" else None


def _require_user(request: Request, db: Session, roles: set[str] | None = None) -> User:
    user = _current_user(request, db)
    if not user:
        raise HTTPException(401, "Prijava je potrebna.")
    if roles and user.role not in roles:
        raise HTTPException(403, "Nemate pristup ovoj akciji.")
    return user


def _audit(db: Session, admin: User, action: str, entity_type: str, entity_id: int | None, details: str = "") -> None:
    db.add(AuditLog(admin_id=admin.id, action=action, entity_type=entity_type, entity_id=entity_id, reason=details))


@router.get("/health")
def health() -> dict:
    return {"ok": True, "ui": "react"}


@router.get("/session")
def session(request: Request, db: Session = Depends(get_db)) -> dict:
    user = _current_user(request, db)
    return {"authenticated": bool(user), "user": _user_data(user) if user else None}


@router.post("/auth/login")
def login(payload: Credentials, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if not user or user.status != "active" or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Pogrešan email, lozinka ili blokiran nalog.")
    response.set_cookie("kz_session", create_session_token(user.id), httponly=True, samesite="lax", secure=_cookie_is_secure(request))
    return {"user": _user_data(user)}


@router.post("/auth/register", status_code=201)
def register(payload: Registration, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email adresa je već registrovana.")
    phone = "".join(character for character in (payload.phone or "") if character.isdigit() or character == "+")
    if payload.role == "korisnik" and len(phone.replace("+", "")) < 7:
        raise HTTPException(400, "Unesi broj telefona za proveru jedinstvenosti naloga.")
    if phone and db.query(User).filter(User.phone == phone).first():
        raise HTTPException(409, "Ovaj broj telefona je već povezan sa drugim nalogom.")
    referrer = None
    if payload.referral_code:
        referrer = db.query(User).filter(User.referral_code == payload.referral_code.strip().upper()).first()
        if not referrer:
            raise HTTPException(400, "Referral kod nije pronađen.")
    user = User(
        full_name=payload.full_name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        status="active",
        phone=phone or None,
        referral_code=make_referral_code(payload.full_name),
        referred_by_id=referrer.id if referrer else None,
        company_name=payload.full_name.strip() if payload.role == "oglasivac" and payload.advertiser_type == "business" else None,
    )
    db.add(user)
    db.flush()
    fingerprint_hash, network_hash, network_label = _record_fraud_device(db, user, request, payload.device_fingerprint)
    if fingerprint_hash:
        linked_users = db.query(AntiFraudDeviceV1.user_id).filter(
            AntiFraudDeviceV1.fingerprint_hash == fingerprint_hash,
            AntiFraudDeviceV1.user_id != user.id,
        ).distinct().count()
        if linked_users:
            _add_fraud_signal(db, user.id, "shared_device_registration", 65, {
                "reason": "Uređaj je već korišćen za drugi nalog.",
                "network": network_label,
                "linked_accounts": linked_users,
            })
    if network_hash:
        network_users = db.query(AntiFraudDeviceV1.user_id).filter(
            AntiFraudDeviceV1.network_hash == network_hash,
            AntiFraudDeviceV1.user_id != user.id,
        ).distinct().count()
        if network_users >= 3:
            _add_fraud_signal(db, user.id, "shared_network_registration", 35, {
                "reason": "Veći broj naloga deli istu mrežu; potrebna je provera.",
                "network": network_label,
                "linked_accounts": network_users,
            })
    db.commit()
    db.refresh(user)
    response.set_cookie("kz_session", create_session_token(user.id), httponly=True, samesite="lax", secure=_cookie_is_secure(request))
    return {"user": _user_data(user)}


@router.post("/auth/logout", status_code=204)
def logout(response: Response) -> Response:
    response.delete_cookie("kz_session")
    return response


@router.get("/public/tasks")
def public_tasks(db: Session = Depends(get_db)) -> dict:
    tasks = db.query(Task).filter(Task.status == "active", Task.used_slots < Task.total_slots).order_by(Task.featured.desc(), Task.reward_rsd.desc()).limit(100).all()
    return {"tasks": [_task_data(task) for task in tasks]}


@router.get("/public/banners")
def public_banners(db: Session = Depends(get_db)) -> dict:
    now = datetime.utcnow()
    banners = db.query(PaidAdBannerV111).filter(
        PaidAdBannerV111.status == "active",
        (PaidAdBannerV111.starts_at.is_(None)) | (PaidAdBannerV111.starts_at <= now),
        (PaidAdBannerV111.ends_at.is_(None)) | (PaidAdBannerV111.ends_at > now),
    ).order_by(PaidAdBannerV111.created_at.desc()).limit(20).all()
    return {"banners": [_banner_data(banner) for banner in banners if not _is_legacy_demo_banner(banner)]}


@router.post("/public/banners/{banner_id}/impression", status_code=204)
def record_banner_impression(banner_id: int, db: Session = Depends(get_db)) -> Response:
    """Count a visible homepage placement. This never creates a user reward."""
    now = datetime.utcnow()
    banner = db.query(PaidAdBannerV111).filter(
        PaidAdBannerV111.id == banner_id,
        PaidAdBannerV111.status == "active",
        (PaidAdBannerV111.starts_at.is_(None)) | (PaidAdBannerV111.starts_at <= now),
        (PaidAdBannerV111.ends_at.is_(None)) | (PaidAdBannerV111.ends_at > now),
    ).first()
    if banner and not _is_legacy_demo_banner(banner):
        banner.views_count = int(banner.views_count or 0) + 1
        db.commit()
    return Response(status_code=204)


@router.get("/user/dashboard")
def user_dashboard(request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik", "admin"})
    tasks = db.query(Task).filter(Task.status == "active", Task.used_slots < Task.total_slots).order_by(Task.featured.desc(), Task.reward_rsd.desc()).limit(100).all()
    submissions = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id).order_by(TaskSubmission.created_at.desc()).limit(100).all()
    withdrawals = db.query(Withdrawal).filter(Withdrawal.user_id == user.id).order_by(Withdrawal.created_at.desc()).limit(100).all()
    transactions = db.query(WalletTransaction).filter(WalletTransaction.user_id == user.id).order_by(WalletTransaction.created_at.desc()).limit(100).all()
    referrals = db.query(User).filter(User.referred_by_id == user.id).count()
    return {
        "user": _user_data(user),
        "min_withdrawal_rsd": MIN_WITHDRAWAL_RSD,
        "referral_count": referrals,
        "tasks": [_task_data(task) for task in tasks],
        "submissions": [_submission_data(submission) for submission in submissions],
        "withdrawals": [{"id": item.id, "amount_rsd": _money(item.amount_rsd), "status": _status(item.status), "payment_method": item.payment_method, "created_at": _iso(item.created_at)} for item in withdrawals],
        "transactions": [{"id": item.id, "amount_rsd": _money(item.amount_rsd), "tx_type": item.tx_type, "description": item.description, "created_at": _iso(item.created_at)} for item in transactions],
    }


@router.put("/user/profile")
def save_user_profile(payload: ProfilePayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik", "admin"})
    phone = "".join(character for character in (payload.phone or "") if character.isdigit() or character == "+")
    if phone and db.query(User).filter(User.phone == phone, User.id != user.id).first():
        raise HTTPException(409, "Taj broj telefona je već povezan sa drugim nalogom.")
    user.full_name = payload.full_name.strip()
    user.phone = phone or None
    user.city = (payload.city or "").strip() or None
    user.payment_method = "PayPal"
    user.payment_details = _paypal_email(payload.payment_details)
    db.commit()
    return {"user": _user_data(user)}


@router.get("/tickets")
def my_support_tickets(request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db)
    tickets = db.query(SupportTicket).filter(SupportTicket.user_id == user.id).order_by(SupportTicket.updated_at.desc()).limit(100).all()
    return {"tickets": [_ticket_data(ticket) for ticket in tickets]}


@router.post("/tickets", status_code=201)
def create_support_ticket(payload: SupportTicketPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db)
    ticket = SupportTicket(user_id=user.id, subject=payload.subject.strip(), category=payload.category.strip() or "Opšte", status="open")
    db.add(ticket)
    db.flush()
    db.add(SupportMessage(ticket_id=ticket.id, sender_id=user.id, body=payload.body.strip()))
    db.commit()
    db.refresh(ticket)
    return {"ticket": _ticket_data(ticket)}


def _proxy_risk(request: Request) -> tuple[float, str | None]:
    """Use trustworthy local hints and an optional IPQualityScore check.

    A reputation provider is intentionally optional: lack of its API key never
    denies a legitimate task, while a positive VPN/proxy result raises risk for
    review. The browser cannot turn this check off.
    """
    risk = 0.0
    note = None
    if request.headers.get("via") or request.headers.get("forwarded"):
        risk += 15.0
        note = "Proxy-forwarding header je prisutan."
    api_key = os.getenv("IPQUALITYSCORE_API_KEY", "").strip()
    client_ip = _request_client_ip(request)
    _, _, network_label = _request_ip_context(request)
    if not api_key or not client_ip:
        return risk, note
    try:
        response = httpx.get(
            f"https://ipqualityscore.com/api/json/ip/{api_key}/{client_ip}",
            params={"strictness": 1, "allow_public_access_points": "true"},
            timeout=3,
        )
        result = response.json() if response.is_success else {}
        if result.get("vpn") or result.get("proxy") or result.get("tor"):
            risk += 45.0
            note = f"Reputation provera je označila VPN/proxy mrežu ({network_label or 'mreža'})."
        elif float(result.get("fraud_score") or 0) >= 75:
            risk += 30.0
            note = f"Reputation provera je vratila visok rizik mreže ({network_label or 'mreža'})."
    except (httpx.HTTPError, ValueError, TypeError):
        # A third-party outage must not break the task flow.
        pass
    return risk, note


def _task_required_seconds(task: Task) -> int:
    configured_min = int(_limit_from_env("ANTI_FRAUD_MIN_TASK_SECONDS", 30))
    configured_max = int(_limit_from_env("ANTI_FRAUD_MAX_TASK_SECONDS", 600))
    estimated = max(1, int(task.estimated_minutes or 1)) * 60
    return min(max(estimated, configured_min), max(configured_min, configured_max))


def _verify_daily_limits(db: Session, user: User, task: Task) -> None:
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    task_limit = int(_limit_from_env("ANTI_FRAUD_DAILY_TASK_LIMIT", ANTI_FRAUD_DAILY_TASK_LIMIT))
    earnings_limit = float(_limit_from_env("ANTI_FRAUD_DAILY_EARNINGS_RSD", ANTI_FRAUD_DAILY_EARNINGS_RSD))
    completed_today = db.query(TaskSubmission).filter(
        TaskSubmission.user_id == user.id,
        TaskSubmission.created_at >= today,
    ).count()
    daily_reward = float(db.query(func.coalesce(func.sum(TaskSubmission.reward_rsd), 0)).filter(
        TaskSubmission.user_id == user.id,
        TaskSubmission.created_at >= today,
    ).scalar() or 0)
    if completed_today >= task_limit:
        raise HTTPException(429, "Dnevni limit zadataka je dostignut. Pokušaj ponovo sutra.")
    if daily_reward + float(task.reward_rsd or 0) > earnings_limit:
        raise HTTPException(429, "Dnevni limit zarade je dostignut. Pokušaj ponovo sutra.")


@router.post("/user/tasks/{task_id}/verification/start", status_code=201)
def start_task_verification(task_id: int, payload: VerificationStartPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik", "admin"})
    task = db.query(Task).filter(Task.id == task_id, Task.status == "active", Task.used_slots < Task.total_slots).first()
    if not task:
        raise HTTPException(404, "Zadatak nije dostupan.")
    _verify_daily_limits(db, user, task)
    existing_submission = db.query(TaskSubmission).filter(
        TaskSubmission.user_id == user.id,
        TaskSubmission.task_id == task.id,
        TaskSubmission.status.in_(["pending", "approved"]),
    ).first()
    if existing_submission:
        raise HTTPException(409, "Za ovaj zadatak je već poslat dokaz.")

    now = datetime.utcnow()
    active_session = db.query(TaskVerificationSessionV1).filter(
        TaskVerificationSessionV1.user_id == user.id,
        TaskVerificationSessionV1.task_id == task.id,
        TaskVerificationSessionV1.status.in_(["started", "ready", "flagged"]),
        TaskVerificationSessionV1.started_at >= now - timedelta(hours=2),
    ).order_by(TaskVerificationSessionV1.started_at.desc()).first()
    if active_session:
        return {"session": _verification_data(active_session), "resumed": True}

    fingerprint_hash, network_hash, network_label = _record_fraud_device(
        db, user, request, payload.device_fingerprint, payload.device_label,
    )
    risk_score = _open_risk_score(db, user.id)
    if fingerprint_hash:
        linked_users = db.query(AntiFraudDeviceV1.user_id).filter(
            AntiFraudDeviceV1.fingerprint_hash == fingerprint_hash,
            AntiFraudDeviceV1.user_id != user.id,
        ).distinct().count()
        if linked_users:
            risk_score += 45.0
            _add_fraud_signal(db, user.id, "shared_device", 65, {
                "reason": "Isti uređaj je povezan sa više naloga.",
                "network": network_label,
                "linked_accounts": linked_users,
            })
    if network_hash:
        linked_network_users = db.query(AntiFraudDeviceV1.user_id).filter(
            AntiFraudDeviceV1.network_hash == network_hash,
            AntiFraudDeviceV1.user_id != user.id,
        ).distinct().count()
        if linked_network_users >= 3:
            risk_score += 25.0
            _add_fraud_signal(db, user.id, "shared_network", 35, {
                "reason": "Više naloga koristi istu mrežu; potreban je ručni pregled.",
                "network": network_label,
                "linked_accounts": linked_network_users,
            })
    proxy_score, proxy_note = _proxy_risk(request)
    if proxy_score:
        risk_score += proxy_score
        _add_fraud_signal(db, user.id, "vpn_proxy_risk", min(90.0, proxy_score + 30.0), {
            "reason": proxy_note or "Sumnjiv mrežni signal.",
            "network": network_label,
        })

    session = TaskVerificationSessionV1(
        token=uuid4().hex,
        user_id=user.id,
        task_id=task.id,
        fingerprint_hash=fingerprint_hash,
        network_hash=network_hash,
        network_label=network_label,
        user_agent=(request.headers.get("user-agent") or "")[:2000],
        required_seconds=_task_required_seconds(task),
        risk_score=min(100.0, risk_score),
        status="flagged" if risk_score >= ANTI_FRAUD_HIGH_RISK_SCORE else "started",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session": _verification_data(session), "resumed": False}


@router.post("/user/tasks/verification/heartbeat")
def task_verification_heartbeat(payload: VerificationHeartbeatPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik", "admin"})
    session = db.query(TaskVerificationSessionV1).filter(
        TaskVerificationSessionV1.token == payload.token,
        TaskVerificationSessionV1.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(404, "Sesija provere nije pronađena.")
    now = datetime.utcnow()
    if session.status == "submitted":
        raise HTTPException(409, "Sesija je već iskorišćena.")
    if session.started_at < now - timedelta(hours=2):
        session.status = "expired"
        db.commit()
        raise HTTPException(409, "Vreme za proveru je isteklo. Pokreni zadatak ponovo.")

    elapsed = max(0, int((now - (session.last_activity_at or session.started_at)).total_seconds()))
    # A single heartbeat may never add more than 15 seconds, so changing the
    # browser clock or sending one late request cannot skip the timer.
    if payload.visible and payload.activity_events > 0:
        session.active_seconds = min(session.required_seconds, session.active_seconds + min(elapsed, 15))
        session.activity_events = min(100_000, session.activity_events + payload.activity_events)
    else:
        session.inactive_heartbeats += 1
    if payload.focus_lost or not payload.visible:
        session.focus_loss_count += 1
    session.heartbeat_count += 1
    session.last_activity_at = now

    minimum_events = int(_limit_from_env("ANTI_FRAUD_MIN_ACTIVITY_EVENTS", ANTI_FRAUD_MIN_ACTIVITY_EVENTS))
    if session.inactive_heartbeats >= 8:
        session.risk_score = min(100.0, float(session.risk_score or 0) + 20.0)
        _add_fraud_signal(db, user.id, "inactive_task_session", 50, {
            "reason": "Timer je tekao bez dovoljno vidljive aktivnosti.",
            "session": session.token[:8],
        })
    if session.focus_loss_count >= 6:
        session.risk_score = min(100.0, float(session.risk_score or 0) + 20.0)
        _add_fraud_signal(db, user.id, "repeated_focus_loss", 45, {
            "reason": "Zadatak je više puta gubio fokus taba.",
            "session": session.token[:8],
        })
    if session.active_seconds >= session.required_seconds and session.activity_events >= minimum_events:
        session.status = "flagged" if session.risk_score >= ANTI_FRAUD_HIGH_RISK_SCORE else "ready"
        session.completed_at = now
    db.commit()
    db.refresh(session)
    return {"session": _verification_data(session)}


@router.post("/user/tasks/{task_id}/proof", status_code=201)
def submit_proof(task_id: int, payload: ProofPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik", "admin"})
    task = db.query(Task).filter(Task.id == task_id, Task.status == "active", Task.used_slots < Task.total_slots).first()
    if not task:
        raise HTTPException(404, "Zadatak nije dostupan.")
    existing = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id, TaskSubmission.task_id == task.id, TaskSubmission.status.in_(["pending", "approved"])).first()
    if existing:
        raise HTTPException(409, "Za ovaj zadatak je već poslat dokaz.")
    verification = db.query(TaskVerificationSessionV1).filter(
        TaskVerificationSessionV1.token == payload.verification_token,
        TaskVerificationSessionV1.user_id == user.id,
        TaskVerificationSessionV1.task_id == task.id,
        TaskVerificationSessionV1.status.in_(["ready", "flagged"]),
    ).first()
    minimum_events = int(_limit_from_env("ANTI_FRAUD_MIN_ACTIVITY_EVENTS", ANTI_FRAUD_MIN_ACTIVITY_EVENTS))
    if not verification or verification.active_seconds < verification.required_seconds or verification.activity_events < minimum_events:
        raise HTTPException(409, "Pre slanja dokaza završi proveru vremena i aktivnosti zadatka.")
    fee = _money(task.reward_rsd * (task.platform_fee_percent or PLATFORM_FEE_PERCENT) / 100)
    submission = TaskSubmission(user_id=user.id, task_id=task.id, proof=payload.proof.strip(), reward_rsd=task.reward_rsd, platform_fee_rsd=fee, advertiser_cost_rsd=_money(task.reward_rsd + fee), status="pending")
    task.used_slots += 1
    user.pending_rsd = _money(user.pending_rsd + task.reward_rsd)
    db.add(submission)
    db.flush()
    verification.status = "submitted"
    verification.submission_id = submission.id
    verification.completed_at = datetime.utcnow()
    if verification.risk_score >= ANTI_FRAUD_HIGH_RISK_SCORE:
        _add_fraud_signal(db, user.id, "high_risk_submission", verification.risk_score, {
            "reason": "Dokaz je poslat, ali zahteva obaveznu ručnu fraud proveru.",
            "submission_id": submission.id,
            "network": verification.network_label,
        })
    db.commit()
    db.refresh(submission)
    return {"submission": _submission_data(submission)}


@router.post("/user/withdrawals", status_code=201)
def request_withdrawal(payload: WithdrawalPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik", "admin"})
    if _open_risk_score(db, user.id) >= ANTI_FRAUD_HIGH_RISK_SCORE:
        raise HTTPException(403, "Isplata je privremeno na fraud proveri. Administrator će pregledati nalog.")
    if payload.amount_rsd < MIN_WITHDRAWAL_RSD:
        raise HTTPException(400, f"Minimalna isplata je {MIN_WITHDRAWAL_RSD:.0f} RSD.")
    if payload.amount_rsd > user.balance_rsd:
        raise HTTPException(400, "Nema dovoljno raspoloživog salda.")
    if payload.payment_method.strip().lower() != "paypal":
        raise HTTPException(400, "KlikZarada trenutno podržava isplate samo na PayPal email adresu.")
    recipient = _paypal_email(payload.payment_details)
    user.balance_rsd = _money(user.balance_rsd - payload.amount_rsd)
    user.payment_method = "PayPal"
    user.payment_details = recipient
    item = Withdrawal(user_id=user.id, amount_rsd=payload.amount_rsd, payment_method=user.payment_method, payment_details=user.payment_details, status="pending")
    db.add(item)
    db.add(WalletTransaction(user_id=user.id, amount_rsd=-payload.amount_rsd, tx_type="withdrawal_hold", description=f"Rezervisan zahtev za isplatu: {payload.amount_rsd:.0f} RSD"))
    db.commit()
    return {"withdrawal": {"id": item.id, "amount_rsd": _money(item.amount_rsd), "status": _status(item.status)}}


@router.get("/advertiser/dashboard")
def advertiser_dashboard(request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"oglasivac", "admin"})
    tasks = db.query(Task).filter(Task.advertiser_id == user.id).order_by(Task.created_at.desc()).limit(100).all()
    submissions = db.query(TaskSubmission).join(Task).filter(Task.advertiser_id == user.id).order_by(TaskSubmission.created_at.desc()).limit(100).all()
    transactions = db.query(AdvertiserBudgetTransaction).filter(AdvertiserBudgetTransaction.advertiser_id == user.id).order_by(AdvertiserBudgetTransaction.created_at.desc()).limit(100).all()
    return {
        "user": _user_data(user),
        "tasks": [_task_data(task) for task in tasks],
        "submissions": [_submission_data(submission) | {"user_name": submission.user.full_name if submission.user else "Korisnik"} for submission in submissions],
        "transactions": [{"id": tx.id, "amount_rsd": _money(tx.amount_rsd), "tx_type": tx.tx_type, "description": tx.description, "created_at": _iso(tx.created_at)} for tx in transactions],
        "pricing": _pricing_data(),
    }


@router.get("/advertiser/banners")
def advertiser_banners(request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"oglasivac", "admin"})
    _ensure_banner_slots(db)
    slots = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.is_active.is_(True)).order_by(HomeBannerSlotV111.price_rsd.desc()).all()
    banners = db.query(PaidAdBannerV111).filter(
        PaidAdBannerV111.advertiser_id == user.id,
    ).order_by(PaidAdBannerV111.created_at.desc()).limit(100).all()
    all_active_and_pending = db.query(PaidAdBannerV111).filter(
        PaidAdBannerV111.status.in_(("active", "pending")),
    ).all()
    visible_banners = [banner for banner in banners if not _is_legacy_demo_banner(banner)]
    visible_active_and_pending = [banner for banner in all_active_and_pending if not _is_legacy_demo_banner(banner)]
    return {
        "slots": [_banner_slot_data(slot, visible_active_and_pending) for slot in slots],
        "banners": [_banner_data(banner) for banner in visible_banners],
        "pricing": _pricing_data(),
    }


@router.post("/advertiser/banners", status_code=201)
def reserve_advertiser_banner(
    payload: BannerReservationPayload,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    user = _require_user(request, db, {"oglasivac", "admin"})
    _ensure_banner_slots(db)
    slot = db.query(HomeBannerSlotV111).filter(
        HomeBannerSlotV111.id == payload.slot_id,
        HomeBannerSlotV111.is_active.is_(True),
    ).with_for_update().first()
    if not slot:
        raise HTTPException(404, "Banner slot nije dostupan.")
    starts_at = datetime.utcnow()
    ends_at = starts_at + timedelta(days=payload.days_count)
    if _banner_slot_conflict(db, slot.id, starts_at, ends_at):
        raise HTTPException(409, "Ovaj slot je već rezervisan za traženi period.")
    target_url = _validate_banner_target_url(payload.target_url)
    image_url = _validate_banner_target_url(payload.image_url) if payload.image_url and payload.image_url.strip() else None
    price_rsd = _money(float(slot.price_rsd or 0) * payload.days_count / 7)
    if user.advertiser_budget_rsd < price_rsd:
        raise HTTPException(400, f"Nedovoljno budžeta. Za ovaj zakup potrebno je {price_rsd:.0f} RSD.")
    user.advertiser_budget_rsd = _money(user.advertiser_budget_rsd - price_rsd)
    user.advertiser_reserved_rsd = _money(user.advertiser_reserved_rsd + price_rsd)
    banner = PaidAdBannerV111(
        advertiser_id=user.id,
        slot_id=slot.id,
        title=payload.title.strip(),
        body=(payload.body or "").strip() or None,
        image_url=image_url,
        target_url=target_url,
        price_rsd=price_rsd,
        days_count=payload.days_count,
        status="pending",
        admin_note="Rezervacija čeka proveru administratora.",
        starts_at=starts_at,
        ends_at=ends_at,
    )
    db.add(banner)
    db.add(AdvertiserBudgetTransaction(
        advertiser_id=user.id,
        amount_rsd=-price_rsd,
        tx_type="reserve_banner",
        description=f"Rezervisan banner slot: {slot.title}",
    ))
    db.commit()
    db.refresh(banner)
    return {"banner": _banner_data(banner), "reserved_rsd": price_rsd}


def _paypal_config() -> tuple[str, str, str, Decimal]:
    """Read checkout credentials from environment, never from the database."""
    mode = os.getenv("PAYPAL_MODE", "").strip().lower()
    client_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
    rate_text = os.getenv("PAYPAL_RSD_PER_EUR", "").strip()
    if mode != "live":
        raise HTTPException(503, "PayPal Live nije aktiviran. Administrator mora postaviti PAYPAL_MODE=live u Renderu.")
    if not client_id or not client_secret:
        raise HTTPException(503, "PayPal Live kredencijali nisu podešeni u Renderu.")
    try:
        rate = Decimal(rate_text)
    except InvalidOperation as exc:
        raise HTTPException(503, "Kurs za PayPal nije podešen. Administrator mora postaviti PAYPAL_RSD_PER_EUR u Renderu.") from exc
    if rate <= 0:
        raise HTTPException(503, "Kurs za PayPal mora biti veći od nule.")
    return "https://api-m.paypal.com", client_id, client_secret, rate


def _paypal_payout_config() -> tuple[tuple[str, str, str, Decimal], str, Decimal]:
    """Return an explicitly enabled payout configuration.

    PayPal's supported-currency list does not include RSD, so platform ledger
    amounts are converted to EUR only after a human administrator confirms the
    payout. A dedicated payout rate keeps that financial decision auditable.
    """
    enabled = os.getenv("PAYPAL_PAYOUTS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        raise HTTPException(503, "PayPal Payouts nije uključen. Administrator mora postaviti PAYPAL_PAYOUTS_ENABLED=true u Renderu.")
    config = _paypal_config()
    currency = os.getenv("PAYPAL_PAYOUT_CURRENCY", "EUR").strip().upper()
    if currency != "EUR":
        raise HTTPException(503, "KlikZarada trenutno podržava samo EUR za PayPal isplate.")
    rate_text = os.getenv("PAYPAL_PAYOUT_RSD_PER_EUR", "").strip() or str(config[3])
    try:
        rate = Decimal(rate_text)
    except InvalidOperation as exc:
        raise HTTPException(503, "Kurs za PayPal isplatu nije podešen.") from exc
    if rate <= 0:
        raise HTTPException(503, "Kurs za PayPal isplatu mora biti veći od nule.")
    return config, currency, rate


def _paypal_payout_recipient(withdrawal: Withdrawal) -> str:
    if "paypal" not in (withdrawal.payment_method or "").lower():
        raise HTTPException(400, "Za PayPal isplatu korisnik mora izabrati PayPal kao metod isplate.")
    return _paypal_email(withdrawal.payment_details)


def _paypal_payout_data(attempt: PayPalPayoutAttempt) -> dict:
    return {
        "withdrawal_id": attempt.withdrawal_id,
        "paypal_batch_id": attempt.paypal_batch_id,
        "sender_batch_id": attempt.sender_batch_id,
        "amount_rsd": _money(attempt.amount_rsd),
        "amount_paypal": _money(attempt.amount_paypal),
        "currency": attempt.currency,
        "status": _status(attempt.status),
        "created_at": _iso(attempt.created_at),
        "updated_at": _iso(attempt.updated_at),
    }


def _paypal_card_checkout_enabled() -> bool:
    """Allow a controlled rollback while PayPal determines card eligibility."""
    return os.getenv("PAYPAL_CARD_PAYMENTS_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}


def _public_app_url(request: Request) -> str:
    configured = (os.getenv("PUBLIC_APP_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")
    if configured.startswith("https://"):
        return configured
    proto = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0].strip()
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "")).split(",")[0].strip()
    if not host:
        raise HTTPException(503, "Javni URL aplikacije nije podešen.")
    return f"{proto}://{host}"


def _paypal_access_token(config: tuple[str, str, str, Decimal]) -> str:
    base_url, client_id, client_secret, _ = config
    try:
        response = httpx.post(
            f"{base_url}/v1/oauth2/token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json", "Accept-Language": "sr_RS"},
            timeout=15,
        )
    except httpx.RequestError as exc:
        raise HTTPException(502, "PayPal trenutno nije dostupan. Pokušaj ponovo malo kasnije.") from exc
    if response.status_code >= 400:
        raise HTTPException(502, "PayPal Live kredencijali nisu prihvaćeni.")
    token = response.json().get("access_token")
    if not token:
        raise HTTPException(502, "PayPal nije vratio pristupni token.")
    return str(token)


def _paypal_get_order(config: tuple[str, str, str, Decimal], order_id: str) -> dict:
    base_url = config[0]
    try:
        response = httpx.get(
            f"{base_url}/v2/checkout/orders/{order_id}",
            headers={"Authorization": f"Bearer {_paypal_access_token(config)}", "Accept": "application/json"},
            timeout=15,
        )
    except httpx.RequestError as exc:
        raise HTTPException(502, "Nije moguće proveriti PayPal uplatu.") from exc
    if response.status_code >= 400:
        raise HTTPException(502, "PayPal nije potvrdio podatke o uplati.")
    return response.json()


def _paypal_capture_data(order: dict) -> tuple[str, Decimal] | None:
    try:
        capture = order["purchase_units"][0]["payments"]["captures"][0]
        if str(capture.get("status", "")).upper() != "COMPLETED":
            return None
        amount = capture["amount"]
        if amount.get("currency_code") != "EUR":
            return None
        return str(capture["id"]), Decimal(str(amount["value"]))
    except (IndexError, KeyError, TypeError, InvalidOperation):
        return None


def _complete_paypal_checkout(db: Session, checkout: PayPalCheckout, order: dict) -> bool:
    """Credit the advertiser once and only after validating PayPal's capture."""
    # A return redirect and a verified webhook can arrive together. Reloading
    # under a row lock makes the completed status authoritative in both paths.
    db.refresh(checkout, with_for_update=True)
    if checkout.status == "completed":
        return False
    capture = _paypal_capture_data(order)
    expected = Decimal(str(checkout.amount_eur)).quantize(Decimal("0.01"))
    if not capture or capture[1].quantize(Decimal("0.01")) != expected:
        checkout.status = "review_required"
        raise HTTPException(400, "PayPal potvrda nema očekivani iznos. Uplata nije knjižena i čeka proveru.")
    advertiser = db.query(User).filter(User.id == checkout.advertiser_id).with_for_update().first()
    if not advertiser:
        checkout.status = "review_required"
        raise HTTPException(404, "Oglašivač za ovu uplatu više ne postoji.")
    checkout.paypal_capture_id = capture[0]
    checkout.status = "completed"
    checkout.captured_at = datetime.utcnow()
    advertiser.advertiser_budget_rsd = _money(advertiser.advertiser_budget_rsd + checkout.amount_rsd)
    db.add(AdvertiserBudgetTransaction(
        advertiser_id=advertiser.id,
        amount_rsd=checkout.amount_rsd,
        tx_type="paypal_live_topup",
        description=f"PayPal Live uplata ({checkout.paypal_order_id})",
    ))
    return True


def _capture_paypal_checkout(db: Session, checkout: PayPalCheckout) -> bool:
    config = _paypal_config()
    if not checkout.paypal_order_id:
        raise HTTPException(400, "PayPal nalog nije pronađen.")
    if checkout.status == "completed":
        return False
    base_url = config[0]
    try:
        response = httpx.post(
            f"{base_url}/v2/checkout/orders/{checkout.paypal_order_id}/capture",
            headers={
                "Authorization": f"Bearer {_paypal_access_token(config)}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "PayPal-Request-Id": checkout.capture_request_id,
            },
            timeout=20,
        )
    except httpx.RequestError as exc:
        raise HTTPException(502, "PayPal trenutno nije dostupan. Pokušaj ponovo malo kasnije.") from exc
    # A retried browser redirect can report an already-captured order. Fetching
    # the order makes the operation idempotent instead of crediting twice.
    if response.status_code in {200, 201}:
        order = response.json()
    elif response.status_code == 422:
        order = _paypal_get_order(config, checkout.paypal_order_id)
    else:
        raise HTTPException(400, "PayPal nije odobrio uplatu. Budžet nije promenjen.")
    return _complete_paypal_checkout(db, checkout, order)


@router.post("/advertiser/paypal/orders", status_code=201)
def create_paypal_order(payload: PayPalTopupPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    advertiser = _require_user(request, db, {"oglasivac", "admin"})
    config = _paypal_config()
    amount_rsd = Decimal(str(payload.amount_rsd)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    amount_eur = (amount_rsd / config[3]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amount_eur < Decimal("1.00"):
        raise HTTPException(400, "Minimalna PayPal uplata je protivvrednost od 1 EUR.")

    checkout = PayPalCheckout(
        advertiser_id=advertiser.id,
        request_id=str(uuid4()),
        capture_request_id=str(uuid4()),
        amount_rsd=float(amount_rsd),
        amount_eur=float(amount_eur),
        exchange_rate=float(config[3]),
        status="creating",
    )
    db.add(checkout)
    db.flush()
    order_payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "custom_id": f"kz-topup:{checkout.id}",
            "invoice_id": f"KZ-{checkout.id}",
            "description": "KlikZarada oglašivački budžet",
            "amount": {"currency_code": "EUR", "value": f"{amount_eur:.2f}"},
        }],
    }
    if payload.checkout_flow == "redirect":
        public_url = _public_app_url(request)
        order_payload["payment_source"] = {"paypal": {"experience_context": {
            "brand_name": "KlikZarada",
            "landing_page": "LOGIN",
            "user_action": "PAY_NOW",
            "shipping_preference": "NO_SHIPPING",
            "return_url": f"{public_url}/api/ui/advertiser/paypal/return",
            "cancel_url": f"{public_url}/api/ui/advertiser/paypal/cancel",
        }}}
    try:
        response = httpx.post(
            f"{config[0]}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {_paypal_access_token(config)}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "PayPal-Request-Id": checkout.request_id,
            },
            json=order_payload,
            timeout=20,
        )
    except httpx.RequestError as exc:
        db.rollback()
        raise HTTPException(502, "PayPal trenutno nije dostupan. Pokušaj ponovo malo kasnije.") from exc
    if response.status_code not in {200, 201}:
        db.rollback()
        raise HTTPException(502, "PayPal nije uspeo da kreira nalog za uplatu.")
    order = response.json()
    approval_url = next((link.get("href") for link in order.get("links", []) if link.get("rel") in {"payer-action", "approve"}), None)
    if not order.get("id") or (payload.checkout_flow == "redirect" and not approval_url):
        db.rollback()
        raise HTTPException(502, "PayPal nije vratio podatke potrebne za plaćanje.")
    checkout.paypal_order_id = str(order["id"])
    checkout.status = "approved"
    db.commit()
    return {
        "order_id": checkout.paypal_order_id,
        "approval_url": approval_url,
        "amount_rsd": _money(float(amount_rsd)),
        "amount_eur": _money(float(amount_eur)),
        "exchange_rate": _money(float(config[3])),
    }


@router.get("/advertiser/paypal/checkout-config")
def paypal_checkout_config(request: Request, db: Session = Depends(get_db)) -> dict:
    """Expose only the browser-safe client ID used by PayPal's checkout SDK."""
    _require_user(request, db, {"oglasivac", "admin"})
    _, client_id, _, _ = _paypal_config()
    return {
        "client_id": client_id,
        "currency": "EUR",
        "card_checkout_enabled": _paypal_card_checkout_enabled(),
    }


@router.post("/advertiser/paypal/orders/{order_id}/capture")
def capture_paypal_order(order_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    """Complete an SDK-approved order after validating its advertiser ownership."""
    advertiser = _require_user(request, db, {"oglasivac", "admin"})
    checkout = db.query(PayPalCheckout).filter(
        PayPalCheckout.paypal_order_id == order_id,
        PayPalCheckout.advertiser_id == advertiser.id,
    ).first()
    if not checkout:
        raise HTTPException(404, "PayPal nalog za ovu uplatu nije pronađen.")
    try:
        credited = _capture_paypal_checkout(db, checkout)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    db.refresh(advertiser)
    return {
        "credited": credited,
        "advertiser_budget_rsd": _money(advertiser.advertiser_budget_rsd),
    }


@router.get("/advertiser/paypal/return")
def paypal_return(token: str, request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    advertiser = _require_user(request, db, {"oglasivac", "admin"})
    checkout = db.query(PayPalCheckout).filter(PayPalCheckout.paypal_order_id == token, PayPalCheckout.advertiser_id == advertiser.id).first()
    if not checkout:
        return RedirectResponse(f"{_public_app_url(request)}/oglasivac/panel?payment=error", status_code=303)
    try:
        _capture_paypal_checkout(db, checkout)
        db.commit()
        result = "success"
    except HTTPException:
        db.rollback()
        result = "error"
    return RedirectResponse(f"{_public_app_url(request)}/oglasivac/panel?payment={result}", status_code=303)


@router.get("/advertiser/paypal/cancel")
def paypal_cancel(request: Request) -> RedirectResponse:
    return RedirectResponse(f"{_public_app_url(request)}/oglasivac/panel?payment=cancelled", status_code=303)


@router.post("/paypal/webhook", status_code=204)
async def paypal_webhook(request: Request, db: Session = Depends(get_db)) -> Response:
    """Verify PayPal webhooks before using them as a secondary confirmation."""
    config = _paypal_config()
    webhook_id = os.getenv("PAYPAL_WEBHOOK_ID", "").strip()
    if not webhook_id:
        raise HTTPException(503, "PayPal webhook nije podešen.")
    raw_body = await request.body()
    try:
        event = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "Neispravan PayPal webhook.") from exc
    required_headers = {
        "auth_algo": request.headers.get("paypal-auth-algo"),
        "cert_url": request.headers.get("paypal-cert-url"),
        "transmission_id": request.headers.get("paypal-transmission-id"),
        "transmission_sig": request.headers.get("paypal-transmission-sig"),
        "transmission_time": request.headers.get("paypal-transmission-time"),
    }
    if not all(required_headers.values()):
        raise HTTPException(400, "Nedostaju PayPal webhook zaglavlja.")
    verification_payload = required_headers | {"webhook_id": webhook_id, "webhook_event": event}
    try:
        response = httpx.post(
            f"{config[0]}/v1/notifications/verify-webhook-signature",
            headers={"Authorization": f"Bearer {_paypal_access_token(config)}", "Content-Type": "application/json"},
            json=verification_payload,
            timeout=20,
        )
    except httpx.RequestError as exc:
        raise HTTPException(502, "PayPal webhook provera trenutno nije dostupna.") from exc
    if response.status_code >= 400 or response.json().get("verification_status") != "SUCCESS":
        raise HTTPException(400, "PayPal webhook potpis nije validan.")
    if event.get("event_type") != "PAYMENT.CAPTURE.COMPLETED":
        return Response(status_code=204)
    related = event.get("resource", {}).get("supplementary_data", {}).get("related_ids", {})
    order_id = related.get("order_id")
    if not order_id:
        return Response(status_code=204)
    checkout = db.query(PayPalCheckout).filter(PayPalCheckout.paypal_order_id == str(order_id)).with_for_update().first()
    if not checkout or checkout.status == "completed":
        return Response(status_code=204)
    _complete_paypal_checkout(db, checkout, _paypal_get_order(config, str(order_id)))
    db.commit()
    return Response(status_code=204)


@router.post("/advertiser/campaigns", status_code=201)
def create_campaign(payload: CampaignPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"oglasivac", "admin"})
    category = payload.category.strip()
    if category not in _SAFE_CAMPAIGN_CATEGORIES:
        raise HTTPException(400, "Izaberi jednu od dozvoljenih kategorija zadatka.")
    total = _money(payload.reward_rsd * payload.total_slots * (1 + PLATFORM_FEE_PERCENT / 100))
    if user.advertiser_budget_rsd < total:
        raise HTTPException(400, f"Nedovoljno budžeta. Potrebno je {total:.0f} RSD.")
    task = Task(advertiser_id=user.id, title=payload.title.strip(), category=category, task_type=payload.task_type.strip(), target_url=(payload.target_url or "").strip() or None, description=payload.description.strip(), instructions=payload.instructions.strip(), proof_required=payload.proof_required.strip(), reward_rsd=payload.reward_rsd, platform_fee_percent=PLATFORM_FEE_PERCENT, total_slots=payload.total_slots, target_city=payload.target_city, target_age_group=payload.target_age_group, target_interests=payload.target_interests, status="pending")
    user.advertiser_budget_rsd = _money(user.advertiser_budget_rsd - total)
    user.advertiser_reserved_rsd = _money(user.advertiser_reserved_rsd + total)
    db.add(task)
    db.add(AdvertiserBudgetTransaction(advertiser_id=user.id, amount_rsd=-total, tx_type="reserve_campaign", description=f"Rezervisan budžet za kampanju: {task.title}"))
    db.commit()
    db.refresh(task)
    return {"campaign": _task_data(task), "reserved_rsd": total}


@router.put("/advertiser/campaigns/{task_id}")
def revise_campaign(task_id: int, payload: CampaignPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    """Resubmit an admin-requested revision and reconcile its held budget."""
    user = _require_user(request, db, {"oglasivac", "admin"})
    task = db.query(Task).filter(Task.id == task_id, Task.advertiser_id == user.id).with_for_update().first()
    if not task:
        raise HTTPException(404, "Kampanja nije pronađena.")
    if task.status != "needs_revision":
        raise HTTPException(409, "Samo kampanja vraćena na doradu može ponovo da se pošalje.")
    category = payload.category.strip()
    if category not in _SAFE_CAMPAIGN_CATEGORIES:
        raise HTTPException(400, "Izaberi jednu od dozvoljenih kategorija zadatka.")
    if payload.total_slots < int(task.used_slots or 0):
        raise HTTPException(400, "Broj mesta ne može biti manji od već odobrenih izvršenja.")

    fee_percent = float(task.platform_fee_percent or PLATFORM_FEE_PERCENT)
    old_total = _money(task.reward_rsd * task.total_slots * (1 + fee_percent / 100))
    new_total = _money(payload.reward_rsd * payload.total_slots * (1 + fee_percent / 100))
    difference = _money(new_total - old_total)
    if difference > 0 and user.advertiser_budget_rsd < difference:
        raise HTTPException(400, f"Nedovoljno budžeta za izmenu. Potrebno je još {difference:.0f} RSD.")
    user.advertiser_budget_rsd = _money(user.advertiser_budget_rsd - difference)
    user.advertiser_reserved_rsd = _money(max(0, user.advertiser_reserved_rsd + difference))
    task.title = payload.title.strip()
    task.category = category
    task.task_type = payload.task_type.strip()
    task.target_url = (payload.target_url or "").strip() or None
    task.description = payload.description.strip()
    task.instructions = payload.instructions.strip()
    task.proof_required = payload.proof_required.strip()
    task.reward_rsd = payload.reward_rsd
    task.total_slots = payload.total_slots
    task.target_city = payload.target_city
    task.target_age_group = payload.target_age_group
    task.target_interests = payload.target_interests
    task.status = "pending"
    task.moderation_note = "Izmenjena kampanja ponovo čeka administrativnu proveru."
    if difference:
        db.add(AdvertiserBudgetTransaction(
            advertiser_id=user.id,
            amount_rsd=-difference,
            tx_type="revise_campaign_reservation",
            description=f"Izmenjen rezervisani budžet za kampanju: {task.title}",
        ))
    db.commit()
    db.refresh(task)
    return {"campaign": _task_data(task), "reserved_rsd": new_total}


def _admin_dashboard_data(db: Session) -> dict:
    pending_submissions = db.query(TaskSubmission).filter(TaskSubmission.status == "pending").count()
    pending_withdrawals = db.query(Withdrawal).filter(Withdrawal.status == "pending").count()
    pending_campaigns = db.query(Task).filter(Task.status == "pending").count()
    pending_banners = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.status == "pending").count()
    return {
        "metrics": {
            "users": db.query(User).filter(User.role == "korisnik").count(),
            "advertisers": db.query(User).filter(User.role == "oglasivac").count(),
            "active_tasks": db.query(Task).filter(Task.status == "active").count(),
            "pending_submissions": pending_submissions,
            "pending_withdrawals": pending_withdrawals,
            "pending_campaigns": pending_campaigns,
            "pending_banners": pending_banners,
            "reserved_budget_rsd": _money(db.query(func.coalesce(func.sum(User.advertiser_reserved_rsd), 0)).scalar()),
        }
    }


@router.get("/admin/dashboard")
def admin_dashboard(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    return _admin_dashboard_data(db)


@router.get("/admin/banners")
def admin_banners(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    _ensure_banner_slots(db)
    slots = db.query(HomeBannerSlotV111).order_by(HomeBannerSlotV111.price_rsd.desc()).all()
    banners = db.query(PaidAdBannerV111).order_by(PaidAdBannerV111.created_at.desc()).limit(300).all()
    visible_banners = [banner for banner in banners if not _is_legacy_demo_banner(banner)]
    return {
        "slots": [_banner_slot_data(slot, visible_banners) for slot in slots],
        "banners": [_banner_data(banner) for banner in visible_banners],
        "pricing": _pricing_data(),
    }


@router.patch("/admin/banners/{banner_id}")
def review_admin_banner(
    banner_id: int,
    payload: AdminBannerStatusPayload,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    admin = _require_user(request, db, {"admin"})
    banner = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.id == banner_id).with_for_update().first()
    if not banner:
        raise HTTPException(404, "Banner nije pronađen.")
    if banner.status != "pending":
        raise HTTPException(409, "Samo banner koji čeka proveru može biti obrađen.")
    advertiser = db.query(User).filter(User.id == banner.advertiser_id).with_for_update().first()
    if not advertiser:
        raise HTTPException(404, "Oglašivač banera nije pronađen.")
    amount = _money(banner.price_rsd)
    if payload.status == "active":
        advertiser.advertiser_reserved_rsd = _money(max(0, advertiser.advertiser_reserved_rsd - amount))
        advertiser.advertiser_spent_rsd = _money(advertiser.advertiser_spent_rsd + amount)
        banner.status = "active"
        banner.starts_at = datetime.utcnow()
        banner.ends_at = banner.starts_at + timedelta(days=max(1, banner.days_count or 7))
        banner.admin_note = (payload.note or "").strip() or "Zakup je odobren."
        db.add(AdvertiserBudgetTransaction(
            advertiser_id=advertiser.id,
            amount_rsd=0,
            tx_type="activate_banner",
            description=f"Odobren banner zakup: {banner.title}",
        ))
    else:
        advertiser.advertiser_reserved_rsd = _money(max(0, advertiser.advertiser_reserved_rsd - amount))
        advertiser.advertiser_budget_rsd = _money(advertiser.advertiser_budget_rsd + amount)
        banner.status = "rejected"
        banner.admin_note = (payload.note or "").strip() or "Zakup je odbijen, rezervisani budžet je vraćen."
        db.add(AdvertiserBudgetTransaction(
            advertiser_id=advertiser.id,
            amount_rsd=amount,
            tx_type="release_banner_reservation",
            description=f"Vraćen budžet za odbijen banner: {banner.title}",
        ))
    _audit(db, admin, "banner_review", "PaidAdBannerV111", banner.id, banner.status)
    db.commit()
    db.refresh(banner)
    return {"banner": _banner_data(banner)}


@router.get("/admin/users")
def admin_users(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    users = db.query(User).order_by(User.created_at.desc()).limit(300).all()
    return {"users": [_user_data(user) | {"created_at": _iso(user.created_at)} for user in users]}


@router.patch("/admin/users/{user_id}")
def update_user_status(user_id: int, payload: AdminStatusPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    admin = _require_user(request, db, {"admin"})
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Korisnik nije pronađen.")
    allowed = {"active", "blocked", "suspended"}
    if payload.status not in allowed:
        raise HTTPException(400, "Nevažeći status korisnika.")
    user.status = payload.status
    _audit(db, admin, "user_status_update", "User", user.id, payload.note or payload.status)
    db.commit()
    return {"user": _user_data(user)}


@router.get("/admin/campaigns")
def admin_campaigns(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    tasks = db.query(Task).order_by(Task.created_at.desc()).limit(300).all()
    return {"campaigns": [_task_data(task) | {"advertiser_name": task.advertiser.full_name if task.advertiser else "Platforma"} for task in tasks]}


@router.patch("/admin/campaigns/{task_id}")
def update_campaign_status(task_id: int, payload: AdminStatusPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    admin = _require_user(request, db, {"admin"})
    task = db.query(Task).filter(Task.id == task_id).with_for_update().first()
    if not task:
        raise HTTPException(404, "Kampanja nije pronađena.")
    if payload.status not in {"active", "rejected", "paused", "needs_revision"}:
        raise HTTPException(400, "Nevažeći status kampanje.")
    if payload.status == "rejected" and task.status in {"pending", "needs_revision"} and task.advertiser_id:
        advertiser = db.query(User).filter(User.id == task.advertiser_id).with_for_update().first()
        if advertiser:
            held_amount = _money(task.reward_rsd * task.total_slots * (1 + (task.platform_fee_percent or PLATFORM_FEE_PERCENT) / 100))
            advertiser.advertiser_reserved_rsd = _money(max(0, advertiser.advertiser_reserved_rsd - held_amount))
            advertiser.advertiser_budget_rsd = _money(advertiser.advertiser_budget_rsd + held_amount)
            db.add(AdvertiserBudgetTransaction(
                advertiser_id=advertiser.id,
                amount_rsd=held_amount,
                tx_type="release_campaign_reservation",
                description=f"Vraćen budžet za odbijenu kampanju: {task.title}",
            ))
    task.status = payload.status
    task.moderation_note = (payload.note or "").strip() or (
        "Administrator traži izmenu kampanje pre odobrenja." if payload.status == "needs_revision" else None
    )
    _audit(db, admin, "campaign_status_update", "Task", task.id, payload.status)
    db.commit()
    return {"campaign": _task_data(task)}


@router.get("/admin/submissions")
def admin_submissions(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    submissions = db.query(TaskSubmission).order_by(TaskSubmission.created_at.desc()).limit(300).all()
    return {"submissions": [_submission_data(item) | {"user_name": item.user.full_name if item.user else "Korisnik"} for item in submissions]}


@router.patch("/admin/submissions/{submission_id}")
def review_submission(submission_id: int, payload: AdminStatusPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    admin = _require_user(request, db, {"admin"})
    submission = db.query(TaskSubmission).filter(TaskSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(404, "Dokaz nije pronađen.")
    if payload.status not in {"approved", "rejected"}:
        raise HTTPException(400, "Status dokaza mora biti approved ili rejected.")
    if submission.status != "pending":
        raise HTTPException(409, "Ovaj dokaz je već obrađen.")
    submission.status = payload.status
    submission.review_note = payload.note
    submission.reviewed_at = datetime.utcnow()
    user = submission.user
    if payload.status == "approved":
        user.pending_rsd = _money(user.pending_rsd - submission.reward_rsd)
        user.balance_rsd = _money(user.balance_rsd + submission.reward_rsd)
        user.lifetime_earned_rsd = _money(user.lifetime_earned_rsd + submission.reward_rsd)
        db.add(WalletTransaction(user_id=user.id, amount_rsd=submission.reward_rsd, tx_type="task_reward", description=f"Odobren zadatak: {submission.task.title}"))
        task = submission.task
        advertiser = task.advertiser if task else None
        if advertiser:
            advertiser_cost = _money(submission.advertiser_cost_rsd)
            advertiser.advertiser_reserved_rsd = _money(max(0, advertiser.advertiser_reserved_rsd - advertiser_cost))
            advertiser.advertiser_spent_rsd = _money(advertiser.advertiser_spent_rsd + advertiser_cost)
            db.add(AdvertiserBudgetTransaction(
                advertiser_id=advertiser.id,
                amount_rsd=0,
                tx_type="spend_campaign_result",
                description=f"Odobren rezultat kampanje: {task.title}",
            ))
    else:
        user.pending_rsd = _money(user.pending_rsd - submission.reward_rsd)
        if submission.task:
            submission.task.used_slots = max(0, int(submission.task.used_slots or 0) - 1)
    _audit(db, admin, "submission_review", "TaskSubmission", submission.id, payload.status)
    db.commit()
    return {"submission": _submission_data(submission)}


@router.get("/admin/withdrawals")
def admin_withdrawals(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    items = db.query(Withdrawal).order_by(Withdrawal.created_at.desc()).limit(300).all()
    attempts = {
        item.withdrawal_id: item for item in db.query(PayPalPayoutAttempt).filter(
            PayPalPayoutAttempt.withdrawal_id.in_([withdrawal.id for withdrawal in items] or [-1])
        ).all()
    }
    return {"withdrawals": [{
        "id": item.id,
        "user_name": item.user.full_name if item.user else "Korisnik",
        "amount_rsd": _money(item.amount_rsd),
        "payment_method": item.payment_method,
        "payment_details": item.payment_details,
        "status": _status(item.status),
        "created_at": _iso(item.created_at),
        "paypal_payout": _paypal_payout_data(attempts[item.id]) if item.id in attempts else None,
    } for item in items]}


@router.get("/admin/tickets")
def admin_tickets(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    tickets = db.query(SupportTicket).order_by(SupportTicket.updated_at.desc()).limit(300).all()
    return {"tickets": [_ticket_data(ticket) for ticket in tickets]}


@router.patch("/admin/tickets/{ticket_id}")
def update_admin_ticket(ticket_id: int, payload: AdminStatusPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    admin = _require_user(request, db, {"admin"})
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Tiket nije pronađen.")
    if payload.status not in {"open", "waiting", "closed"}:
        raise HTTPException(400, "Status tiketa mora biti open, waiting ili closed.")
    ticket.status = payload.status
    ticket.updated_at = datetime.utcnow()
    if payload.note:
        db.add(SupportMessage(ticket_id=ticket.id, sender_id=admin.id, body=payload.note.strip()))
    _audit(db, admin, "support_ticket_update", "SupportTicket", ticket.id, payload.status)
    db.commit()
    db.refresh(ticket)
    return {"ticket": _ticket_data(ticket)}


@router.patch("/admin/withdrawals/{withdrawal_id}")
def update_withdrawal(withdrawal_id: int, payload: AdminStatusPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    admin = _require_user(request, db, {"admin"})
    item = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    if not item:
        raise HTTPException(404, "Isplata nije pronađena.")
    if payload.status not in {"paid", "rejected"}:
        raise HTTPException(400, "Status isplate mora biti paid ili rejected.")
    if item.status not in {"pending", "payout_failed"}:
        raise HTTPException(409, "Ova isplata je već obrađena ili se još obrađuje preko PayPal-a.")
    if payload.status == "paid" and item.status != "pending":
        raise HTTPException(409, "Neuspelu PayPal isplatu možeš odbiti i vratiti saldo, ali je ne smeš ručno označiti kao plaćenu.")
    if payload.status == "paid" and _open_risk_score(db, item.user_id) >= ANTI_FRAUD_HIGH_RISK_SCORE:
        raise HTTPException(409, "Isplata ima otvoren visokorizični fraud signal. Prvo pregledaj signal ili odbij isplatu.")
    item.status = payload.status
    item.admin_note = payload.note
    item.processed_at = datetime.utcnow()
    if payload.status == "rejected":
        item.user.balance_rsd = _money(item.user.balance_rsd + item.amount_rsd)
        db.add(WalletTransaction(user_id=item.user_id, amount_rsd=item.amount_rsd, tx_type="withdrawal_return", description="Vraćena odbijena isplata"))
    _audit(db, admin, "withdrawal_review", "Withdrawal", item.id, payload.status)
    db.commit()
    return {"withdrawal": {"id": item.id, "status": _status(item.status)}}


@router.post("/admin/withdrawals/{withdrawal_id}/paypal-payout")
def send_paypal_payout(withdrawal_id: int, payload: PayPalPayoutPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    """Send exactly one PayPal payout after a deliberate, auditable admin action."""
    admin = _require_user(request, db, {"admin"})
    item = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).with_for_update().first()
    if not item:
        raise HTTPException(404, "Isplata nije pronađena.")
    if item.status != "pending":
        raise HTTPException(409, "Samo isplata na čekanju može biti poslata na PayPal.")
    expected_confirmation = f"PAYPAL-ISPLATA-{item.id}"
    if not hmac.compare_digest(payload.confirmation_code.strip().upper(), expected_confirmation):
        raise HTTPException(400, f"Potvrda mora biti tačno: {expected_confirmation}")
    if _open_risk_score(db, item.user_id) >= ANTI_FRAUD_HIGH_RISK_SCORE:
        raise HTTPException(409, "Isplata ima otvoren visokorizični fraud signal. Prvo pregledaj signal.")

    config, currency, exchange_rate = _paypal_payout_config()
    recipient = _paypal_payout_recipient(item)
    amount_rsd = Decimal(str(item.amount_rsd)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    amount_paypal = (amount_rsd / exchange_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amount_paypal < Decimal("1.00"):
        raise HTTPException(400, "PayPal isplata mora iznositi najmanje 1,00 EUR po odobrenom kursu.")

    attempt = db.query(PayPalPayoutAttempt).filter(PayPalPayoutAttempt.withdrawal_id == item.id).with_for_update().first()
    if attempt and attempt.paypal_batch_id:
        raise HTTPException(409, "PayPal isplata je već poslata. Prvo osveži njen status.")
    if not attempt:
        attempt = PayPalPayoutAttempt(
            withdrawal_id=item.id,
            admin_id=admin.id,
            sender_batch_id=f"kz-w-{item.id}-{uuid4().hex[:16]}",
            recipient_email=recipient,
            amount_rsd=float(amount_rsd),
            amount_paypal=float(amount_paypal),
            currency=currency,
            status="created",
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
    else:
        # Retrying uses the original accounting values and sender batch ID.
        # PayPal treats that ID idempotently for 30 days.
        recipient = attempt.recipient_email
        amount_paypal = Decimal(str(attempt.amount_paypal)).quantize(Decimal("0.01"))
        currency = attempt.currency

    payout_payload = {
        "sender_batch_header": {
            "sender_batch_id": attempt.sender_batch_id,
            "recipient_type": "EMAIL",
            "email_subject": "KlikZarada isplata",
            "email_message": f"Isplata zahteva #{item.id} sa platforme KlikZarada.",
        },
        "items": [{
            "recipient_type": "EMAIL",
            "amount": {"value": f"{amount_paypal:.2f}", "currency": currency},
            "receiver": recipient,
            "note": f"KlikZarada isplata #{item.id}",
            "sender_item_id": f"withdrawal-{item.id}",
        }],
    }
    try:
        response = httpx.post(
            f"{config[0]}/v1/payments/payouts",
            headers={
                "Authorization": f"Bearer {_paypal_access_token(config)}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "PayPal-Request-Id": attempt.sender_batch_id,
            },
            json=payout_payload,
            timeout=25,
        )
    except httpx.RequestError as exc:
        attempt.status = "retryable_error"
        attempt.response_summary = "Mrežna greška pri slanju PayPal zahteva. Isti batch ID može bezbedno da se pokuša ponovo."
        attempt.updated_at = datetime.utcnow()
        db.commit()
        raise HTTPException(502, "PayPal trenutno nije dostupan. Isplata nije označena kao plaćena.") from exc

    if response.status_code not in {200, 201, 202}:
        attempt.status = "retryable_error"
        attempt.response_summary = f"PayPal HTTP {response.status_code}"
        attempt.updated_at = datetime.utcnow()
        db.commit()
        raise HTTPException(502, "PayPal nije prihvatio isplatu. Sredstva nisu označena kao plaćena.")

    result = response.json()
    batch_header = result.get("batch_header") if isinstance(result, dict) else None
    batch_id = str((batch_header or {}).get("payout_batch_id") or "")
    batch_status = str((batch_header or {}).get("batch_status") or "PENDING").upper()
    if not batch_id:
        attempt.status = "review_required"
        attempt.response_summary = "PayPal odgovor nije sadržao payout_batch_id."
        attempt.updated_at = datetime.utcnow()
        db.commit()
        raise HTTPException(502, "PayPal odgovor nije potpun. Isplata ostaje na ručnoj proveri.")

    attempt.paypal_batch_id = batch_id
    attempt.status = _status(batch_status)
    attempt.response_summary = json.dumps({"batch_status": batch_status}, separators=(",", ":"))
    attempt.updated_at = datetime.utcnow()
    item.status = "processing"
    item.admin_note = f"PayPal batch {batch_id} je poslat i čeka potvrdu."
    _audit(db, admin, "paypal_payout_send", "Withdrawal", item.id, batch_id)
    db.commit()
    return {"withdrawal": {"id": item.id, "status": _status(item.status)}, "payout": _paypal_payout_data(attempt)}


@router.post("/admin/withdrawals/{withdrawal_id}/paypal-payout/sync")
def sync_paypal_payout(withdrawal_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    """Read the provider status; only PayPal SUCCESS marks a withdrawal paid."""
    admin = _require_user(request, db, {"admin"})
    item = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).with_for_update().first()
    attempt = db.query(PayPalPayoutAttempt).filter(PayPalPayoutAttempt.withdrawal_id == withdrawal_id).with_for_update().first()
    if not item or not attempt or not attempt.paypal_batch_id:
        raise HTTPException(404, "PayPal batch za ovu isplatu nije pronađen.")
    config, _, _ = _paypal_payout_config()
    try:
        response = httpx.get(
            f"{config[0]}/v1/payments/payouts/{attempt.paypal_batch_id}",
            params={"fields": "batch_header"},
            headers={"Authorization": f"Bearer {_paypal_access_token(config)}", "Accept": "application/json"},
            timeout=20,
        )
    except httpx.RequestError as exc:
        raise HTTPException(502, "PayPal status trenutno nije dostupan.") from exc
    if response.status_code >= 400:
        raise HTTPException(502, "PayPal nije vratio status isplate.")
    result = response.json()
    batch_status = str(result.get("batch_header", {}).get("batch_status") or "PENDING").upper()
    attempt.status = _status(batch_status)
    attempt.response_summary = json.dumps({"batch_status": batch_status}, separators=(",", ":"))
    attempt.updated_at = datetime.utcnow()
    if batch_status == "SUCCESS":
        item.status = "paid"
        item.processed_at = datetime.utcnow()
        item.admin_note = f"PayPal batch {attempt.paypal_batch_id} je uspešno potvrđen."
    elif batch_status in {"DENIED", "CANCELED"}:
        item.status = "payout_failed"
        item.admin_note = f"PayPal batch {attempt.paypal_batch_id} nije izvršen ({batch_status}). Odbij isplatu da bi se saldo vratio korisniku."
    else:
        item.status = "processing"
    _audit(db, admin, "paypal_payout_sync", "Withdrawal", item.id, batch_status)
    db.commit()
    return {"withdrawal": {"id": item.id, "status": _status(item.status)}, "payout": _paypal_payout_data(attempt)}


def _fraud_details(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {"note": value}
    except json.JSONDecodeError:
        return {"note": value}


@router.get("/admin/fraud/overview")
def admin_fraud_overview(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    signals = db.query(FraudSignalV11).order_by(
        FraudSignalV11.status.asc(), FraudSignalV11.risk_score.desc(), FraudSignalV11.created_at.desc(),
    ).limit(300).all()
    sessions = db.query(TaskVerificationSessionV1).order_by(TaskVerificationSessionV1.started_at.desc()).limit(200).all()
    devices = db.query(AntiFraudDeviceV1).order_by(AntiFraudDeviceV1.last_seen_at.desc()).limit(300).all()
    high_risk_users = {item.user_id for item in signals if item.status == "open" and float(item.risk_score or 0) >= ANTI_FRAUD_HIGH_RISK_SCORE and item.user_id}
    return {
        "policy": {
            "daily_task_limit": int(_limit_from_env("ANTI_FRAUD_DAILY_TASK_LIMIT", ANTI_FRAUD_DAILY_TASK_LIMIT)),
            "daily_earnings_rsd": float(_limit_from_env("ANTI_FRAUD_DAILY_EARNINGS_RSD", ANTI_FRAUD_DAILY_EARNINGS_RSD)),
            "minimum_activity_events": int(_limit_from_env("ANTI_FRAUD_MIN_ACTIVITY_EVENTS", ANTI_FRAUD_MIN_ACTIVITY_EVENTS)),
            "ip_reputation_enabled": bool(os.getenv("IPQUALITYSCORE_API_KEY", "").strip()),
        },
        "summary": {
            "open_signals": sum(1 for item in signals if item.status == "open"),
            "high_risk_users": len(high_risk_users),
            "flagged_sessions": sum(1 for item in sessions if item.status == "flagged"),
            "shared_devices": sum(1 for item in devices if db.query(AntiFraudDeviceV1.user_id).filter(AntiFraudDeviceV1.fingerprint_hash == item.fingerprint_hash).distinct().count() > 1),
        },
        "signals": [{
            "id": item.id,
            "user_id": item.user_id,
            "user_name": item.user.full_name if item.user else "Obrisan korisnik",
            "user_email": item.user.email if item.user else None,
            "signal_type": item.signal_type,
            "risk_score": _money(item.risk_score),
            "status": _status(item.status),
            "details": _fraud_details(item.details),
            "created_at": _iso(item.created_at),
        } for item in signals],
        "sessions": [{
            "id": item.id,
            "user_id": item.user_id,
            "user_name": item.user.full_name if item.user else "Korisnik",
            "task_title": item.task.title if item.task else "Zadatak",
            "network": item.network_label,
            "active_seconds": item.active_seconds,
            "required_seconds": item.required_seconds,
            "activity_events": item.activity_events,
            "focus_loss_count": item.focus_loss_count,
            "risk_score": _money(item.risk_score),
            "status": _status(item.status),
            "started_at": _iso(item.started_at),
        } for item in sessions],
        "devices": [{
            "id": item.id,
            "user_id": item.user_id,
            "user_name": item.user.full_name if item.user else "Korisnik",
            "network": item.network_label,
            "device": item.device_label or "Nepoznat uređaj",
            "last_seen_at": _iso(item.last_seen_at),
        } for item in devices],
    }


@router.patch("/admin/fraud/signals/{signal_id}")
def review_fraud_signal(signal_id: int, payload: AdminStatusPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    admin = _require_user(request, db, {"admin"})
    signal = db.query(FraudSignalV11).filter(FraudSignalV11.id == signal_id).first()
    if not signal:
        raise HTTPException(404, "Fraud signal nije pronađen.")
    if payload.status not in {"reviewed", "dismissed"}:
        raise HTTPException(400, "Signal može biti označen kao reviewed ili dismissed.")
    signal.status = payload.status
    if payload.note:
        details = _fraud_details(signal.details)
        details["admin_note"] = payload.note.strip()
        signal.details = json.dumps(details, ensure_ascii=False, separators=(",", ":"))
    _audit(db, admin, "fraud_signal_review", "FraudSignalV11", signal.id, payload.status)
    db.commit()
    return {"signal": {"id": signal.id, "status": _status(signal.status)}}


@router.get("/admin/task-sources")
def admin_task_sources(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    sources = db.query(TaskSourceV11).order_by(TaskSourceV11.created_at.desc()).all()
    return {"sources": [{"id": source.id, "name": source.name, "endpoint_url": source.endpoint_url, "source_type": source.source_type, "import_mode": source.import_mode, "status": source.status, "has_api_key": bool(source.api_key), "last_sync_at": _iso(source.last_sync_at), "created_at": _iso(source.created_at)} for source in sources]}


@router.post("/admin/task-sources", status_code=201)
def create_task_source(payload: SourcePayload, request: Request, db: Session = Depends(get_db)) -> dict:
    admin = _require_user(request, db, {"admin"})
    _validate_public_https_endpoint(payload.endpoint_url)
    source = TaskSourceV11(name=payload.name.strip(), endpoint_url=payload.endpoint_url.strip(), api_key=(payload.api_key or "").strip() or None, source_type="partner_api", import_mode=payload.import_mode, status="active")
    db.add(source)
    db.flush()
    _audit(db, admin, "task_source_create", "TaskSourceV11", source.id, source.name)
    db.commit()
    return {"source": {"id": source.id, "name": source.name, "status": source.status}}


@router.post("/admin/task-sources/{source_id}/sync")
def sync_task_source(source_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    """Import a documented JSON feed into the moderation queue.

    Only JSON arrays or common list wrappers are accepted.  HTML/API
    documentation pages are rejected explicitly, rather than being scraped
    into fake tasks.
    """
    admin = _require_user(request, db, {"admin"})
    source = db.query(TaskSourceV11).filter(TaskSourceV11.id == source_id).first()
    if not source:
        raise HTTPException(404, "Izvor nije pronađen.")
    if source.status != "active":
        raise HTTPException(400, "Izvor nije aktivan.")
    try:
        headers = {"Accept": "application/json"}
        params = {"api_key": source.api_key} if source.api_key else None
        response = httpx.get(source.endpoint_url, headers=headers, params=params, timeout=15, follow_redirects=False)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "Partner API nije vratio validan JSON feed. Proveri endpoint i format izvora.") from exc
    items = payload if isinstance(payload, list) else next((payload.get(key) for key in ("tasks", "items", "results", "data") if isinstance(payload, dict) and isinstance(payload.get(key), list)), None)
    if not items:
        raise HTTPException(422, "JSON nema listu zadataka. Očekuju se tasks, items, results ili data.")
    created = 0
    skipped = 0
    for item in items[:500]:
        if not isinstance(item, dict):
            skipped += 1
            continue
        title = str(item.get("title") or item.get("name") or "").strip()
        description = str(item.get("description") or item.get("text") or title).strip()
        reward = item.get("reward_rsd", item.get("reward", item.get("amount", 0)))
        try:
            reward_value = float(str(reward).replace(",", "."))
        except (TypeError, ValueError):
            reward_value = 0
        if not title or not description or reward_value <= 0:
            skipped += 1
            continue
        try:
            slots = max(1, int(float(item.get("total_slots") or item.get("slots") or 1)))
            minutes = max(1, int(float(item.get("estimated_minutes") or item.get("minutes") or 5)))
        except (TypeError, ValueError):
            skipped += 1
            continue
        remote_id = str(item.get("id") or item.get("remote_id") or "").strip()
        marker = f"source:{source.id};remote:{remote_id}" if remote_id else f"source:{source.id};title:{title}"
        if db.query(Task).filter(Task.moderation_note == marker).first():
            skipped += 1
            continue
        task = Task(
            advertiser_id=admin.id,
            title=title[:220],
            category=str(item.get("category") or source.name)[:80],
            task_type=str(item.get("task_type") or item.get("type") or "partner_task")[:80],
            target_url=str(item.get("target_url") or item.get("url") or "").strip() or None,
            description=description[:5000],
            instructions=str(item.get("instructions") or description)[:5000],
            proof_required=str(item.get("proof_required") or "Pošaljite dokaz izvršenja.")[:5000],
            reward_rsd=reward_value,
            total_slots=slots,
            estimated_minutes=minutes,
            status="pending",
            moderation_note=marker,
        )
        db.add(task)
        created += 1
    source.last_sync_at = datetime.utcnow()
    _audit(db, admin, "task_source_sync", "TaskSourceV11", source.id, f"created={created}; skipped={skipped}")
    db.commit()
    return {"created": created, "skipped": skipped, "message": "Uvezeni zadaci čekaju moderaciju."}


@router.get("/admin/settings")
def admin_settings(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    _ensure_required_settings(db)
    settings = db.query(SystemSetting).order_by(SystemSetting.key).all()
    sensitive_keys = {"payment_provider_webhook_secret", "smtp_password", "partner_api_key"}
    return {"settings": [{
        "key": item.key,
        "value": "" if item.key in sensitive_keys else item.value,
        "has_value": bool(item.value) if item.key in sensitive_keys else None,
        "description": item.description,
        "sensitive": item.key in sensitive_keys,
    } for item in settings]}


@router.put("/admin/settings/{key}")
def update_admin_setting(key: str, payload: SettingPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    admin = _require_user(request, db, {"admin"})
    item = db.query(SystemSetting).filter(SystemSetting.key == key.strip()).first()
    if not item:
        raise HTTPException(404, "Podešavanje nije pronađeno.")
    sensitive_keys = {"payment_provider_webhook_secret", "smtp_password", "partner_api_key"}
    value = payload.value.strip()
    if item.key in sensitive_keys and not value:
        return {"setting": {"key": item.key, "has_value": bool(item.value), "sensitive": True}}
    item.value = value
    item.updated_at = datetime.utcnow()
    _audit(db, admin, "system_setting_update", "SystemSetting", item.id, item.key)
    db.commit()
    return {"setting": {"key": item.key, "value": "" if item.key in sensitive_keys else item.value, "has_value": bool(item.value) if item.key in sensitive_keys else None, "sensitive": item.key in sensitive_keys}}
