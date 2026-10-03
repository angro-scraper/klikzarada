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
import smtplib
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .database import get_db
from .login_guard import admin_identity_allowed, authenticate_login, throttle_public_action
from .analytics import PUBLIC_PAGEVIEW_PATHS, start_clean_pageview_measurement
from .models import (
    AppTesterDailyCheckin,
    AppTesterEnrollment,
    AdvertiserBudgetTransaction,
    AntiFraudDeviceV1,
    AuditLog,
    EmailOutboxV8,
    EmailVerificationTokenV11,
    FraudSignalV11,
    HomeBannerSlotV111,
    LaunchWaitlist,
    Notification,
    PasswordResetTokenV11,
    PayPalCheckout,
    PayPalPayoutAttempt,
    PaidAdBannerV111,
    PaidPromotionRequestV111,
    PublicFunnelEventV12,
    PublicFunnelFailureReasonV12,
    PlatformVisitV117,
    SystemErrorLogV11,
    SystemSetting,
    SupportMessage,
    SupportTicket,
    Task,
    TaskChatMessage,
    TaskSourceV11,
    TaskSubmission,
    TaskVerificationSessionV1,
    User,
    UserConsentV11,
    UserProgramRewardClaim,
    WalletTransaction,
    Withdrawal,
)
from .security import create_session_token, hash_password, is_legacy_session, make_referral_code, read_session_token, session_matches_user, verify_password


router = APIRouter(prefix="/api/ui", tags=["KlikZarada UI"])

# Internal operating margin for new advertiser campaigns. The advertiser UI
# presents the final required budget, not this internal allocation.
PLATFORM_FEE_PERCENT = 40.0
MIN_WITHDRAWAL_RSD = 1000.0
REFERRAL_INVITER_BONUS_RSD = 100.0
REFERRAL_JOINER_BONUS_RSD = 50.0
ANTI_FRAUD_DAILY_TASK_LIMIT = 20
ANTI_FRAUD_DAILY_EARNINGS_RSD = 2000.0
ANTI_FRAUD_MIN_ACTIVITY_EVENTS = 8
ANTI_FRAUD_HIGH_RISK_SCORE = 70.0

PROGRAM_REWARDS = {
    "today_3_proofs": 50.0,
    "week_5_proofs": 150.0,
    "first_active_referral": 200.0,
}
DAILY_REWARD_RSD = 10.0

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
    accept_terms: bool = False
    website: str | None = Field(default=None, max_length=200)


class PublicFunnelEventPayload(BaseModel):
    event_type: Literal["registration_opened", "registration_submitted", "registration_failed"]
    failure_reason: Literal[
        "email_taken", "phone_taken", "terms_missing", "invalid_phone",
        "invalid_referral", "validation", "network_error", "server_error", "request_error",
    ] | None = None


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
    company_name: str | None = Field(default=None, max_length=180)
    company_pib: str | None = Field(default=None, max_length=80)
    company_website: str | None = Field(default=None, max_length=300)
    company_activity: str | None = Field(default=None, max_length=160)


class PasswordChangePayload(BaseModel):
    current_password: str = Field(min_length=8, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class CampaignLifecyclePayload(BaseModel):
    action: Literal["pause", "resume", "stop"]


class WaitlistPayload(BaseModel):
    email: str = Field(min_length=5, max_length=160)


class PasswordResetRequestPayload(BaseModel):
    email: str = Field(min_length=5, max_length=160)


class PasswordResetConfirmPayload(BaseModel):
    token: str = Field(min_length=20, max_length=160)
    new_password: str = Field(min_length=8, max_length=200)


class EmailVerificationPayload(BaseModel):
    token: str = Field(min_length=20, max_length=160)


class OnboardingPayload(BaseModel):
    city: str | None = Field(default=None, max_length=100)
    age_group: str = Field(min_length=2, max_length=40)
    interests: list[str] = Field(default_factory=list, max_length=8)


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
    campaign_duration_days: int = Field(default=30, ge=1, le=365)
    target_city: str | None = Field(default="Srbija", max_length=100)
    target_age_group: str | None = Field(default="18+", max_length=40)
    target_interests: str | None = Field(default=None, max_length=2000)
    requires_tester_enrollment: bool = False
    tester_required_count: int = Field(default=12, ge=12, le=100000)
    tester_duration_days: int = Field(default=14, ge=14, le=31)
    tester_daily_minutes: int = Field(default=5, ge=1, le=60)
    tester_daily_reward_rsd: float = Field(default=0, ge=0)
    repeat_interval_hours: int = Field(default=0, ge=0, le=24 * 30)
    submission_deadline_hours: int = Field(default=24, ge=1, le=24 * 14)
    max_proof_revisions: int = Field(default=1, ge=0, le=3)
    min_quality_score: float = Field(default=0, ge=0, le=100)


class TesterEnrollmentPayload(BaseModel):
    testing_email: str = Field(min_length=5, max_length=160)


class TaskChatPayload(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class TesterEnrollmentStatusPayload(BaseModel):
    status: Literal["invited", "declined"]
    note: str | None = Field(default=None, max_length=1000)


class TesterCohortStartPayload(BaseModel):
    count: int | None = Field(default=None, ge=1, le=100000)


class TesterDailyCheckinPayload(BaseModel):
    note: str = Field(min_length=3, max_length=1000)


class BannerReservationPayload(BaseModel):
    slot_id: int
    title: str = Field(min_length=3, max_length=180)
    body: str | None = Field(default=None, max_length=1000)
    image_url: str | None = Field(default=None, max_length=500)
    target_url: str = Field(min_length=1, max_length=500)
    days_count: int = Field(default=7, ge=1, le=31)
    requested_start_at: datetime | None = None


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


class SupportTicketMessagePayload(BaseModel):
    body: str = Field(min_length=2, max_length=5000)


class AccountDeletionPayload(BaseModel):
    password: str = Field(min_length=1, max_length=256)
    confirmation: Literal["OBRIŠI NALOG"]


class PromotionPayload(BaseModel):
    task_id: int
    promotion_type: Literal["featured", "priority"]
    days_count: int = Field(default=7, ge=1, le=31)


class AdminPromotionStatusPayload(BaseModel):
    status: Literal["active", "rejected"]
    note: str | None = Field(default=None, max_length=1000)


class SettingPayload(BaseModel):
    value: str = Field(default="", max_length=5000)


class ClientErrorPayload(BaseModel):
    """Small, sanitized browser error report used to repair live user flows."""

    path: str = Field(min_length=1, max_length=300)
    message: str = Field(min_length=1, max_length=1000)
    stack: str | None = Field(default=None, max_length=4000)


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


def _is_platform_publisher(user: User | None) -> bool:
    """Platform-owned advertising is free, but user rewards remain real costs."""
    return bool(user and user.role == "admin")


def _invalid_city(value: str | None) -> bool:
    return bool(value and ("@" in value or "://" in value))


def _profile_city(value: str | None) -> str | None:
    city = (value or "").strip()
    if _invalid_city(city):
        raise HTTPException(400, "U polje Grad unesi naziv grada, ne email adresu ili link.")
    return city or None


def _user_data(user: User) -> dict:
    try:
        interests = json.loads(user.interests or "[]")
    except (TypeError, json.JSONDecodeError):
        interests = []
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "platform_publishing": _is_platform_publisher(user),
        "status": user.status,
        "level": user.level or "Bronza",
        "balance_rsd": _money(user.balance_rsd),
        "pending_rsd": _money(user.pending_rsd),
        "lifetime_earned_rsd": _money(user.lifetime_earned_rsd),
        "phone": user.phone,
        "email_verified": bool(user.email_verified),
        "phone_verified": bool(user.phone_verified),
        "city": None if _invalid_city(user.city) else user.city,
        "city_needs_correction": _invalid_city(user.city),
        "age_group": user.age_group,
        "interests": interests if isinstance(interests, list) else [],
        "payment_method": user.payment_method,
        "payment_details": user.payment_details,
        "company_name": user.company_name,
        "company_pib": user.company_pib,
        "company_website": user.company_website,
        "company_activity": user.company_activity,
        "advertiser_budget_rsd": _money(user.advertiser_budget_rsd),
        "advertiser_reserved_rsd": _money(user.advertiser_reserved_rsd),
        "advertiser_spent_rsd": _money(user.advertiser_spent_rsd),
        "referral_code": user.referral_code,
    }


def _new_referral_code(db: Session, full_name: str) -> str:
    """Keep referral links short, readable, and unique before a user is created."""
    for _ in range(12):
        candidate = make_referral_code(full_name)
        if not db.query(User.id).filter(User.referral_code == candidate).first():
            return candidate
    raise HTTPException(503, "Referral kod trenutno nije moguće generisati. Pokušaj ponovo.")


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
        "campaign_duration_days": task.campaign_duration_days or 30,
        "starts_at": _iso(task.starts_at),
        "ends_at": _iso(task.ends_at),
        "paused_at": _iso(task.paused_at),
        "stopped_at": _iso(task.stopped_at),
        "estimated_minutes": task.estimated_minutes,
        "repeat_interval_hours": max(0, int(task.repeat_interval_hours or 0)),
        "submission_deadline_hours": max(1, int(task.submission_deadline_hours or 24)),
        "max_proof_revisions": max(0, int(task.max_proof_revisions or 0)),
        "min_quality_score": _money(task.min_quality_score or 0),
        "min_user_level": task.min_user_level or "Bronza",
        "featured": bool(task.featured),
        "requires_tester_enrollment": bool(task.requires_tester_enrollment),
        "tester_required_count": task.tester_required_count or 12,
        "tester_duration_days": task.tester_duration_days or 14,
        "tester_daily_minutes": task.tester_daily_minutes or 5,
        "tester_daily_reward_rsd": _money(task.tester_daily_reward_rsd or 0),
        "platform_sponsored": _is_platform_publisher(task.advertiser),
        "status": _status(task.status),
        "moderation_note": task.moderation_note,
        "target_city": task.target_city,
        "target_age_group": task.target_age_group,
        "target_interests": task.target_interests,
        "created_at": _iso(task.created_at),
    }


def _campaign_remaining_reservation(task: Task) -> float:
    """Return only the still-held amount; pending/approved executions stay funded."""
    remaining_slots = max(0, int(task.total_slots or 0) - int(task.used_slots or 0))
    fee_percent = float(task.platform_fee_percent or PLATFORM_FEE_PERCENT)
    return _money(float(task.reward_rsd or 0) * remaining_slots * (1 + fee_percent / 100))


def _release_campaign_reservation(db: Session, task: Task, reason: str) -> float:
    """Release unused advertiser budget once, keeping spent and pending results covered."""
    advertiser = task.advertiser
    if not advertiser or _is_platform_publisher(advertiser):
        return 0.0
    amount = _campaign_remaining_reservation(task)
    if amount <= 0:
        return 0.0
    advertiser.advertiser_reserved_rsd = _money(max(0, float(advertiser.advertiser_reserved_rsd or 0) - amount))
    advertiser.advertiser_budget_rsd = _money(float(advertiser.advertiser_budget_rsd or 0) + amount)
    db.add(AdvertiserBudgetTransaction(
        advertiser_id=advertiser.id,
        amount_rsd=amount,
        tx_type="release_campaign_reservation",
        description=f"Vraćen neiskorišćen budžet ({reason}): {task.title}",
    ))
    return amount


def _ensure_campaign_schedules(db: Session) -> None:
    """Backfill the window for campaigns created before scheduling existed."""
    tasks = db.query(Task).filter(
        Task.status.in_(("active", "paused")),
        Task.starts_at.is_(None),
    ).with_for_update().all()
    if not tasks:
        return
    now = datetime.utcnow()
    for task in tasks:
        task.starts_at = task.created_at or now
        task.ends_at = task.starts_at + timedelta(days=max(1, int(task.campaign_duration_days or 30)))
        if task.status == "paused" and not task.paused_at:
            task.paused_at = now
    db.commit()


def _expire_campaigns(db: Session) -> None:
    """Finish elapsed campaigns and return the portion that was never allocated."""
    _ensure_campaign_schedules(db)
    now = datetime.utcnow()
    tasks = db.query(Task).filter(Task.status == "active", Task.ends_at.is_not(None), Task.ends_at <= now).with_for_update().all()
    if not tasks:
        return
    for task in tasks:
        released = _release_campaign_reservation(db, task, "istek kampanje")
        task.status = "expired"
        task.stopped_at = now
        task.moderation_note = f"Kampanja je automatski završena po isteku. Vraćeno: {released:.0f} RSD."
    db.commit()


def _tester_enrollment_data(item: AppTesterEnrollment, include_email: bool = False) -> dict:
    data = {
        "id": item.id,
        "task_id": item.task_id,
        "status": _status(item.status),
        "note": item.note,
        "cohort_number": item.cohort_number,
        "invited_at": _iso(item.invited_at),
        "created_at": _iso(item.created_at),
        "updated_at": _iso(item.updated_at),
    }
    if include_email:
        data |= {
            "user_id": item.user_id,
            "testing_email": item.testing_email,
            "user_name": item.user.full_name if item.user else "Korisnik",
            "account_email": item.user.email if item.user else None,
        }
    return data


def _tester_email_conflict(db: Session, email: str, user_id: int) -> bool:
    normalized = email.strip().lower()
    registered_to_other = db.query(User.id).filter(
        func.lower(User.email) == normalized, User.id != user_id,
    ).first()
    used_by_other = db.query(AppTesterEnrollment.id).filter(
        func.lower(AppTesterEnrollment.testing_email) == normalized,
        AppTesterEnrollment.user_id != user_id,
        AppTesterEnrollment.status.in_(("requested", "invited")),
    ).first()
    return bool(registered_to_other or used_by_other)


def _tester_checkin_data(item: AppTesterDailyCheckin) -> dict:
    return {
        "id": item.id,
        "user_id": item.user_id,
        "task_id": item.task_id,
        "day_number": item.day_number,
        "note": item.note,
        "reward_rsd": _money(item.reward_rsd),
        "status": _status(item.status),
        "review_note": item.review_note,
        "reviewed_at": _iso(item.reviewed_at),
        "checked_in_at": _iso(item.checked_in_at),
    }


def _tester_window_progress(task: Task, enrollment: AppTesterEnrollment | None, checkins: list[AppTesterDailyCheckin] | None = None) -> dict:
    """Expose user-declared progress without claiming visibility into app activity."""
    duration = task.tester_duration_days or 14
    started_at = enrollment.invited_at if enrollment and enrollment.status == "invited" else None
    checked_days = sorted({item.day_number for item in (checkins or []) if item.status in {"pending", "approved"}})
    current_day = 0
    if started_at:
        current_day = max(1, (datetime.utcnow().date() - started_at.date()).days + 1)
    return {
        "started": bool(started_at),
        "started_at": _iso(started_at),
        "current_day": min(current_day, duration),
        "days_elapsed": current_day,
        "duration_days": duration,
        "checkin_total": len(checked_days),
        "checked_days": checked_days,
        "can_check_in": bool(started_at and 1 <= current_day <= duration and current_day not in checked_days),
        "complete": len(checked_days) >= duration,
    }


def _submission_data(submission: TaskSubmission) -> dict:
    return {
        "id": submission.id,
        "user_id": submission.user_id,
        "task_id": submission.task_id,
        "task_title": submission.task.title if submission.task else "Zadatak",
        "proof": submission.proof,
        "status": _status(submission.status),
        "reward_rsd": _money(submission.reward_rsd),
        "review_note": submission.review_note,
        "revision_count": int(submission.revision_count or 0),
        "revision_due_at": _iso(submission.revision_due_at),
        "created_at": _iso(submission.created_at),
    }


def _latest_task_submission(db: Session, user_id: int, task_id: int) -> TaskSubmission | None:
    return db.query(TaskSubmission).filter(
        TaskSubmission.user_id == user_id,
        TaskSubmission.task_id == task_id,
    ).order_by(TaskSubmission.created_at.desc()).first()


def _task_access_error(task: Task, user: User, latest: TaskSubmission | None, now: datetime | None = None) -> str | None:
    """Return a user-safe reason when a task cannot be started again yet."""
    now = now or datetime.utcnow()
    if float(user.quality_score or 0) < float(task.min_quality_score or 0):
        return f"Za ovaj zadatak potreban je kvalitet izvršioca od najmanje {task.min_quality_score:.0f}%."
    if latest and latest.status == "needs_revision":
        if latest.revision_due_at and latest.revision_due_at < now:
            return "Rok za doradu dokaza je istekao."
        if int(latest.revision_count or 0) >= int(task.max_proof_revisions or 0):
            return "Iskorišćen je dozvoljeni broj dorada dokaza."
        return None
    if latest and latest.status == "pending":
        return "Dokaz za ovaj zadatak već čeka pregled."
    if latest and latest.status == "approved":
        repeat_hours = max(0, int(task.repeat_interval_hours or 0))
        if not repeat_hours:
            return "Ovaj zadatak možeš izvršiti samo jednom."
        available_at = (latest.reviewed_at or latest.created_at) + timedelta(hours=repeat_hours)
        if available_at > now:
            return f"Ovaj zadatak možeš ponovo izvršiti nakon {available_at.strftime('%d.%m. u %H:%M')}."
    if int(task.used_slots or 0) >= int(task.total_slots or 0):
        return "Sva mesta na ovom zadatku su već popunjena."
    return None


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
        "messages": [{
            "id": message.id,
            "body": message.body,
            "sender_name": message.sender.full_name if message.sender else "Podrška",
            "from_support": bool(message.sender and message.sender.role == "admin"),
            "created_at": _iso(message.created_at),
        } for message in sorted(ticket.messages, key=lambda item: item.created_at or datetime.min)],
    }


def _paypal_email(value: str | None) -> str:
    """Normalize the only payout destination the platform accepts."""
    recipient = (value or "").strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", recipient):
        raise HTTPException(400, "Unesi važeću PayPal email adresu za isplatu.")
    return recipient


_BANNER_SLOT_DEFAULTS = (
    ("home_top_wide", "Početna — veliki gornji banner", "home_top", "wide", 9500),
    ("home_top_left", "Početna — gornji levi premium banner", "home_top", "half", 5000),
    ("home_top_right", "Početna — gornji desni premium banner", "home_top", "half", 5000),
    ("home_mid_left", "Početna — srednji levi banner", "home_mid", "half", 5500),
    ("home_mid_right", "Početna — srednji desni banner", "home_mid", "half", 5500),
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
    # A short-lived `home_top` placeholder was superseded by the established
    # `home_top_wide` code. Remove it only when it has never held a booking.
    obsolete_slot = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code == "home_top").first()
    if obsolete_slot and not db.query(PaidAdBannerV111.id).filter(PaidAdBannerV111.slot_id == obsolete_slot.id).first():
        db.delete(obsolete_slot)
        db.commit()

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
        "platform_sponsored": _is_platform_publisher(banner.advertiser),
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
    scheduled_banners = [
        banner
        for banner in sorted(slot_banners, key=lambda item: item.starts_at or item.created_at or now)
        if banner.status in {"active", "pending"}
        and (banner.ends_at is None or banner.ends_at > now)
    ]
    schedule = [_banner_data(banner) for banner in scheduled_banners]
    next_available_at = now
    for banner in scheduled_banners:
        starts_at = banner.starts_at or banner.created_at or now
        ends_at = banner.ends_at or starts_at + timedelta(days=max(1, banner.days_count or 7))
        if starts_at <= next_available_at < ends_at:
            next_available_at = ends_at
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
        "is_available_now": not any(
            (banner.starts_at or banner.created_at or now) <= now < (banner.ends_at or (banner.starts_at or banner.created_at or now) + timedelta(days=max(1, banner.days_count or 7)))
            for banner in scheduled_banners
        ),
        "next_available_at": _iso(next_available_at),
    }


def _validate_banner_target_url(value: str) -> str:
    url = value.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(400, "Link banera mora biti pun http:// ili https:// URL.")
    return url


def _validate_banner_image_url(value: str) -> str:
    url = value.strip()
    if url.startswith("/api/ui/public/banner-files/"):
        return url
    return _validate_banner_target_url(url)


_BANNER_UPLOAD_DIR = Path(os.getenv("BANNER_UPLOAD_DIR", "app/static/uploads/banners"))
_BANNER_MAX_BYTES = 5 * 1024 * 1024
_BANNER_IMAGE_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def _banner_upload_url(filename: str) -> str:
    return f"/api/ui/public/banner-files/{filename}"


def _promotion_price(promotion_type: str, days_count: int) -> float:
    weekly_price = {"featured": 1200.0, "priority": 700.0}.get(promotion_type)
    if weekly_price is None:
        raise HTTPException(400, "Nepoznat tip promocije.")
    return _money(weekly_price * days_count / 7)


def _promotion_data(item: PaidPromotionRequestV111) -> dict:
    return {
        "id": item.id,
        "task_id": item.task_id,
        "task_title": item.task.title if item.task else item.title,
        "advertiser_id": item.advertiser_id,
        "platform_sponsored": _is_platform_publisher(item.advertiser),
        "advertiser_name": item.advertiser.company_name or item.advertiser.full_name if item.advertiser else "Oglašivač",
        "promotion_type": item.promotion_type,
        "price_rsd": _money(item.price_rsd),
        "days_count": item.days_count,
        "status": _banner_status(item.status),
        "admin_note": item.admin_note,
        "starts_at": _iso(item.starts_at),
        "ends_at": _iso(item.ends_at),
        "created_at": _iso(item.created_at),
    }


def _expire_promotions(db: Session) -> None:
    now = datetime.utcnow()
    expired = db.query(PaidPromotionRequestV111).filter(
        PaidPromotionRequestV111.status == "active",
        PaidPromotionRequestV111.ends_at.is_not(None),
        PaidPromotionRequestV111.ends_at <= now,
    ).all()
    if expired:
        for item in expired:
            item.status = "expired"
            item.admin_note = "Promocija je automatski istekla."
        db.commit()


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
    token = request.cookies.get("kz_session")
    user_id = read_session_token(token)
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    legacy_revoked = bool(is_legacy_session(token) and db.query(SystemSetting.id).filter(SystemSetting.key == f"legacy_session_revoked:{user.id}").first()) if user else False
    return user if user and user.status == "active" and admin_identity_allowed(user) and session_matches_user(token, user.password_hash, user.role, legacy_revoked) else None


def _revoke_legacy_sessions(db: Session, user_id: int) -> None:
    key = f"legacy_session_revoked:{user_id}"
    if not db.query(SystemSetting.id).filter(SystemSetting.key == key).first():
        db.add(SystemSetting(key=key, value="1", description="Stare sesije odjavljene nakon promene lozinke."))


def _valid_visitor_id(request: Request) -> str:
    visitor_id = request.cookies.get("kz_visitor_id") or ""
    return visitor_id if re.fullmatch(r"[A-Za-z0-9_-]{20,128}", visitor_id) else ""


def _record_public_funnel_event(
    db: Session,
    request: Request,
    event_type: str,
    user_id: int | None = None,
) -> bool:
    """Record a deduplicated browser funnel event without retaining PII."""
    visitor_id = _valid_visitor_id(request)
    if not visitor_id:
        return False
    now = datetime.utcnow()
    duplicate = db.query(PublicFunnelEventV12.id).filter(
        PublicFunnelEventV12.visitor_id == visitor_id,
        PublicFunnelEventV12.event_type == event_type,
        PublicFunnelEventV12.created_at >= now - timedelta(minutes=30),
    ).first()
    if duplicate:
        return False
    latest_landing = db.query(PublicFunnelEventV12).filter(
        PublicFunnelEventV12.visitor_id == visitor_id,
        PublicFunnelEventV12.event_type == "ad_landing",
        PublicFunnelEventV12.created_at >= now - timedelta(days=30),
    ).order_by(PublicFunnelEventV12.created_at.desc()).first()
    db.add(PublicFunnelEventV12(
        visitor_id=visitor_id,
        user_id=user_id,
        event_type=event_type,
        source=latest_landing.source if latest_landing else "direct",
        medium=latest_landing.medium if latest_landing else "",
        campaign=latest_landing.campaign if latest_landing else "",
        landing_path=latest_landing.landing_path if latest_landing else "",
        created_at=now,
    ))
    return True


def _record_public_funnel_failure_reason(
    db: Session,
    request: Request,
    reason: str,
) -> bool:
    """Store an aggregate-safe failure category, never a submitted form value."""
    visitor_id = _valid_visitor_id(request)
    if not visitor_id:
        return False
    now = datetime.utcnow()
    duplicate = db.query(PublicFunnelFailureReasonV12.id).filter(
        PublicFunnelFailureReasonV12.visitor_id == visitor_id,
        PublicFunnelFailureReasonV12.reason == reason,
        PublicFunnelFailureReasonV12.created_at >= now - timedelta(minutes=30),
    ).first()
    if duplicate:
        return False
    latest_landing = db.query(PublicFunnelEventV12).filter(
        PublicFunnelEventV12.visitor_id == visitor_id,
        PublicFunnelEventV12.event_type == "ad_landing",
        PublicFunnelEventV12.created_at >= now - timedelta(days=30),
    ).order_by(PublicFunnelEventV12.created_at.desc()).first()
    db.add(PublicFunnelFailureReasonV12(
        visitor_id=visitor_id,
        source=latest_landing.source if latest_landing else "direct",
        medium=latest_landing.medium if latest_landing else "",
        campaign=latest_landing.campaign if latest_landing else "",
        reason=reason,
        created_at=now,
    ))
    return True


def _require_user(request: Request, db: Session, roles: set[str] | None = None) -> User:
    user = _current_user(request, db)
    if not user:
        raise HTTPException(401, "Prijava je potrebna.")
    if roles and user.role not in roles:
        raise HTTPException(403, "Nemate pristup ovoj akciji.")
    return user


def _audit(db: Session, admin: User, action: str, entity_type: str, entity_id: int | None, details: str = "") -> None:
    db.add(AuditLog(admin_id=admin.id, action=action, entity_type=entity_type, entity_id=entity_id, reason=details))


def _public_app_url() -> str:
    return (os.getenv("PUBLIC_APP_URL") or "https://klikzarada.onrender.com").rstrip("/")


def _queue_email(db: Session, recipient_email: str, subject: str, body: str) -> EmailOutboxV8:
    item = EmailOutboxV8(
        recipient_email=recipient_email,
        subject=subject,
        body=body,
        status="queued",
    )
    db.add(item)
    return item


def _deliver_queued_email(db: Session, item_id: int) -> bool:
    """Deliver one queued email only when explicit SMTP configuration exists.

    Keeping the row queued without credentials makes deployment safe: no local
    fallback sender or hidden external service is used.
    """
    host = (os.getenv("SMTP_HOST") or "").strip()
    sender = (os.getenv("SMTP_SENDER") or os.getenv("SMTP_FROM") or "").strip()
    if not host or not sender:
        return False
    item = db.query(EmailOutboxV8).filter(EmailOutboxV8.id == item_id, EmailOutboxV8.status == "queued").first()
    if not item:
        return False
    try:
        message = EmailMessage()
        message["From"] = sender
        message["To"] = item.recipient_email
        message["Subject"] = item.subject
        message.set_content(item.body)
        port = int(os.getenv("SMTP_PORT") or "587")
        username = os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER") or sender
        password = os.getenv("SMTP_PASSWORD") or ""
        with smtplib.SMTP(host, port, timeout=12) as client:
            if (os.getenv("SMTP_USE_TLS") or "true").lower() not in {"0", "false", "no"}:
                client.starttls()
            if password:
                client.login(username, password)
            client.send_message(message)
        item.status = "sent"
        item.sent_at = datetime.utcnow()
        db.commit()
        return True
    except (OSError, smtplib.SMTPException, ValueError):
        # A scheduled worker or an admin retry can send the still-queued item.
        db.rollback()
        return False


def _queue_email_verification(db: Session, user: User) -> EmailOutboxV8:
    db.query(EmailVerificationTokenV11).filter(
        EmailVerificationTokenV11.user_id == user.id,
        EmailVerificationTokenV11.status == "pending",
    ).update({"status": "expired"}, synchronize_session=False)
    token = uuid4().hex + uuid4().hex
    db.add(EmailVerificationTokenV11(user_id=user.id, token=token, status="pending"))
    verify_url = f"{_public_app_url()}/prijava?verify={token}"
    return _queue_email(
        db,
        user.email,
        "Potvrdi email adresu za KlikZaradu",
        f"Zdravo {user.full_name},\n\nPotvrdi email adresu preko ovog linka (važi 48 sati):\n{verify_url}\n\nAko nisi ti kreirao/la nalog, ignoriši ovu poruku.",
    )


def _queue_password_reset(db: Session, user: User) -> EmailOutboxV8:
    db.query(PasswordResetTokenV11).filter(
        PasswordResetTokenV11.user_id == user.id,
        PasswordResetTokenV11.status == "pending",
    ).update({"status": "expired"}, synchronize_session=False)
    token = uuid4().hex + uuid4().hex
    db.add(PasswordResetTokenV11(user_id=user.id, token=token, status="pending"))
    reset_url = f"{_public_app_url()}/prijava?reset={token}"
    return _queue_email(
        db,
        user.email,
        "Reset lozinke za KlikZaradu",
        f"Zdravo {user.full_name},\n\nZa postavljanje nove lozinke otvori link u narednih 60 minuta:\n{reset_url}\n\nAko nisi tražio/la reset, ignoriši ovu poruku.",
    )


@router.get("/health")
def health() -> dict:
    return {"ok": True, "ui": "react"}


@router.get("/session")
def session(request: Request, db: Session = Depends(get_db)) -> dict:
    user = _current_user(request, db)
    return {"authenticated": bool(user), "user": _user_data(user) if user else None}


@router.get("/account/deletion-request")
def account_deletion_request_status(request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik", "oglasivac"})
    ticket = db.query(SupportTicket).filter(
        SupportTicket.user_id == user.id,
        SupportTicket.category == "account_deletion",
        SupportTicket.status.in_(("open", "waiting")),
    ).order_by(SupportTicket.id.desc()).first()
    return {"requested": ticket is not None, "requested_at": _iso(ticket.created_at) if ticket else None}


@router.post("/account/deletion-request", status_code=201)
def request_account_deletion(payload: AccountDeletionPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik", "oglasivac"})
    throttle_public_action(db, request, "account_deletion", user.email, 5, 15)
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(400, "Lozinka nije ispravna.")
    existing = db.query(SupportTicket).filter(
        SupportTicket.user_id == user.id,
        SupportTicket.category == "account_deletion",
        SupportTicket.status.in_(("open", "waiting")),
    ).order_by(SupportTicket.id.desc()).first()
    if existing:
        return {"requested": True, "requested_at": _iso(existing.created_at)}
    ticket = SupportTicket(
        user_id=user.id,
        subject="Zahtev za trajno brisanje naloga",
        category="account_deletion",
        priority="high",
        status="open",
    )
    db.add(ticket)
    db.flush()
    db.add(SupportMessage(
        ticket_id=ticket.id,
        sender_id=user.id,
        body="Tražim brisanje naloga i povezanih ličnih podataka. Proveriti otvorene isplate, kampanje i obavezno čuvanje finansijske evidencije pre završetka.",
    ))
    db.add(Notification(
        user_id=user.id,
        title="Zahtev za brisanje naloga je primljen",
        body="Zahtev je prosleđen na obradu. Nalog i sredstva nisu automatski obrisani. O ishodu ćeš dobiti obaveštenje.",
        status="unread",
    ))
    _audit(db, user, "account_deletion_requested", "SupportTicket", ticket.id)
    db.commit()
    return {"requested": True, "requested_at": _iso(ticket.created_at)}


@router.post("/account/role/correct-to-user")
def correct_account_role_to_user(request: Request, db: Session = Depends(get_db)) -> dict:
    """Let an accidentally-created advertiser account safely become a worker account."""
    user = _require_user(request, db, {"oglasivac"})
    has_campaigns = db.query(Task.id).filter(Task.advertiser_id == user.id).first() is not None
    has_budget_history = db.query(AdvertiserBudgetTransaction.id).filter(
        AdvertiserBudgetTransaction.advertiser_id == user.id,
    ).first() is not None
    balances = (
        float(user.advertiser_budget_rsd or 0),
        float(user.advertiser_reserved_rsd or 0),
        float(user.advertiser_spent_rsd or 0),
    )
    if has_campaigns or has_budget_history or any(abs(value) > 0.001 for value in balances):
        raise HTTPException(
            409,
            "Nalog sa kampanjama, budžetom ili uplatama ne može automatski promeniti ulogu. Obrati se podršci.",
        )
    user.role = "korisnik"
    user.advertiser_verified = False
    _audit(db, user, "self_role_correction_to_user", "User", user.id, "Accidental advertiser registration corrected by account owner.")
    db.add(Notification(
        user_id=user.id,
        title="Nalog je prebačen u korisnički režim",
        body="Sada možeš da otvaraš dostupne zadatke i šalješ dokaze.",
        status="unread",
    ))
    db.commit()
    db.refresh(user)
    return {"user": _user_data(user)}


@router.post("/account/role/enable-advertiser")
def enable_advertiser_workspace(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"korisnik"})
    raise HTTPException(409, "Korisnički i oglašivački nalog su odvojeni. Za kampanje otvori oglašivački nalog.")


@router.post("/analytics/funnel")
def track_public_funnel_event(payload: PublicFunnelEventPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    recorded = _record_public_funnel_event(db, request, payload.event_type)
    if payload.event_type == "registration_failed" and payload.failure_reason:
        recorded = _record_public_funnel_failure_reason(db, request, payload.failure_reason) or recorded
    if recorded:
        db.commit()
    return {"recorded": recorded}


@router.post("/auth/login")
def login(payload: Credentials, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    user = authenticate_login(db, payload.email, payload.password, request)
    response.set_cookie("kz_session", create_session_token(user.id, user.password_hash), httponly=True, samesite="lax", secure=_cookie_is_secure(request))
    return {"user": _user_data(user)}


@router.post("/auth/register", status_code=201)
def register(payload: Registration, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    email = payload.email.strip().lower()
    throttle_public_action(db, request, "registration", email, 5, 60)
    if payload.website:
        raise HTTPException(400, "Registracija nije uspela. Proveri podatke.")
    if not payload.accept_terms:
        raise HTTPException(400, "Moraš prihvatiti Uslove korišćenja i Politiku privatnosti.")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email adresa je već registrovana.")
    phone = "".join(character for character in (payload.phone or "") if character.isdigit() or character == "+")
    if phone and len(phone.replace("+", "")) < 7:
        raise HTTPException(400, "Ako unosiš telefon, broj mora imati najmanje 7 cifara.")
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
        referral_code=_new_referral_code(db, payload.full_name),
        referred_by_id=referrer.id if referrer else None,
        company_name=payload.full_name.strip() if payload.role == "oglasivac" and payload.advertiser_type == "business" else None,
    )
    db.add(user)
    db.flush()
    db.add(UserConsentV11(
        user_id=user.id,
        consent_type="terms_and_privacy",
        version="1.0",
        ip_address=_request_client_ip(request),
    ))
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
    verification_email = _queue_email_verification(db, user)
    db.add(Notification(
        user_id=user.id,
        title="Dobrodošao/la na KlikZaradu",
        body="Potvrdi email adresu i popuni kratak profil da bi dobijao/la relevantnije zadatke.",
        status="unread",
    ))
    _record_public_funnel_event(db, request, "registration_completed", user.id)
    db.commit()
    db.refresh(user)
    _deliver_queued_email(db, verification_email.id)
    response.set_cookie("kz_session", create_session_token(user.id, user.password_hash), httponly=True, samesite="lax", secure=_cookie_is_secure(request))
    return {"user": _user_data(user)}


@router.post("/auth/logout", status_code=204)
def logout() -> Response:
    response = Response(status_code=204)
    response.delete_cookie("kz_session")
    return response


@router.post("/auth/email-verification/confirm")
def confirm_email_verification(payload: EmailVerificationPayload, db: Session = Depends(get_db)) -> dict:
    item = db.query(EmailVerificationTokenV11).filter(
        EmailVerificationTokenV11.token == payload.token,
        EmailVerificationTokenV11.status == "pending",
    ).first()
    if not item or item.created_at < datetime.utcnow() - timedelta(hours=48):
        if item:
            item.status = "expired"
            db.commit()
        raise HTTPException(400, "Link za potvrdu emaila je nevažeći ili je istekao.")
    item.status = "used"
    item.used_at = datetime.utcnow()
    item.user.email_verified = True
    db.add(Notification(
        user_id=item.user_id,
        title="Email je potvrđen",
        body="Tvoj nalog je spreman za bezbednije korišćenje KlikZarade.",
        status="unread",
    ))
    db.commit()
    return {"verified": True}


@router.post("/auth/email-verification/resend")
def resend_email_verification(request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db)
    if user.email_verified:
        return {"queued": False, "already_verified": True}
    throttle_public_action(db, request, "email_verification", user.email, 3, 60)
    email = _queue_email_verification(db, user)
    db.commit()
    return {"queued": True, "delivered": _deliver_queued_email(db, email.id), "already_verified": False}


@router.post("/auth/password-reset/request")
def request_password_reset(payload: PasswordResetRequestPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    # Deliberately generic so this endpoint cannot be used to discover accounts.
    throttle_public_action(db, request, "password_reset", payload.email, 3, 60)
    user = db.query(User).filter(User.email == payload.email.strip().lower(), User.status == "active").first()
    if not user:
        return {"accepted": True}
    email = _queue_password_reset(db, user)
    db.commit()
    _deliver_queued_email(db, email.id)
    return {"accepted": True}


@router.post("/auth/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirmPayload, db: Session = Depends(get_db)) -> dict:
    item = db.query(PasswordResetTokenV11).filter(
        PasswordResetTokenV11.token == payload.token,
        PasswordResetTokenV11.status == "pending",
    ).first()
    if not item or item.created_at < datetime.utcnow() - timedelta(hours=1):
        if item:
            item.status = "expired"
            db.commit()
        raise HTTPException(400, "Link za reset lozinke je nevažeći ili je istekao.")
    if verify_password(payload.new_password, item.user.password_hash):
        raise HTTPException(400, "Nova lozinka mora biti različita od prethodne.")
    item.user.password_hash = hash_password(payload.new_password)
    _revoke_legacy_sessions(db, item.user_id)
    item.status = "used"
    item.used_at = datetime.utcnow()
    db.add(Notification(
        user_id=item.user_id,
        title="Lozinka je promenjena",
        body="Ako ovu promenu nisi ti napravio/la, odmah se javi podršci.",
        status="unread",
    ))
    db.commit()
    return {"reset": True}


@router.get("/public/tasks")
def public_tasks(db: Session = Depends(get_db)) -> dict:
    _expire_promotions(db)
    _expire_campaigns(db)
    now = datetime.utcnow()
    active_promotions = db.query(PaidPromotionRequestV111).filter(
        PaidPromotionRequestV111.status == "active",
        PaidPromotionRequestV111.starts_at <= now,
        PaidPromotionRequestV111.ends_at > now,
    ).all()
    promotion_by_task = {item.task_id: item for item in active_promotions if item.task_id}
    tasks = db.query(Task).filter(Task.status == "active", Task.used_slots < Task.total_slots).order_by(Task.reward_rsd.desc()).limit(100).all()
    payload = []
    for task in tasks:
        item = promotion_by_task.get(task.id)
        data = _task_data(task)
        data["sponsored"] = bool(item)
        data["promotion_type"] = item.promotion_type if item else None
        payload.append(data)
    payload.sort(key=lambda item: (0 if item.get("promotion_type") == "featured" else 1 if item.get("promotion_type") == "priority" else 2, -item["reward_rsd"]))
    return {"tasks": payload}


@router.get("/public/overview")
def public_overview(db: Session = Depends(get_db)) -> dict:
    """Return only aggregate, live platform figures suitable for the homepage."""
    _expire_campaigns(db)
    active_tasks = db.query(Task).filter(Task.status == "active", Task.used_slots < Task.total_slots)
    task_count = active_tasks.count()
    categories_count = db.query(func.count(func.distinct(Task.category))).filter(
        Task.status == "active", Task.used_slots < Task.total_slots,
    ).scalar() or 0
    advertiser_count = db.query(func.count(func.distinct(Task.advertiser_id))).filter(
        Task.status == "active", Task.used_slots < Task.total_slots,
    ).scalar() or 0
    average_minutes = db.query(func.avg(Task.estimated_minutes)).filter(
        Task.status == "active", Task.used_slots < Task.total_slots,
    ).scalar()
    approved_results = db.query(TaskSubmission).filter(TaskSubmission.status == "approved").count()
    return {
        "active_tasks": task_count,
        "categories": int(categories_count),
        "active_advertisers": int(advertiser_count),
        "approved_results": approved_results,
        "average_minutes": round(float(average_minutes or 0), 1),
    }


@router.post("/public/waitlist")
def join_waitlist(payload: WaitlistPayload, db: Session = Depends(get_db)) -> dict:
    email = payload.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(422, "Unesi ispravnu email adresu.")
    if db.query(LaunchWaitlist).filter(LaunchWaitlist.email == email).first():
        return {"saved": True, "already_registered": True}
    db.add(LaunchWaitlist(email=email))
    db.commit()
    return {"saved": True, "already_registered": False}


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


@router.post("/client-errors", status_code=204)
def record_client_error(payload: ClientErrorPayload, db: Session = Depends(get_db)) -> Response:
    """Keep production browser failures visible without storing form or account data."""
    path = " ".join(payload.path.split())[:300]
    message = " ".join(payload.message.split())[:1000]
    stack = " ".join((payload.stack or "").split())[:2000]
    details = f"path={path}; message={message}"
    if stack:
        details = f"{details}; stack={stack}"
    db.add(SystemErrorLogV11(level="error", source="browser", message=details, status="open"))
    db.commit()
    return Response(status_code=204)


def _program_data(db: Session, user: User) -> dict:
    """Return only server-calculated engagement progress for the signed-in user."""
    now = datetime.utcnow()
    today = now.date()
    today_start = datetime.combine(today, datetime.min.time())
    tomorrow_start = today_start + timedelta(days=1)
    week_start = today_start - timedelta(days=today.weekday())
    next_week_start = week_start + timedelta(days=7)

    submitted_total = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id).count()
    approved_total = db.query(TaskSubmission).filter(
        TaskSubmission.user_id == user.id,
        TaskSubmission.status == "approved",
    ).count()
    submitted_today = db.query(TaskSubmission).filter(
        TaskSubmission.user_id == user.id,
        TaskSubmission.created_at >= today_start,
        TaskSubmission.created_at < tomorrow_start,
    ).count()
    submitted_this_week = db.query(TaskSubmission).filter(
        TaskSubmission.user_id == user.id,
        TaskSubmission.created_at >= week_start,
        TaskSubmission.created_at < next_week_start,
    ).count()
    active_referrals = db.query(func.count(func.distinct(User.id))).join(
        TaskSubmission, TaskSubmission.user_id == User.id,
    ).filter(
        User.referred_by_id == user.id,
        TaskSubmission.status == "approved",
    ).scalar() or 0

    claims = db.query(UserProgramRewardClaim).filter(UserProgramRewardClaim.user_id == user.id).all()
    claimed_keys = {claim.reward_key for claim in claims}
    claimed_daily_dates = {
        claim.reward_key.removeprefix("daily:")
        for claim in claims
        if claim.reward_key.startswith("daily:")
    }
    streak = 0
    cursor = today
    while cursor.isoformat() in claimed_daily_dates:
        streak += 1
        cursor -= timedelta(days=1)

    mission_specs = (
        ("today_3_proofs", "Pošalji 3 dokaza danas", submitted_today, 3, "bg-blue-500"),
        ("week_5_proofs", "Pošalji 5 dokaza ove nedelje", submitted_this_week, 5, "bg-emerald-500"),
        ("first_active_referral", "Dovedi prvog aktivnog prijatelja", active_referrals, 1, "bg-violet-500"),
    )
    missions = [
        {
            "key": key,
            "title": title,
            "progress": min(progress, target),
            "target": target,
            "reward_rsd": PROGRAM_REWARDS[key],
            "accent": accent,
            "eligible": progress >= target,
            "claimed": key in claimed_keys,
        }
        for key, title, progress, target, accent in mission_specs
    ]
    badges = [
        {"key": "starter", "icon": "🚀", "name": "Starter", "description": "Prvih 5 poslatih dokaza", "unlocked": submitted_total >= 5},
        {"key": "streak_7", "icon": "🔥", "name": "Streak 7", "description": "7 uzastopno preuzetih dnevnih nagrada", "unlocked": streak >= 7},
        {"key": "trusted", "icon": "⭐", "name": "Trusted", "description": "20 odobrenih dokaza", "unlocked": approved_total >= 20},
        {"key": "pro_earner", "icon": "💎", "name": "Pro Earner", "description": "500 RSD stvarne zarade", "unlocked": (user.lifetime_earned_rsd or 0) >= 500},
        {"key": "elite", "icon": "👑", "name": "Elite", "description": "50 odobrenih dokaza", "unlocked": approved_total >= 50},
    ]
    week = []
    for offset in range(7):
        day = week_start.date() + timedelta(days=offset)
        week.append({
            "date": day.isoformat(),
            "label": ("Pon", "Uto", "Sre", "Čet", "Pet", "Sub", "Ned")[offset],
            "claimed": day.isoformat() in claimed_daily_dates,
            "is_today": day == today,
        })
    daily_key = f"daily:{today.isoformat()}"
    return {
        "daily": {
            "key": daily_key,
            "reward_rsd": DAILY_REWARD_RSD,
            "eligible": submitted_today > 0,
            "claimed": daily_key in claimed_keys,
            "streak": streak,
            "week": week,
        },
        "missions": missions,
        "badges": badges,
        "stats": {"submitted_total": submitted_total, "approved_total": approved_total},
    }


def _claimable_program_reward(db: Session, user: User, reward_key: str) -> tuple[float, str]:
    program = _program_data(db, user)
    if reward_key == program["daily"]["key"]:
        if not program["daily"]["eligible"]:
            raise HTTPException(409, "Dnevna nagrada se otključava nakon prvog stvarno poslatog dokaza danas.")
        return DAILY_REWARD_RSD, "Dnevna nagrada za aktivnost"
    mission = next((item for item in program["missions"] if item["key"] == reward_key), None)
    if not mission:
        raise HTTPException(404, "Nagrada nije pronađena.")
    if not mission["eligible"]:
        raise HTTPException(409, "Uslov za ovu misiju još nije ispunjen.")
    return mission["reward_rsd"], f"Nagrada za misiju: {mission['title']}"


@router.get("/user/dashboard")
def user_dashboard(request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik"})
    now = datetime.utcnow()
    active_verifications = db.query(TaskVerificationSessionV1).filter(
        TaskVerificationSessionV1.user_id == user.id,
        TaskVerificationSessionV1.status.in_(("started", "ready", "flagged")),
        TaskVerificationSessionV1.started_at >= now - timedelta(hours=2),
    ).order_by(TaskVerificationSessionV1.started_at.desc()).all()
    verification_by_task = {item.task_id: item for item in reversed(active_verifications)}
    enrollment_by_task = {
        item.task_id: item
        for item in db.query(AppTesterEnrollment).filter(AppTesterEnrollment.user_id == user.id).all()
    }
    tasks = []
    for task in db.query(Task).filter(Task.status == "active").order_by(Task.featured.desc(), Task.reward_rsd.desc()).limit(100).all():
        latest = _latest_task_submission(db, user.id, task.id)
        # A task returned for proof revision stays visible even when its last
        # available slot has already been reserved by this user.
        if task.id in enrollment_by_task or task.id in verification_by_task or _task_access_error(task, user, latest, now) is None:
            tasks.append(task)
    checkins_by_task: dict[int, list[AppTesterDailyCheckin]] = {}
    for item in db.query(AppTesterDailyCheckin).filter(AppTesterDailyCheckin.user_id == user.id).all():
        checkins_by_task.setdefault(item.task_id, []).append(item)
    submissions = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id).order_by(TaskSubmission.created_at.desc()).limit(100).all()
    my_task_ids = set(enrollment_by_task) | set(verification_by_task) | {item.task_id for item in submissions}
    my_tasks = db.query(Task).filter(Task.id.in_(my_task_ids)).all() if my_task_ids else []
    def task_for_user(task: Task) -> dict:
        data = _task_data(task)
        enrollment = enrollment_by_task.get(task.id)
        if enrollment:
            data.update({
                "tester_enrollment": _tester_enrollment_data(enrollment, include_email=True) | {
                    "email_conflict": _tester_email_conflict(db, enrollment.testing_email, enrollment.user_id),
                },
                "tester_checkins": [_tester_checkin_data(item) for item in checkins_by_task.get(task.id, [])],
                "tester_progress": _tester_window_progress(task, enrollment, checkins_by_task.get(task.id, [])),
            })
        data["verification_in_progress"] = task.id in verification_by_task
        return data
    withdrawals = db.query(Withdrawal).filter(Withdrawal.user_id == user.id).order_by(Withdrawal.created_at.desc()).limit(100).all()
    transactions = db.query(WalletTransaction).filter(WalletTransaction.user_id == user.id).order_by(WalletTransaction.created_at.desc()).limit(100).all()
    referrals = db.query(User).filter(User.referred_by_id == user.id).count()
    referral_earned = db.query(func.coalesce(func.sum(WalletTransaction.amount_rsd), 0)).filter(
        WalletTransaction.user_id == user.id,
        WalletTransaction.tx_type == "referral_inviter_bonus",
    ).scalar()
    return {
        "user": _user_data(user),
        "min_withdrawal_rsd": MIN_WITHDRAWAL_RSD,
        "referral_count": referrals,
        "referral_earned_rsd": _money(referral_earned),
        "referral_inviter_bonus_rsd": REFERRAL_INVITER_BONUS_RSD,
        "referral_joiner_bonus_rsd": REFERRAL_JOINER_BONUS_RSD,
        "program": _program_data(db, user),
        "tasks": [task_for_user(task) for task in tasks],
        "my_tasks": [task_for_user(task) for task in sorted(my_tasks, key=lambda item: item.id, reverse=True)],
        "submissions": [_submission_data(submission) for submission in submissions],
        "withdrawals": [{"id": item.id, "amount_rsd": _money(item.amount_rsd), "status": _status(item.status), "payment_method": item.payment_method, "created_at": _iso(item.created_at)} for item in withdrawals],
        "transactions": [{"id": item.id, "amount_rsd": _money(item.amount_rsd), "tx_type": item.tx_type, "description": item.description, "created_at": _iso(item.created_at)} for item in transactions],
    }


@router.post("/user/program/rewards/{reward_key}")
def claim_program_reward(reward_key: str, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik"})
    reward_key = reward_key.strip()[:80]
    reward_rsd, description = _claimable_program_reward(db, user, reward_key)
    existing = db.query(UserProgramRewardClaim).filter(
        UserProgramRewardClaim.user_id == user.id,
        UserProgramRewardClaim.reward_key == reward_key,
    ).first()
    if existing:
        raise HTTPException(409, "Ova nagrada je već preuzeta.")
    user.balance_rsd = _money(user.balance_rsd + reward_rsd)
    user.lifetime_earned_rsd = _money(user.lifetime_earned_rsd + reward_rsd)
    db.add(UserProgramRewardClaim(user_id=user.id, reward_key=reward_key, reward_rsd=reward_rsd))
    db.add(WalletTransaction(user_id=user.id, amount_rsd=reward_rsd, tx_type="program_reward", description=description))
    db.add(Notification(user_id=user.id, title="Nagrada je dodata", body=f"{description}: dodato je {reward_rsd:.0f} RSD na raspoloživi saldo.", status="unread"))
    db.commit()
    return {"claimed": True, "reward_rsd": _money(reward_rsd), "program": _program_data(db, user)}


@router.put("/user/profile")
def save_user_profile(payload: ProfilePayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik", "oglasivac", "admin"})
    phone = "".join(character for character in (payload.phone or "") if character.isdigit() or character == "+")
    if phone and db.query(User).filter(User.phone == phone, User.id != user.id).first():
        raise HTTPException(409, "Taj broj telefona je već povezan sa drugim nalogom.")
    user.full_name = payload.full_name.strip()
    user.phone = phone or None
    user.city = _profile_city(payload.city)
    if user.role == "oglasivac":
        website = (payload.company_website or "").strip()
        if website and not website.startswith(("https://", "http://")):
            raise HTTPException(400, "Sajt firme mora početi sa https:// ili http://.")
        pib = "".join(character for character in (payload.company_pib or "") if character.isalnum() or character in "-/")
        user.company_name = (payload.company_name or "").strip() or None
        user.company_pib = pib or None
        user.company_website = website or None
        user.company_activity = (payload.company_activity or "").strip() or None
    if payload.payment_details:
        user.payment_method = "PayPal"
        user.payment_details = _paypal_email(payload.payment_details)
    db.commit()
    return {"user": _user_data(user)}


@router.post("/user/onboarding")
def complete_user_onboarding(payload: OnboardingPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik"})
    allowed_age_groups = {"18-24", "25-34", "35-44", "45-54", "55+", "18+"}
    age_group = payload.age_group.strip()
    if age_group not in allowed_age_groups:
        raise HTTPException(400, "Izaberi jednu od ponuđenih starosnih grupa.")
    interests: list[str] = []
    for value in payload.interests:
        clean = re.sub(r"\s+", " ", value).strip()
        if clean and clean not in interests:
            interests.append(clean[:50])
    if not interests:
        raise HTTPException(400, "Izaberi najmanje jednu oblast interesovanja.")
    user.city = _profile_city(payload.city)
    user.age_group = age_group
    user.interests = json.dumps(interests, ensure_ascii=False)
    db.add(Notification(
        user_id=user.id,
        title="Profil je podešen",
        body="Sada možemo da prikazujemo zadatke koji bolje odgovaraju tvom profilu.",
        status="unread",
    ))
    db.commit()
    return {"user": _user_data(user), "onboarding_complete": True}


def _notification_data(item: Notification) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "body": item.body,
        "status": _status(item.status),
        "created_at": _iso(item.created_at),
    }


@router.get("/notifications")
def my_notifications(request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db)
    items = db.query(Notification).filter(
        (Notification.user_id == user.id) | (Notification.role_target == user.role) | (Notification.role_target == "all"),
    ).order_by(Notification.created_at.desc()).limit(100).all()
    return {"notifications": [_notification_data(item) for item in items]}


@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db)
    item = db.query(Notification).filter(Notification.id == notification_id).first()
    if not item or (item.user_id != user.id and item.role_target not in {user.role, "all"}):
        raise HTTPException(404, "Obaveštenje nije pronađeno.")
    item.status = "read"
    db.commit()
    return {"notification": _notification_data(item)}


@router.put("/account/password")
def change_account_password(payload: PasswordChangePayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik", "oglasivac", "admin"})
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(400, "Trenutna lozinka nije ispravna.")
    if payload.current_password == payload.new_password:
        raise HTTPException(400, "Nova lozinka mora biti različita od trenutne.")
    user.password_hash = hash_password(payload.new_password)
    _revoke_legacy_sessions(db, user.id)
    db.commit()
    return {"ok": True}


@router.get("/tickets")
def my_support_tickets(request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db)
    tickets = db.query(SupportTicket).filter(SupportTicket.user_id == user.id).order_by(SupportTicket.updated_at.desc()).limit(100).all()
    return {"tickets": [_ticket_data(ticket) for ticket in tickets]}


@router.post("/tickets", status_code=201)
def create_support_ticket(payload: SupportTicketPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db)
    if payload.category.strip().lower() == "account_deletion":
        raise HTTPException(400, "Za brisanje naloga koristi opciju u profilu i potvrdi lozinku.")
    ticket = SupportTicket(user_id=user.id, subject=payload.subject.strip(), category=payload.category.strip() or "Opšte", status="open")
    db.add(ticket)
    db.flush()
    db.add(SupportMessage(ticket_id=ticket.id, sender_id=user.id, body=payload.body.strip()))
    db.commit()
    db.refresh(ticket)
    return {"ticket": _ticket_data(ticket)}


@router.post("/tickets/{ticket_id}/messages", status_code=201)
def reply_to_support_ticket(ticket_id: int, payload: SupportTicketMessagePayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db)
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id, SupportTicket.user_id == user.id).first()
    if not ticket:
        raise HTTPException(404, "Tiket nije pronađen.")
    if ticket.status == "closed":
        ticket.status = "open"
    ticket.updated_at = datetime.utcnow()
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


def _require_tester_invitation(db: Session, user: User, task: Task) -> None:
    """Keep closed beta access separate from a paid task result."""
    if not task.requires_tester_enrollment:
        return
    enrollment = db.query(AppTesterEnrollment).filter(
        AppTesterEnrollment.task_id == task.id,
        AppTesterEnrollment.user_id == user.id,
    ).first()
    if not enrollment:
        raise HTTPException(409, "Prvo pošalji email za poziv u zatvoreno testiranje.")
    if enrollment.status != "invited":
        raise HTTPException(409, "Pristup testiranju još nije odobren. Sačekaj obaveštenje oglašivača.")


def _require_tester_daily_completion(db: Session, user: User, task: Task) -> None:
    if not task.requires_tester_enrollment:
        return
    enrollment = db.query(AppTesterEnrollment).filter(
        AppTesterEnrollment.task_id == task.id,
        AppTesterEnrollment.user_id == user.id,
        AppTesterEnrollment.status == "invited",
    ).first()
    if not enrollment or not enrollment.invited_at:
        raise HTTPException(409, "Sačekaj da oglašivač potvrdi tvoje mesto u testiranju.")
    checkins = db.query(AppTesterDailyCheckin).filter(
        AppTesterDailyCheckin.task_id == task.id,
        AppTesterDailyCheckin.user_id == user.id,
        AppTesterDailyCheckin.status.in_(("pending", "approved")),
    ).all()
    progress = _tester_window_progress(task, enrollment, checkins)
    if not progress["complete"]:
        raise HTTPException(409, f"Za ovaj test treba {task.tester_duration_days or 14} dnevnih prijava. Trenutno imaš {progress['checkin_total']}.")


@router.post("/user/tasks/{task_id}/tester-enrollments", status_code=201)
def request_tester_enrollment(task_id: int, payload: TesterEnrollmentPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik"})
    _expire_campaigns(db)
    task = db.query(Task).filter(Task.id == task_id, Task.status == "active").first()
    if not task or not task.requires_tester_enrollment:
        raise HTTPException(404, "Ovaj zadatak nema prijavu za zatvoreno testiranje.")
    email = payload.testing_email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(400, "Unesi važeću email adresu za pristup testiranju.")
    if _tester_email_conflict(db, email, user.id):
        raise HTTPException(409, "Ovu test adresu nije moguće vezati za tvoj nalog. Proveri da li koristiš sopstveni Google Play email ili se obrati podršci.")
    enrollment = db.query(AppTesterEnrollment).filter(
        AppTesterEnrollment.task_id == task.id,
        AppTesterEnrollment.user_id == user.id,
    ).first()
    if enrollment and enrollment.status in {"requested", "invited"}:
        raise HTTPException(409, "Prijava za testiranje je već poslata.")
    if int(task.used_slots or 0) >= int(task.total_slots or 0):
        raise HTTPException(409, "Sva mesta za testere su trenutno popunjena.")
    if enrollment:
        enrollment.testing_email = email
        enrollment.status = "requested"
        enrollment.note = None
        enrollment.updated_at = datetime.utcnow()
    else:
        enrollment = AppTesterEnrollment(task_id=task.id, user_id=user.id, testing_email=email)
        db.add(enrollment)
    if task.advertiser_id:
        db.add(Notification(
            user_id=task.advertiser_id,
            title="Nova prijava za zatvoreno testiranje",
            body=f"{user.full_name} je poslao/la email za pristup testiranju kampanje: {task.title}.",
            status="unread",
        ))
    db.commit()
    db.refresh(enrollment)
    return {"enrollment": _tester_enrollment_data(enrollment)}


@router.post("/user/tasks/{task_id}/tester-checkins", status_code=201)
def create_tester_daily_checkin(task_id: int, payload: TesterDailyCheckinPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    """Record a daily test report. It is a user declaration, not third-party telemetry."""
    user = _require_user(request, db, {"korisnik"})
    _expire_campaigns(db)
    task = db.query(Task).filter(Task.id == task_id, Task.status == "active").first()
    if not task or not task.requires_tester_enrollment:
        raise HTTPException(404, "Ovaj zadatak nema dnevnu evidenciju testiranja.")
    enrollment = db.query(AppTesterEnrollment).filter(
        AppTesterEnrollment.task_id == task.id,
        AppTesterEnrollment.user_id == user.id,
        AppTesterEnrollment.status == "invited",
    ).first()
    if not enrollment or not enrollment.invited_at:
        raise HTTPException(409, "Dnevna evidencija se otključava kada oglašivač potvrdi da si dodat/a u tester listu.")
    if _tester_email_conflict(db, enrollment.testing_email, user.id):
        raise HTTPException(409, "Test adresa je povezana sa drugim nalogom. Razjasni prijavu preko podrške pre novog dnevnog izveštaja.")
    progress = _tester_window_progress(task, enrollment, [])
    if not progress["started"] or progress["current_day"] < 1:
        raise HTTPException(409, "Tvoj period testiranja još nije počeo.")
    if progress["days_elapsed"] > (task.tester_duration_days or 14):
        raise HTTPException(409, "Tvoj rok za dnevne prijave je istekao.")
    day_number = progress["current_day"]
    checkin = db.query(AppTesterDailyCheckin).filter(
        AppTesterDailyCheckin.task_id == task.id,
        AppTesterDailyCheckin.user_id == user.id,
        AppTesterDailyCheckin.day_number == day_number,
    ).first()
    if checkin and checkin.status != "rejected":
        raise HTTPException(409, "Današnji test je već prijavljen.")
    if checkin:
        checkin.note = payload.note.strip()
        checkin.reward_rsd = task.tester_daily_reward_rsd or 0
        checkin.status = "pending"
        checkin.review_note = None
        checkin.reviewed_at = None
        checkin.checked_in_at = datetime.utcnow()
    else:
        checkin = AppTesterDailyCheckin(
            task_id=task.id,
            user_id=user.id,
            day_number=day_number,
            note=payload.note.strip(),
            reward_rsd=task.tester_daily_reward_rsd or 0,
        )
        db.add(checkin)
    user.pending_rsd = _money(user.pending_rsd + (task.tester_daily_reward_rsd or 0))
    if task.advertiser_id:
        db.add(Notification(
            user_id=task.advertiser_id,
            title=f"Dnevni izveštaj, dan {day_number}",
            body=f"{user.full_name} je poslao/la dnevni izveštaj za kampanju: {task.title}.",
            status="unread",
        ))
    db.commit()
    db.refresh(checkin)
    return {"checkin": _tester_checkin_data(checkin)}


@router.post("/user/tasks/{task_id}/verification/start", status_code=201)
def start_task_verification(task_id: int, payload: VerificationStartPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik"})
    _expire_campaigns(db)
    task = db.query(Task).filter(Task.id == task_id, Task.status == "active").first()
    if not task:
        raise HTTPException(404, "Zadatak nije dostupan.")
    _require_tester_invitation(db, user, task)
    if task.requires_tester_enrollment:
        raise HTTPException(409, "Za zatvoreno testiranje koristi dnevnu evidenciju. Nagrada se obračunava po odobrenom danu.")
    latest_submission = _latest_task_submission(db, user.id, task.id)
    access_error = _task_access_error(task, user, latest_submission)
    if access_error:
        raise HTTPException(409, access_error)
    # A proof revision does not consume a new slot or reserve a new reward.
    if not latest_submission or latest_submission.status != "needs_revision":
        _verify_daily_limits(db, user, task)

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
    user = _require_user(request, db, {"korisnik"})
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
    user = _require_user(request, db, {"korisnik"})
    _expire_campaigns(db)
    task = db.query(Task).filter(Task.id == task_id, Task.status == "active").first()
    if not task:
        raise HTTPException(404, "Zadatak nije dostupan.")
    _require_tester_invitation(db, user, task)
    if task.requires_tester_enrollment:
        raise HTTPException(409, "Za zatvoreno testiranje nagrade se obračunavaju po odobrenim dnevnim izveštajima.")
    existing = _latest_task_submission(db, user.id, task.id)
    access_error = _task_access_error(task, user, existing)
    if access_error:
        raise HTTPException(409, access_error)
    verification = db.query(TaskVerificationSessionV1).filter(
        TaskVerificationSessionV1.token == payload.verification_token,
        TaskVerificationSessionV1.user_id == user.id,
        TaskVerificationSessionV1.task_id == task.id,
        TaskVerificationSessionV1.status.in_(["ready", "flagged"]),
    ).first()
    minimum_events = int(_limit_from_env("ANTI_FRAUD_MIN_ACTIVITY_EVENTS", ANTI_FRAUD_MIN_ACTIVITY_EVENTS))
    if not verification or verification.active_seconds < verification.required_seconds or verification.activity_events < minimum_events:
        raise HTTPException(409, "Pre slanja dokaza završi proveru vremena i aktivnosti zadatka.")
    is_revision = bool(existing and existing.status == "needs_revision")
    if is_revision:
        submission = existing
        submission.proof = payload.proof.strip()
        submission.status = "pending"
        submission.review_note = None
        submission.reviewed_at = None
        submission.revision_due_at = None
        submission.revision_count = int(submission.revision_count or 0) + 1
    else:
        fee = _money(task.reward_rsd * (task.platform_fee_percent or PLATFORM_FEE_PERCENT) / 100)
        submission = TaskSubmission(
            user_id=user.id,
            task_id=task.id,
            proof=payload.proof.strip(),
            reward_rsd=task.reward_rsd,
            platform_fee_rsd=fee,
            advertiser_cost_rsd=_money(task.reward_rsd + fee),
            status="pending",
        )
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
    user = _require_user(request, db, {"korisnik"})
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
    _expire_campaigns(db)
    tasks = db.query(Task).filter(Task.advertiser_id == user.id).order_by(Task.created_at.desc()).limit(100).all()
    submissions = db.query(TaskSubmission).join(Task).filter(Task.advertiser_id == user.id).order_by(TaskSubmission.created_at.desc()).limit(100).all()
    enrollments = db.query(AppTesterEnrollment).join(Task).filter(Task.advertiser_id == user.id).order_by(AppTesterEnrollment.created_at.desc()).limit(300).all()
    tester_emails = {item.testing_email.strip().lower() for item in enrollments}
    registered_email_owners = {
        email.lower(): owner_id for owner_id, email in db.query(User.id, User.email).filter(func.lower(User.email).in_(tester_emails)).all()
    }
    tester_email_owners: dict[str, set[int]] = {}
    for owner_id, email in db.query(AppTesterEnrollment.user_id, func.lower(AppTesterEnrollment.testing_email)).filter(
        func.lower(AppTesterEnrollment.testing_email).in_(tester_emails),
        AppTesterEnrollment.status.in_(("requested", "invited")),
    ).all():
        tester_email_owners.setdefault(email, set()).add(owner_id)
    tester_checkins = db.query(AppTesterDailyCheckin).join(Task).filter(Task.advertiser_id == user.id).order_by(AppTesterDailyCheckin.checked_in_at.desc()).limit(500).all()
    transactions = db.query(AdvertiserBudgetTransaction).filter(AdvertiserBudgetTransaction.advertiser_id == user.id).order_by(AdvertiserBudgetTransaction.created_at.desc()).limit(100).all()
    task_payload = []
    for task in tasks:
        task_submissions = [submission for submission in submissions if submission.task_id == task.id]
        task_data = _task_data(task)
        task_data["submission_total"] = len(task_submissions)
        task_data["submission_approved"] = sum(1 for submission in task_submissions if _status(submission.status) == "approved")
        task_data["submission_rejected"] = sum(1 for submission in task_submissions if _status(submission.status) == "rejected")
        task_data["submission_pending"] = sum(1 for submission in task_submissions if _status(submission.status) in {"pending", "submitted"})
        task_data["submission_needs_revision"] = sum(1 for submission in task_submissions if _status(submission.status) == "needs_revision")
        task_enrollments = [item for item in enrollments if item.task_id == task.id]
        task_data["tester_enrollment_total"] = len(task_enrollments)
        task_data["tester_enrollment_requested"] = sum(1 for item in task_enrollments if item.status == "requested")
        task_data["tester_enrollment_invited"] = sum(1 for item in task_enrollments if item.status == "invited")
        task_data["tester_cohort_count"] = len({item.cohort_number for item in task_enrollments if item.cohort_number})
        task_checkins = [item for item in tester_checkins if item.task_id == task.id]
        task_data["tester_checkin_total"] = len(task_checkins)
        task_data["tester_checkin_pending"] = sum(1 for item in task_checkins if item.status == "pending")
        task_data["tester_checkin_approved"] = sum(1 for item in task_checkins if item.status == "approved")
        task_payload.append(task_data)
    return {
        "user": _user_data(user),
        "tasks": task_payload,
        "submissions": [_submission_data(submission) | {"user_name": submission.user.full_name if submission.user else "Korisnik"} for submission in submissions],
        "tester_enrollments": [
            _tester_enrollment_data(item, include_email=True) | {
                "task_title": item.task.title if item.task else "Zadatak",
                "email_conflict": (
                    registered_email_owners.get(item.testing_email.strip().lower()) not in (None, item.user_id)
                    or bool(tester_email_owners.get(item.testing_email.strip().lower(), set()) - {item.user_id})
                ),
            } for item in enrollments
        ],
        "tester_checkins": [_tester_checkin_data(item) | {"task_title": item.task.title if item.task else "Zadatak", "user_name": item.user.full_name if item.user else "Korisnik"} for item in tester_checkins],
        "transactions": [{"id": tx.id, "amount_rsd": _money(tx.amount_rsd), "tx_type": tx.tx_type, "description": tx.description, "created_at": _iso(tx.created_at)} for tx in transactions],
        "pricing": _pricing_data(),
    }


@router.post("/advertiser/tasks/{task_id}/tester-cohorts/start")
def start_tester_cohort(task_id: int, payload: TesterCohortStartPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    """Activate waiting testers immediately, each with their own full test window."""
    advertiser = _require_user(request, db, {"oglasivac", "admin"})
    task = db.query(Task).filter(Task.id == task_id, Task.advertiser_id == advertiser.id).first()
    if not task or not task.requires_tester_enrollment:
        raise HTTPException(404, "Zatvorena beta kampanja nije pronađena.")
    if _status(task.status) != "active":
        raise HTTPException(409, "Testera možeš aktivirati tek kada je kampanja aktivna.")

    requested = db.query(AppTesterEnrollment).filter(
        AppTesterEnrollment.task_id == task.id,
        AppTesterEnrollment.status == "requested",
    ).order_by(AppTesterEnrollment.created_at.asc()).all()
    invited_count = db.query(AppTesterEnrollment).filter(
        AppTesterEnrollment.task_id == task.id,
        AppTesterEnrollment.status == "invited",
    ).count()
    available_slots = max(0, int(task.total_slots or 0) - invited_count)
    eligible = [item for item in requested if not _tester_email_conflict(db, item.testing_email, item.user_id)]
    requested_count = payload.count or 1
    count = min(int(requested_count), len(eligible), available_slots)
    if count < 1:
        raise HTTPException(409, "Nema prijava sa slobodnim mestom i jedinstvenom test adresom za aktivaciju. Proveri upozorenja uz prijave.")

    activation_number = int(db.query(func.max(AppTesterEnrollment.cohort_number)).filter(
        AppTesterEnrollment.task_id == task.id,
    ).scalar() or 0) + 1
    started_at = datetime.utcnow()
    activated = eligible[:count]
    for enrollment in activated:
        enrollment.status = "invited"
        enrollment.cohort_number = activation_number
        enrollment.invited_at = started_at
        enrollment.updated_at = started_at
        db.add(Notification(
            user_id=enrollment.user_id,
            title="Pristup testiranju je odobren",
            body=f"Pristup testiranju za '{task.title}' je aktiviran. Tvojih {task.tester_duration_days or 14} dana počinje danas. Svakog dana testiraj najmanje {task.tester_daily_minutes or 5} min i pošalji kratak dnevni izveštaj.",
            status="unread",
        ))
    task.used_slots = int(task.used_slots or 0) + len(activated)
    _audit(db, advertiser, "tester_access_activated", "Task", task.id, f"activation={activation_number}; testers={len(activated)}")
    db.commit()
    return {
        "cohort_number": activation_number,
        "activated_count": len(activated),
        "started_at": _iso(started_at),
        "enrollments": [_tester_enrollment_data(item, include_email=True) for item in activated],
    }


@router.patch("/advertiser/tester-enrollments/{enrollment_id}")
def update_tester_enrollment(enrollment_id: int, payload: TesterEnrollmentStatusPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    """The advertiser manually controls who gets access to a closed beta."""
    advertiser = _require_user(request, db, {"oglasivac", "admin"})
    enrollment = db.query(AppTesterEnrollment).join(Task).filter(
        AppTesterEnrollment.id == enrollment_id,
        Task.advertiser_id == advertiser.id,
    ).first()
    if not enrollment:
        raise HTTPException(404, "Prijava za testiranje nije pronađena.")
    if enrollment.status == "invited" and payload.status == "invited":
        raise HTTPException(409, "Korisnik je već označen kao pozvan u testiranje.")
    task = enrollment.task
    was_invited = enrollment.status == "invited"
    if payload.status == "invited" and not was_invited:
        if _tester_email_conflict(db, enrollment.testing_email, enrollment.user_id):
            raise HTTPException(409, "Test adresa je povezana sa drugim nalogom. Razjasni prijavu pre aktivacije.")
        occupied_slots = db.query(AppTesterEnrollment).filter(
            AppTesterEnrollment.task_id == task.id,
            AppTesterEnrollment.status == "invited",
        ).count()
        if occupied_slots >= int(task.total_slots or 0):
            raise HTTPException(409, "Sva mesta za testere su već popunjena.")
        enrollment.invited_at = datetime.utcnow()
        enrollment.cohort_number = int(db.query(func.max(AppTesterEnrollment.cohort_number)).filter(
            AppTesterEnrollment.task_id == task.id,
        ).scalar() or 0) + 1
        task.used_slots = int(task.used_slots or 0) + 1
    elif payload.status == "declined" and was_invited:
        enrollment.invited_at = None
        enrollment.cohort_number = None
        task.used_slots = max(0, int(task.used_slots or 0) - 1)
    enrollment.status = payload.status
    enrollment.note = (payload.note or "").strip() or None
    enrollment.updated_at = datetime.utcnow()
    if payload.status == "invited":
        body = f"Dodat/a si u zatvoreno testiranje za: {task.title}. Tvojih {task.tester_duration_days or 14} dana počinje sada. Svakog dana testiraj najmanje {task.tester_daily_minutes or 5} min i pošalji kratak dnevni izveštaj."
        title = "Pristup testiranju je odobren"
    else:
        body = enrollment.note or f"Prijava za zatvoreno testiranje kampanje '{enrollment.task.title}' trenutno nije odobrena."
        title = "Prijava za testiranje nije odobrena"
    db.add(Notification(user_id=enrollment.user_id, title=title, body=body, status="unread"))
    _audit(db, advertiser, "tester_enrollment_status", "AppTesterEnrollment", enrollment.id, payload.status)
    db.commit()
    db.refresh(enrollment)
    return {"enrollment": _tester_enrollment_data(enrollment, include_email=True)}


def _task_chat_access(task_id: int, participant_id: int, request: Request, db: Session) -> tuple[Task, User, User]:
    actor = _require_user(request, db)
    task = db.get(Task, task_id)
    participant = db.get(User, participant_id)
    if not task or not task.advertiser_id or not participant or participant.role != "korisnik" or participant_id == task.advertiser_id:
        raise HTTPException(404, "Razgovor nije pronađen.")
    is_participant = actor.id == participant_id and actor.role == "korisnik"
    is_owner = actor.id == task.advertiser_id and actor.role in {"oglasivac", "admin"}
    if not (is_participant or is_owner):
        raise HTTPException(403, "Nemaš pristup ovom razgovoru.")
    enrolled = db.query(AppTesterEnrollment.id).filter(
        AppTesterEnrollment.task_id == task_id,
        AppTesterEnrollment.user_id == participant_id,
        AppTesterEnrollment.status.in_({"requested", "invited"}),
    ).first()
    submitted = db.query(TaskSubmission.id).filter(
        TaskSubmission.task_id == task_id, TaskSubmission.user_id == participant_id,
    ).first()
    started = db.query(TaskVerificationSessionV1.id).filter(
        TaskVerificationSessionV1.task_id == task_id, TaskVerificationSessionV1.user_id == participant_id,
    ).first()
    existing_chat = db.query(TaskChatMessage.id).filter(
        TaskChatMessage.task_id == task_id, TaskChatMessage.participant_id == participant_id,
    ).first()
    if not (enrolled or submitted or started or existing_chat):
        raise HTTPException(404, "Razgovor nije pronađen.")
    return task, actor, participant


def _task_chat_message_data(message: TaskChatMessage) -> dict:
    return {
        "id": message.id,
        "sender_id": message.sender_id,
        "body": message.body,
        "created_at": message.created_at.replace(tzinfo=timezone.utc).isoformat() if message.created_at else None,
    }


@router.get("/advertiser/task-chats")
def advertiser_task_chats(request: Request, db: Session = Depends(get_db)) -> dict:
    advertiser = _require_user(request, db, {"oglasivac", "admin"})
    latest = db.query(
        TaskChatMessage.task_id.label("task_id"),
        TaskChatMessage.participant_id.label("participant_id"),
        func.max(TaskChatMessage.id).label("message_id"),
    ).group_by(TaskChatMessage.task_id, TaskChatMessage.participant_id).subquery()
    rows = db.query(TaskChatMessage, Task.title, User.full_name).join(
        latest, TaskChatMessage.id == latest.c.message_id,
    ).join(Task, Task.id == TaskChatMessage.task_id).join(
        User, User.id == TaskChatMessage.participant_id,
    ).filter(Task.advertiser_id == advertiser.id).order_by(TaskChatMessage.id.desc()).limit(100).all()
    return {"threads": [{
        "task_id": message.task_id,
        "task_title": title,
        "participant_id": message.participant_id,
        "participant_name": name,
        "last_message": message.body[:180],
        "last_message_at": message.created_at.replace(tzinfo=timezone.utc).isoformat() if message.created_at else None,
    } for message, title, name in rows]}


@router.get("/user/task-chats")
def user_task_chats(request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik"})
    latest = db.query(
        TaskChatMessage.task_id.label("task_id"),
        TaskChatMessage.participant_id.label("participant_id"),
        func.max(TaskChatMessage.id).label("message_id"),
    ).filter(TaskChatMessage.participant_id == user.id).group_by(
        TaskChatMessage.task_id, TaskChatMessage.participant_id,
    ).subquery()
    rows = db.query(TaskChatMessage, Task.title).join(
        latest, TaskChatMessage.id == latest.c.message_id,
    ).join(Task, Task.id == TaskChatMessage.task_id).order_by(TaskChatMessage.id.desc()).limit(100).all()
    return {"threads": [{
        "task_id": message.task_id,
        "task_title": title,
        "participant_id": user.id,
        "participant_name": user.full_name,
        "last_message": message.body[:180],
        "last_message_at": message.created_at.replace(tzinfo=timezone.utc).isoformat() if message.created_at else None,
    } for message, title in rows]}


@router.get("/task-chat/{task_id}/{participant_id}")
def get_task_chat(task_id: int, participant_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    task, actor, participant = _task_chat_access(task_id, participant_id, request, db)
    messages = db.query(TaskChatMessage).filter(
        TaskChatMessage.task_id == task_id, TaskChatMessage.participant_id == participant_id,
    ).order_by(TaskChatMessage.id.desc()).limit(200).all()
    return {
        "task_id": task.id,
        "task_title": task.title,
        "participant_id": participant.id,
        "participant_name": participant.full_name,
        "current_user_id": actor.id,
        "messages": [_task_chat_message_data(message) for message in reversed(messages)],
    }


@router.post("/task-chat/{task_id}/{participant_id}")
def send_task_chat_message(task_id: int, participant_id: int, payload: TaskChatPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    task, actor, participant = _task_chat_access(task_id, participant_id, request, db)
    body = payload.body.strip()
    if not body:
        raise HTTPException(400, "Unesi poruku pre slanja.")
    message = TaskChatMessage(task_id=task.id, participant_id=participant.id, sender_id=actor.id, body=body)
    db.add(message)
    recipient_id = participant.id if actor.id == task.advertiser_id else task.advertiser_id
    db.add(Notification(
        user_id=recipient_id,
        title="Nova poruka uz zadatak",
        body=f"{actor.full_name} je poslao/la poruku za zadatak '{task.title}'. Otvori razgovor uz zadatak.",
        status="unread",
    ))
    db.commit()
    db.refresh(message)
    return {"message": _task_chat_message_data(message)}


@router.patch("/advertiser/tester-checkins/{checkin_id}")
def review_tester_daily_checkin(checkin_id: int, payload: AdminStatusPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    """The campaign owner approves each declared test day and its daily reward."""
    advertiser = _require_user(request, db, {"oglasivac", "admin"})
    if payload.status not in {"approved", "rejected"}:
        raise HTTPException(400, "Dnevni izveštaj može biti odobren ili odbijen.")
    checkin = db.query(AppTesterDailyCheckin).join(Task).filter(
        AppTesterDailyCheckin.id == checkin_id,
        Task.advertiser_id == advertiser.id,
    ).first()
    if not checkin:
        raise HTTPException(404, "Dnevni izveštaj nije pronađen.")
    if checkin.status != "pending":
        raise HTTPException(409, "Ovaj dnevni izveštaj je već obrađen.")
    if payload.status == "approved":
        enrollment = db.query(AppTesterEnrollment).filter(
            AppTesterEnrollment.task_id == checkin.task_id,
            AppTesterEnrollment.user_id == checkin.user_id,
        ).first()
        if enrollment and _tester_email_conflict(db, enrollment.testing_email, checkin.user_id):
            raise HTTPException(409, "Test adresa je povezana sa drugim nalogom. Ne odobravaj nagradu dok prijava ne bude razjašnjena.")
    checkin.status = payload.status
    checkin.review_note = (payload.note or "").strip() or None
    checkin.reviewed_at = datetime.utcnow()
    user = checkin.user
    task = checkin.task
    user.pending_rsd = _money(max(0, user.pending_rsd - checkin.reward_rsd))
    if payload.status == "approved":
        user.balance_rsd = _money(user.balance_rsd + checkin.reward_rsd)
        user.lifetime_earned_rsd = _money(user.lifetime_earned_rsd + checkin.reward_rsd)
        db.add(WalletTransaction(
            user_id=user.id,
            amount_rsd=checkin.reward_rsd,
            tx_type="app_test_daily_reward",
            description=f"Odobren test aplikacije, dan {checkin.day_number}: {task.title}",
        ))
        if checkin.reward_rsd > 0:
            _grant_referral_bonus_if_eligible(db, user)
        if not _is_platform_publisher(advertiser):
            advertiser_cost = _money(checkin.reward_rsd * (1 + float(task.platform_fee_percent or 0) / 100))
            advertiser.advertiser_reserved_rsd = _money(max(0, advertiser.advertiser_reserved_rsd - advertiser_cost))
            advertiser.advertiser_spent_rsd = _money(advertiser.advertiser_spent_rsd + advertiser_cost)
        title = "Dnevno testiranje je odobreno"
        body = f"Odobrena je nagrada od {checkin.reward_rsd:.0f} RSD za dan {checkin.day_number}."
    else:
        title = "Dnevno testiranje nije odobreno"
        body = checkin.review_note or f"Izveštaj za dan {checkin.day_number} nije ispunio zahteve kampanje."
    db.add(Notification(user_id=user.id, title=title, body=body, status="unread"))
    _audit(db, advertiser, "tester_daily_checkin_review", "AppTesterDailyCheckin", checkin.id, payload.status)
    db.commit()
    db.refresh(checkin)
    return {"checkin": _tester_checkin_data(checkin)}


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


@router.post("/advertiser/banners/upload", status_code=201)
async def upload_advertiser_banner(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
) -> dict:
    _require_user(request, db, {"oglasivac", "admin"})
    declared_type = (file.content_type or "").lower()
    if declared_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(400, "Banner mora biti JPG, PNG ili WEBP slika.")
    content = await file.read(_BANNER_MAX_BYTES + 1)
    if not content or len(content) > _BANNER_MAX_BYTES:
        raise HTTPException(400, "Banner je prazan ili veći od 5 MB.")
    try:
        image = Image.open(BytesIO(content))
        image.verify()
        image = Image.open(BytesIO(content))
        width, height = image.size
        suffix = _BANNER_IMAGE_FORMATS.get(image.format or "")
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(400, "Fajl nije ispravna slika.")
    if not suffix:
        raise HTTPException(400, "Podržani su samo JPG, PNG i WEBP banneri.")
    if width < 200 or height < 80 or width > 6000 or height > 6000:
        raise HTTPException(400, "Dimenzije bannera moraju biti između 200x80 i 6000x6000 px.")
    _BANNER_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{suffix}"
    (_BANNER_UPLOAD_DIR / filename).write_bytes(content)
    return {"image_url": _banner_upload_url(filename), "width": width, "height": height, "warning": "Fajl je sačuvan na disku aplikacije. Za trajno čuvanje posle redeploy-a podesi BANNER_UPLOAD_DIR na persistent disk ili object storage."}


@router.get("/public/banner-files/{filename}")
def uploaded_banner_file(filename: str) -> FileResponse:
    safe_name = Path(filename).name
    if safe_name != filename or not re.fullmatch(r"[a-f0-9]{32}\.(?:jpg|png|webp)", safe_name):
        raise HTTPException(404, "Banner nije pronađen.")
    path = _BANNER_UPLOAD_DIR / safe_name
    if not path.is_file():
        raise HTTPException(404, "Banner nije pronađen.")
    media_types = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return FileResponse(path, media_type=media_types[path.suffix])


@router.get("/advertiser/promotions")
def advertiser_promotions(request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"oglasivac", "admin"})
    _expire_promotions(db)
    items = db.query(PaidPromotionRequestV111).filter(PaidPromotionRequestV111.advertiser_id == user.id).order_by(PaidPromotionRequestV111.created_at.desc()).limit(100).all()
    return {"promotions": [_promotion_data(item) for item in items], "prices": {"featured_per_7_days_rsd": 1200, "priority_per_7_days_rsd": 700, "max_days": 31}}


@router.post("/advertiser/promotions", status_code=201)
def reserve_advertiser_promotion(payload: PromotionPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"oglasivac", "admin"})
    task = db.query(Task).filter(Task.id == payload.task_id, Task.advertiser_id == user.id).with_for_update().first()
    if not task:
        raise HTTPException(404, "Kampanja nije pronađena.")
    if task.status != "active":
        raise HTTPException(400, "Samo aktivna kampanja može dobiti promociju.")
    now = datetime.utcnow()
    active_or_pending = db.query(PaidPromotionRequestV111).filter(
        PaidPromotionRequestV111.task_id == task.id,
        PaidPromotionRequestV111.promotion_type == payload.promotion_type,
        PaidPromotionRequestV111.status.in_(("pending", "active")),
    ).first()
    if active_or_pending:
        raise HTTPException(409, "Za ovu kampanju već postoji aktivna ili poslata rezervacija iste promocije.")
    platform_publishing = _is_platform_publisher(user)
    price = 0.0 if platform_publishing else _promotion_price(payload.promotion_type, payload.days_count)
    if float(user.advertiser_budget_rsd or 0) < price:
        raise HTTPException(400, f"Nedovoljno budžeta. Za ovu promociju potrebno je {price:.0f} RSD.")
    if not platform_publishing:
        user.advertiser_budget_rsd = _money(float(user.advertiser_budget_rsd or 0) - price)
        user.advertiser_reserved_rsd = _money(float(user.advertiser_reserved_rsd or 0) + price)
    item = PaidPromotionRequestV111(
        advertiser_id=user.id,
        task_id=task.id,
        promotion_type=payload.promotion_type,
        title=task.title,
        price_rsd=price,
        days_count=payload.days_count,
        status="pending",
        admin_note="Platformska promocija čeka odobrenje." if platform_publishing else "Rezervacija čeka odobrenje administratora.",
        starts_at=now,
        ends_at=now + timedelta(days=payload.days_count),
    )
    db.add(item)
    db.add(AdvertiserBudgetTransaction(
        advertiser_id=user.id,
        amount_rsd=-price if not platform_publishing else 0,
        tx_type="platform_promotion_requested" if platform_publishing else "reserve_promotion",
        description=f"Platformska promocija bez naknade: {task.title}" if platform_publishing else f"Rezervisana promocija ({payload.promotion_type}): {task.title}",
    ))
    db.commit()
    db.refresh(item)
    return {"promotion": _promotion_data(item), "reserved_rsd": price}


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
    now = datetime.utcnow()
    starts_at = payload.requested_start_at or now
    if starts_at.tzinfo is not None:
        starts_at = starts_at.replace(tzinfo=None)
    starts_at = starts_at.replace(second=0, microsecond=0)
    if starts_at < now - timedelta(minutes=1):
        raise HTTPException(400, "Početak zakupa ne može biti u prošlosti.")
    if starts_at > now + timedelta(days=365):
        raise HTTPException(400, "Banner možeš rezervisati najviše godinu dana unapred.")
    ends_at = starts_at + timedelta(days=payload.days_count)
    if _banner_slot_conflict(db, slot.id, starts_at, ends_at):
        raise HTTPException(409, "Ovaj slot je već rezervisan za traženi period.")
    target_url = _validate_banner_target_url(payload.target_url)
    image_url = _validate_banner_image_url(payload.image_url) if payload.image_url and payload.image_url.strip() else None
    platform_publishing = _is_platform_publisher(user)
    price_rsd = 0.0 if platform_publishing else _money(float(slot.price_rsd or 0) * payload.days_count / 7)
    if user.advertiser_budget_rsd < price_rsd:
        raise HTTPException(400, f"Nedovoljno budžeta. Za ovaj zakup potrebno je {price_rsd:.0f} RSD.")
    if not platform_publishing:
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
        admin_note="Platformski banner čeka proveru." if platform_publishing else "Rezervacija čeka proveru administratora.",
        starts_at=starts_at,
        ends_at=ends_at,
    )
    db.add(banner)
    db.add(AdvertiserBudgetTransaction(
        advertiser_id=user.id,
        amount_rsd=-price_rsd if not platform_publishing else 0,
        tx_type="platform_banner_requested" if platform_publishing else "reserve_banner",
        description=f"Platformski banner bez naknade: {slot.title}" if platform_publishing else f"Rezervisan banner slot: {slot.title}",
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


def _public_app_url_from_request(request: Request) -> str:
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
        public_url = _public_app_url_from_request(request)
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
        return RedirectResponse(f"{_public_app_url_from_request(request)}/oglasivac/panel?payment=error", status_code=303)
    try:
        _capture_paypal_checkout(db, checkout)
        db.commit()
        result = "success"
    except HTTPException:
        db.rollback()
        result = "error"
    return RedirectResponse(f"{_public_app_url_from_request(request)}/oglasivac/panel?payment={result}", status_code=303)


@router.get("/advertiser/paypal/cancel")
def paypal_cancel(request: Request) -> RedirectResponse:
    return RedirectResponse(f"{_public_app_url_from_request(request)}/oglasivac/panel?payment=cancelled", status_code=303)


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
    if payload.requires_tester_enrollment:
        if payload.total_slots < payload.tester_required_count:
            raise HTTPException(400, "Broj mesta mora biti najmanje jednak broju obaveznih testera.")
        expected_reward = _money(payload.tester_daily_reward_rsd * payload.tester_duration_days)
        if payload.tester_daily_reward_rsd <= 0 or abs(float(payload.reward_rsd) - expected_reward) > 0.01:
            raise HTTPException(400, "Za zatvoreni beta test ukupna nagrada po testeru mora odgovarati dnevnoj nagradi pomnoženoj brojem dana.")
    platform_publishing = _is_platform_publisher(user)
    total = 0.0 if platform_publishing else _money(payload.reward_rsd * payload.total_slots * (1 + PLATFORM_FEE_PERCENT / 100))
    if user.advertiser_budget_rsd < total:
        raise HTTPException(400, f"Nedovoljno budžeta. Potrebno je {total:.0f} RSD.")
    task = Task(advertiser_id=user.id, title=payload.title.strip(), category=category, task_type=payload.task_type.strip(), target_url=(payload.target_url or "").strip() or None, description=payload.description.strip(), instructions=payload.instructions.strip(), proof_required=payload.proof_required.strip(), reward_rsd=payload.reward_rsd, platform_fee_percent=0.0 if platform_publishing else PLATFORM_FEE_PERCENT, total_slots=payload.total_slots, campaign_duration_days=payload.campaign_duration_days, repeat_interval_hours=0 if payload.requires_tester_enrollment else payload.repeat_interval_hours, submission_deadline_hours=payload.submission_deadline_hours, max_proof_revisions=payload.max_proof_revisions, min_quality_score=payload.min_quality_score, target_city=payload.target_city, target_age_group=payload.target_age_group, target_interests=payload.target_interests, requires_tester_enrollment=payload.requires_tester_enrollment, tester_required_count=payload.tester_required_count, tester_duration_days=payload.tester_duration_days, tester_daily_minutes=payload.tester_daily_minutes, tester_daily_reward_rsd=payload.tester_daily_reward_rsd, status="pending")
    if not platform_publishing:
        user.advertiser_budget_rsd = _money(user.advertiser_budget_rsd - total)
        user.advertiser_reserved_rsd = _money(user.advertiser_reserved_rsd + total)
    db.add(task)
    db.add(AdvertiserBudgetTransaction(
        advertiser_id=user.id,
        amount_rsd=-total if not platform_publishing else 0,
        tx_type="platform_campaign_created" if platform_publishing else "reserve_campaign",
        description=f"Platformska kampanja bez naknade: {task.title}" if platform_publishing else f"Rezervisan budžet za kampanju: {task.title}",
    ))
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
    if payload.requires_tester_enrollment:
        if payload.total_slots < payload.tester_required_count:
            raise HTTPException(400, "Broj mesta mora biti najmanje jednak broju obaveznih testera.")
        expected_reward = _money(payload.tester_daily_reward_rsd * payload.tester_duration_days)
        if payload.tester_daily_reward_rsd <= 0 or abs(float(payload.reward_rsd) - expected_reward) > 0.01:
            raise HTTPException(400, "Za zatvoreni beta test ukupna nagrada po testeru mora odgovarati dnevnoj nagradi pomnoženoj brojem dana.")

    platform_publishing = _is_platform_publisher(user)
    fee_percent = 0.0 if platform_publishing else float(task.platform_fee_percent or PLATFORM_FEE_PERCENT)
    old_total = 0.0 if platform_publishing else _money(task.reward_rsd * task.total_slots * (1 + fee_percent / 100))
    new_total = 0.0 if platform_publishing else _money(payload.reward_rsd * payload.total_slots * (1 + fee_percent / 100))
    difference = _money(new_total - old_total)
    if difference > 0 and user.advertiser_budget_rsd < difference:
        raise HTTPException(400, f"Nedovoljno budžeta za izmenu. Potrebno je još {difference:.0f} RSD.")
    if not platform_publishing:
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
    task.platform_fee_percent = fee_percent
    task.total_slots = payload.total_slots
    task.campaign_duration_days = payload.campaign_duration_days
    task.repeat_interval_hours = 0 if payload.requires_tester_enrollment else payload.repeat_interval_hours
    task.submission_deadline_hours = payload.submission_deadline_hours
    task.max_proof_revisions = payload.max_proof_revisions
    task.min_quality_score = payload.min_quality_score
    task.target_city = payload.target_city
    task.target_age_group = payload.target_age_group
    task.target_interests = payload.target_interests
    task.requires_tester_enrollment = payload.requires_tester_enrollment
    task.tester_required_count = payload.tester_required_count
    task.tester_duration_days = payload.tester_duration_days
    task.tester_daily_minutes = payload.tester_daily_minutes
    task.tester_daily_reward_rsd = payload.tester_daily_reward_rsd
    task.status = "pending"
    task.moderation_note = "Izmenjena kampanja ponovo čeka administrativnu proveru."
    if platform_publishing:
        db.add(AdvertiserBudgetTransaction(advertiser_id=user.id, amount_rsd=0, tx_type="platform_campaign_revised", description=f"Izmenjena platformska kampanja bez naknade: {task.title}"))
    elif difference:
        db.add(AdvertiserBudgetTransaction(
            advertiser_id=user.id,
            amount_rsd=-difference,
            tx_type="revise_campaign_reservation",
            description=f"Izmenjen rezervisani budžet za kampanju: {task.title}",
        ))
    db.commit()
    db.refresh(task)
    return {"campaign": _task_data(task), "reserved_rsd": new_total}


@router.patch("/advertiser/campaigns/{task_id}/lifecycle")
def update_campaign_lifecycle(task_id: int, payload: CampaignLifecyclePayload, request: Request, db: Session = Depends(get_db)) -> dict:
    """Let a campaign owner pause, resume, or finish an approved campaign."""
    user = _require_user(request, db, {"oglasivac", "admin"})
    task = db.query(Task).filter(Task.id == task_id, Task.advertiser_id == user.id).with_for_update().first()
    if not task:
        raise HTTPException(404, "Kampanja nije pronađena.")
    current_status = _status(task.status)
    now = datetime.utcnow()
    if payload.action == "pause":
        if current_status != "active":
            raise HTTPException(409, "Možeš pauzirati samo aktivnu kampanju.")
        if not task.starts_at:
            task.starts_at = now
            task.ends_at = now + timedelta(days=max(1, int(task.campaign_duration_days or 30)))
        task.status = "paused"
        task.paused_at = now
        task.moderation_note = "Kampanju je pauzirao oglašivač. Rok se produžava za vreme pauze."
    elif payload.action == "resume":
        if current_status != "paused":
            raise HTTPException(409, "Možeš nastaviti samo pauziranu kampanju.")
        if int(task.used_slots or 0) >= int(task.total_slots or 0):
            raise HTTPException(409, "Kampanja je već ispunila sve raspoložive pozicije.")
        if task.paused_at and task.ends_at:
            task.ends_at = task.ends_at + (now - task.paused_at)
        task.paused_at = None
        task.status = "active"
        task.moderation_note = "Kampanju je oglašivač ponovo aktivirao."
    else:
        if current_status not in {"active", "paused"}:
            raise HTTPException(409, "Možeš završiti samo aktivnu ili pauziranu kampanju.")
        released = _release_campaign_reservation(db, task, "ranije zaustavljanje oglašivača")
        task.status = "stopped"
        task.stopped_at = now
        task.paused_at = None
        task.moderation_note = f"Kampanju je oglašivač završio pre isteka. Vraćeno: {released:.0f} RSD."
    db.add(AuditLog(admin_id=user.id, action=f"advertiser_campaign_{payload.action}", entity_type="task", entity_id=task.id, reason=task.title))
    db.commit()
    db.refresh(task)
    return {"campaign": _task_data(task)}


def _admin_dashboard_data(db: Session) -> dict:
    now = datetime.utcnow()
    tracking_start = start_clean_pageview_measurement(db, now)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=6)
    active_start = now - timedelta(minutes=15)
    public_visits = db.query(PlatformVisitV117).filter(
        or_(
            PlatformVisitV117.path.in_(PUBLIC_PAGEVIEW_PATHS),
            PlatformVisitV117.path.like("/zadaci/%"),
        ),
        PlatformVisitV117.created_at >= tracking_start,
    )
    today_visits = public_visits.filter(PlatformVisitV117.created_at >= today_start)
    week_visits = public_visits.filter(PlatformVisitV117.created_at >= week_start)
    daily_visit_rows = (
        week_visits.with_entities(
            func.date(PlatformVisitV117.created_at).label("day"),
            func.count(PlatformVisitV117.id).label("views"),
            func.count(func.distinct(PlatformVisitV117.visitor_id)).label("unique_visitors"),
        )
        .group_by(func.date(PlatformVisitV117.created_at))
        .all()
    )
    daily_visits = {
        str(row.day): {"views": int(row.views or 0), "unique_visitors": int(row.unique_visitors or 0)}
        for row in daily_visit_rows
    }
    site_daily = []
    for offset in range(6, -1, -1):
        day = (today_start - timedelta(days=offset)).date().isoformat()
        counts = daily_visits.get(day, {"views": 0, "unique_visitors": 0})
        site_daily.append({"date": day, **counts})
    pending_submissions = db.query(TaskSubmission).filter(TaskSubmission.status == "pending").count()
    pending_withdrawals = db.query(Withdrawal).filter(Withdrawal.status == "pending").count()
    pending_campaigns = db.query(Task).filter(Task.status == "pending").count()
    pending_banners = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.status == "pending").count()
    pending_promotions = db.query(PaidPromotionRequestV111).filter(PaidPromotionRequestV111.status == "pending").count()
    funnel_events = db.query(PublicFunnelEventV12).all()
    paid_funnel_events = [event for event in funnel_events if event.source and event.source != "direct"]

    def funnel_visitors(event_type: str, events: list[PublicFunnelEventV12] | None = None) -> set[str]:
        return {
            event.visitor_id for event in (events if events is not None else paid_funnel_events)
            if event.event_type == event_type and event.visitor_id
        }

    source_keys = sorted({
        (event.source, event.medium, event.campaign)
        for event in paid_funnel_events if event.event_type == "ad_landing"
    })
    funnel_sources = []
    for source, medium, campaign in source_keys:
        source_events = [event for event in paid_funnel_events if (
            event.source, event.medium, event.campaign
        ) == (source, medium, campaign)]
        landings = funnel_visitors("ad_landing", source_events)
        funnel_sources.append({
            "source": source,
            "medium": medium,
            "campaign": campaign,
            "landings": len(landings),
            "opened": len(funnel_visitors("registration_opened", source_events)),
            "submitted": len(funnel_visitors("registration_submitted", source_events)),
            "failed": len(funnel_visitors("registration_failed", source_events)),
            "completed": len(funnel_visitors("registration_completed", source_events)),
        })
    funnel_sources.sort(key=lambda item: item["landings"], reverse=True)
    paid_landings = funnel_visitors("ad_landing")
    paid_completed = funnel_visitors("registration_completed")
    failure_reason_labels = {
        "email_taken": "Email je već registrovan",
        "phone_taken": "Telefon je već povezan sa nalogom",
        "terms_missing": "Uslovi nisu prihvaćeni",
        "invalid_phone": "Telefon nije ispravan",
        "invalid_referral": "Referral kod nije ispravan",
        "validation": "Nedostaje ili nije ispravan podatak",
        # request_error is retained only so that older, privacy-minimal events
        # stay intelligible. New browser events use one of the precise groups below.
        "request_error": "Ranije neodređena greška pri slanju",
        "network_error": "Prekinuta veza sa serverom",
        "server_error": "Server je privremeno bio nedostupan",
    }
    failure_reason_rows = db.query(
        PublicFunnelFailureReasonV12.reason,
        func.count(PublicFunnelFailureReasonV12.id).label("count"),
    ).filter(
        PublicFunnelFailureReasonV12.source.isnot(None),
        PublicFunnelFailureReasonV12.source != "direct",
    ).group_by(PublicFunnelFailureReasonV12.reason).order_by(
        func.count(PublicFunnelFailureReasonV12.id).desc()
    ).all()
    failure_reasons = [
        {
            "reason": row.reason,
            "label": failure_reason_labels.get(row.reason, "Nepoznata greška"),
            "count": int(row.count or 0),
        }
        for row in failure_reason_rows
    ]
    return {
        "metrics": {
            "users": db.query(User).filter(User.role == "korisnik").count(),
            "advertisers": db.query(User).filter(User.role == "oglasivac").count(),
            "active_tasks": db.query(Task).filter(Task.status == "active").count(),
            "pending_submissions": pending_submissions,
            "pending_withdrawals": pending_withdrawals,
            "pending_campaigns": pending_campaigns,
            "pending_banners": pending_banners,
            "pending_promotions": pending_promotions,
            "reserved_budget_rsd": _money(db.query(func.coalesce(func.sum(User.advertiser_reserved_rsd), 0)).scalar()),
            "site_views_today": today_visits.count(),
            "site_unique_today": today_visits.with_entities(PlatformVisitV117.visitor_id).distinct().count(),
            "site_views_7d": week_visits.count(),
            "site_unique_7d": week_visits.with_entities(PlatformVisitV117.visitor_id).distinct().count(),
            "site_views_total": public_visits.count(),
            "site_unique_total": public_visits.with_entities(PlatformVisitV117.visitor_id).distinct().count(),
            "site_active_now": public_visits.filter(
                PlatformVisitV117.created_at >= active_start
            ).with_entities(PlatformVisitV117.visitor_id).distinct().count(),
            "site_daily": site_daily,
            "site_tracking_started_at": tracking_start.isoformat() + "Z",
            "acquisition_funnel": {
                "landings": len(paid_landings),
                "opened": len(funnel_visitors("registration_opened")),
                "submitted": len(funnel_visitors("registration_submitted")),
                "failed": len(funnel_visitors("registration_failed")),
                "completed": len(paid_completed),
                "conversion_rate": round((len(paid_completed) / len(paid_landings) * 100) if paid_landings else 0, 1),
                "failure_reasons": failure_reasons,
                "sources": funnel_sources[:8],
            },
        }
    }


@router.get("/admin/dashboard")
def admin_dashboard(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    _expire_campaigns(db)
    dashboard = _admin_dashboard_data(db)
    db.commit()
    return dashboard


@router.post("/admin/analytics/reset")
def reset_admin_analytics(request: Request, db: Session = Depends(get_db)) -> dict:
    """Start a new clean public-navigation series without deleting business data."""
    user = _require_user(request, db, {"admin"})
    tracking_start = start_clean_pageview_measurement(db, datetime.utcnow(), force=True)
    started_at = tracking_start.isoformat() + "Z"
    db.add(AuditLog(
        admin_id=user.id,
        action="analytics_pageviews_reset",
        entity_type="PlatformVisitV117",
        entity_id=None,
        reason="Pokrenuta nova čista serija javnih navigacija; raniji analitički zapisi nisu obrisani iz baze.",
    ))
    db.commit()
    return {"deleted": 0, "started_at": started_at, "legacy_measurements_hidden": True}


@router.get("/admin/production-readiness")
def admin_production_readiness(request: Request, db: Session = Depends(get_db)) -> dict:
    """Report configuration facts without exposing any secret values."""
    _require_user(request, db, {"admin"})
    database_url = (os.getenv("DATABASE_URL") or "").strip().lower()
    checks = [
        {
            "key": "database",
            "label": "PostgreSQL baza",
            "ready": database_url.startswith(("postgres://", "postgresql://")),
            "action": "Podesi DATABASE_URL na Render Internal Database URL.",
        },
        {
            "key": "email",
            "label": "Transakcioni email",
            "ready": bool((os.getenv("SMTP_HOST") or "").strip() and (os.getenv("SMTP_SENDER") or os.getenv("SMTP_FROM") or "").strip()),
            "action": "Dodaj SMTP_HOST, SMTP_PORT, SMTP_SENDER, SMTP_USERNAME i SMTP_PASSWORD.",
        },
        {
            "key": "backup",
            "label": "Rezervne kopije baze",
            "ready": bool((os.getenv("DATABASE_BACKUP_URL") or os.getenv("BACKUP_DESTINATION") or "").strip() or (os.getenv("RENDER_POSTGRES_BACKUP_ENABLED") or "").lower() == "true"),
            "action": "U Renderu uključi PostgreSQL backup ili podesi DATABASE_BACKUP_URL ka bezbednoj destinaciji.",
        },
        {
            "key": "monitoring",
            "label": "Monitoring grešaka",
            "ready": bool((os.getenv("SENTRY_DSN") or os.getenv("ERROR_MONITORING_DSN") or "").strip()),
            "action": "Podesi SENTRY_DSN ili ERROR_MONITORING_DSN za spoljašnji monitoring.",
        },
    ]
    return {"checks": checks, "ready_count": sum(1 for item in checks if item["ready"]), "total": len(checks)}


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
        now = datetime.utcnow()
        planned_start = banner.starts_at or now
        if planned_start <= now:
            planned_start = now
        banner.status = "active"
        banner.starts_at = planned_start
        banner.ends_at = planned_start + timedelta(days=max(1, banner.days_count or 7))
        banner.admin_note = (payload.note or "").strip() or (
            "Zakup je odobren; prikaz počinje po rezervisanom terminu."
            if planned_start > now else "Zakup je odobren."
        )
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


@router.get("/admin/promotions")
def admin_promotions(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    _expire_promotions(db)
    items = db.query(PaidPromotionRequestV111).order_by(PaidPromotionRequestV111.created_at.desc()).limit(300).all()
    return {"promotions": [_promotion_data(item) for item in items]}


@router.patch("/admin/promotions/{promotion_id}")
def review_admin_promotion(
    promotion_id: int,
    payload: AdminPromotionStatusPayload,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    admin = _require_user(request, db, {"admin"})
    item = db.query(PaidPromotionRequestV111).filter(PaidPromotionRequestV111.id == promotion_id).with_for_update().first()
    if not item:
        raise HTTPException(404, "Promocija nije pronađena.")
    if item.status != "pending":
        raise HTTPException(409, "Samo promocija koja čeka proveru može biti obrađena.")
    advertiser = db.query(User).filter(User.id == item.advertiser_id).with_for_update().first()
    if not advertiser:
        raise HTTPException(404, "Oglašivač promocije nije pronađen.")
    amount = _money(item.price_rsd)
    if payload.status == "active":
        advertiser.advertiser_reserved_rsd = _money(max(0, float(advertiser.advertiser_reserved_rsd or 0) - amount))
        advertiser.advertiser_spent_rsd = _money(float(advertiser.advertiser_spent_rsd or 0) + amount)
        item.status = "active"
        item.starts_at = datetime.utcnow()
        item.ends_at = item.starts_at + timedelta(days=max(1, min(31, item.days_count or 7)))
        item.admin_note = (payload.note or "").strip() or "Promocija je odobrena i jasno će biti označena kao sponzorisana."
        tx_type = "activate_promotion"
        description = f"Odobrena promocija ({item.promotion_type}): {item.title}"
    else:
        advertiser.advertiser_reserved_rsd = _money(max(0, float(advertiser.advertiser_reserved_rsd or 0) - amount))
        advertiser.advertiser_budget_rsd = _money(float(advertiser.advertiser_budget_rsd or 0) + amount)
        item.status = "rejected"
        item.admin_note = (payload.note or "").strip() or "Promocija je odbijena, rezervisani budžet je vraćen."
        tx_type = "release_promotion_reservation"
        description = f"Vraćen budžet za odbijenu promociju: {item.title}"
    db.add(AdvertiserBudgetTransaction(advertiser_id=advertiser.id, amount_rsd=amount if payload.status == "rejected" else 0, tx_type=tx_type, description=description))
    _audit(db, admin, "promotion_review", "PaidPromotionRequestV111", item.id, item.status)
    db.commit()
    db.refresh(item)
    return {"promotion": _promotion_data(item)}


@router.get("/admin/users")
def admin_users(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    users = db.query(User).order_by(User.created_at.desc()).limit(300).all()
    return {"users": [_user_data(user) | {"created_at": _iso(user.created_at)} for user in users]}


@router.get("/admin/users/{user_id}/profile")
def admin_user_profile(user_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    """Return the operational profile an admin needs without exposing payout credentials."""
    _require_user(request, db, {"admin"})
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Korisnik nije pronađen.")

    submission_rows = db.query(TaskSubmission.status, func.count(TaskSubmission.id)).filter(
        TaskSubmission.user_id == user.id,
    ).group_by(TaskSubmission.status).all()
    withdrawal_rows = db.query(Withdrawal.status, func.count(Withdrawal.id)).filter(
        Withdrawal.user_id == user.id,
    ).group_by(Withdrawal.status).all()
    submissions = {str(status or "unknown").lower(): count for status, count in submission_rows}
    withdrawals = {str(status or "unknown").lower(): count for status, count in withdrawal_rows}

    return {
        "user": _user_data(user) | {"created_at": _iso(user.created_at)},
        "activity": {
            "submissions_total": sum(submissions.values()),
            "submissions_pending": submissions.get("pending", 0),
            "submissions_approved": submissions.get("approved", 0),
            "submissions_rejected": submissions.get("rejected", 0),
            "withdrawals_total": sum(withdrawals.values()),
            "withdrawals_pending": withdrawals.get("pending", 0),
        },
    }


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
    _expire_campaigns(db)
    tasks = db.query(Task).order_by(Task.created_at.desc()).limit(300).all()
    return {"campaigns": [
        _task_data(task) | {
            "advertiser_name": task.advertiser.full_name if task.advertiser else "Platforma",
            "platform_fee_percent": _money(task.platform_fee_percent or 0),
        }
        for task in tasks
    ]}


@router.patch("/admin/campaigns/{task_id}")
def update_campaign_status(task_id: int, payload: AdminStatusPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    admin = _require_user(request, db, {"admin"})
    task = db.query(Task).filter(Task.id == task_id).with_for_update().first()
    if not task:
        raise HTTPException(404, "Kampanja nije pronađena.")
    if payload.status not in {"active", "rejected", "paused", "needs_revision", "stopped"}:
        raise HTTPException(400, "Nevažeći status kampanje.")
    if payload.status == "rejected" and task.status in {"pending", "needs_revision"} and task.advertiser_id:
        advertiser = db.query(User).filter(User.id == task.advertiser_id).with_for_update().first()
        if advertiser and not _is_platform_publisher(advertiser):
            held_amount = _money(task.reward_rsd * task.total_slots * (1 + (task.platform_fee_percent or PLATFORM_FEE_PERCENT) / 100))
            advertiser.advertiser_reserved_rsd = _money(max(0, advertiser.advertiser_reserved_rsd - held_amount))
            advertiser.advertiser_budget_rsd = _money(advertiser.advertiser_budget_rsd + held_amount)
            db.add(AdvertiserBudgetTransaction(
                advertiser_id=advertiser.id,
                amount_rsd=held_amount,
                tx_type="release_campaign_reservation",
                description=f"Vraćen budžet za odbijenu kampanju: {task.title}",
            ))
    now = datetime.utcnow()
    current_status = _status(task.status)
    if payload.status == "active":
        if current_status == "stopped":
            raise HTTPException(409, "Ranije završena kampanja ne može se ponovo aktivirati.")
        if current_status == "paused" and task.paused_at and task.ends_at:
            task.ends_at = task.ends_at + (now - task.paused_at)
        if not task.starts_at:
            task.starts_at = now
            task.ends_at = now + timedelta(days=max(1, int(task.campaign_duration_days or 30)))
        task.paused_at = None
    elif payload.status == "paused":
        if current_status != "active":
            raise HTTPException(409, "Pauza je moguća samo za aktivnu kampanju.")
        task.paused_at = now
    elif payload.status == "stopped":
        if current_status not in {"active", "paused"}:
            raise HTTPException(409, "Zaustavljanje je moguće samo za aktivnu ili pauziranu kampanju.")
        released = _release_campaign_reservation(db, task, "ranije zaustavljanje administratora")
        task.stopped_at = now
        task.paused_at = None
        payload.note = (payload.note or "").strip() or f"Kampanju je administrator zaustavio pre isteka. Vraćeno: {released:.0f} RSD."
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


def _grant_referral_bonus_if_eligible(db: Session, user: User) -> bool:
    if not user.referred_by_id:
        return False
    # Serialize approvals for the same user before checking their first result.
    db.query(User).filter(User.id == user.id).with_for_update().first()
    approved_proofs = db.query(TaskSubmission).filter(
        TaskSubmission.user_id == user.id,
        TaskSubmission.status == "approved",
    ).count()
    approved_test_days = db.query(AppTesterDailyCheckin).filter(
        AppTesterDailyCheckin.user_id == user.id,
        AppTesterDailyCheckin.status == "approved",
        AppTesterDailyCheckin.reward_rsd > 0,
    ).count()
    already_paid = db.query(WalletTransaction.id).filter(
        WalletTransaction.user_id == user.id,
        WalletTransaction.tx_type == "referral_joiner_bonus",
    ).first()
    referrer = db.query(User).filter(
        User.id == user.referred_by_id,
        User.status == "active",
    ).first()
    if approved_proofs + approved_test_days != 1 or already_paid or not referrer or _open_risk_score(db, user.id) >= ANTI_FRAUD_HIGH_RISK_SCORE:
        return False
    user.balance_rsd = _money(user.balance_rsd + REFERRAL_JOINER_BONUS_RSD)
    user.lifetime_earned_rsd = _money(user.lifetime_earned_rsd + REFERRAL_JOINER_BONUS_RSD)
    referrer.balance_rsd = _money(referrer.balance_rsd + REFERRAL_INVITER_BONUS_RSD)
    referrer.lifetime_earned_rsd = _money(referrer.lifetime_earned_rsd + REFERRAL_INVITER_BONUS_RSD)
    db.add(WalletTransaction(user_id=user.id, amount_rsd=REFERRAL_JOINER_BONUS_RSD, tx_type="referral_joiner_bonus", description="Referral bonus nakon prvog odobrenog rezultata"))
    db.add(WalletTransaction(user_id=referrer.id, amount_rsd=REFERRAL_INVITER_BONUS_RSD, tx_type="referral_inviter_bonus", description=f"Referral bonus za prvi odobreni rezultat korisnika {user.full_name}"))
    db.add(Notification(user_id=user.id, title="Referral bonus je dodat", body=f"Dobio/la si {REFERRAL_JOINER_BONUS_RSD:.0f} RSD nakon prvog odobrenog rezultata.", status="unread"))
    db.add(Notification(user_id=referrer.id, title="Referral bonus je dodat", body=f"Dobio/la si {REFERRAL_INVITER_BONUS_RSD:.0f} RSD jer je {user.full_name} završio/la prvi odobreni rezultat.", status="unread"))
    return True


def _review_submission(submission_id: int, payload: AdminStatusPayload, actor: User, db: Session) -> dict:
    submission = db.query(TaskSubmission).filter(TaskSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(404, "Dokaz nije pronađen.")
    if payload.status not in {"approved", "rejected", "needs_revision"}:
        raise HTTPException(400, "Status dokaza mora biti approved, rejected ili needs_revision.")
    if submission.status != "pending":
        raise HTTPException(409, "Ovaj dokaz je već obrađen.")
    user = submission.user
    task = submission.task
    now = datetime.utcnow()
    if payload.status == "needs_revision":
        max_revisions = int(task.max_proof_revisions or 0) if task else 0
        if max_revisions <= int(submission.revision_count or 0):
            raise HTTPException(409, "Za ovaj dokaz više nije dozvoljena dorada.")
        submission.status = "needs_revision"
        submission.review_note = (payload.note or "Dopuni dokaz traženim informacijama i pošalji ga ponovo.").strip()
        submission.reviewed_at = now
        submission.revision_due_at = now + timedelta(hours=max(1, int(task.submission_deadline_hours or 24)))
        db.add(Notification(
            user_id=user.id,
            title="Potrebna je dopuna dokaza",
            body=f"Oglašivač je vratio dokaz na doradu za zadatak: {task.title if task else 'zadatak'}. Rok za ponovni dokaz je {submission.revision_due_at.strftime('%d.%m. u %H:%M')}.",
            status="unread",
        ))
        _audit(db, actor, "submission_revision_requested", "TaskSubmission", submission.id, payload.status)
        db.commit()
        return {"submission": _submission_data(submission)}

    submission.status = payload.status
    submission.review_note = payload.note
    submission.reviewed_at = now
    if payload.status == "approved":
        user.pending_rsd = _money(user.pending_rsd - submission.reward_rsd)
        user.balance_rsd = _money(user.balance_rsd + submission.reward_rsd)
        user.lifetime_earned_rsd = _money(user.lifetime_earned_rsd + submission.reward_rsd)
        db.add(WalletTransaction(user_id=user.id, amount_rsd=submission.reward_rsd, tx_type="task_reward", description=f"Odobren zadatak: {submission.task.title}"))
        _grant_referral_bonus_if_eligible(db, user)
        db.add(Notification(user_id=user.id, title="Zadatak je odobren", body=f"Nagrada od {submission.reward_rsd:.0f} RSD je prebačena u raspoloživi saldo.", status="unread"))
        advertiser = task.advertiser if task else None
        if advertiser and not _is_platform_publisher(advertiser):
            advertiser_cost = _money(submission.advertiser_cost_rsd)
            advertiser.advertiser_reserved_rsd = _money(max(0, advertiser.advertiser_reserved_rsd - advertiser_cost))
            advertiser.advertiser_spent_rsd = _money(advertiser.advertiser_spent_rsd + advertiser_cost)
            db.add(AdvertiserBudgetTransaction(
                advertiser_id=advertiser.id,
                amount_rsd=0,
                tx_type="spend_campaign_result",
                description=f"Odobren rezultat kampanje: {task.title}",
            ))
        elif advertiser:
            db.add(AdvertiserBudgetTransaction(
                advertiser_id=advertiser.id,
                amount_rsd=0,
                tx_type="platform_campaign_result_approved",
                description=f"Odobrena nagrada korisniku za platformsku kampanju: {task.title}",
            ))
    else:
        user.pending_rsd = _money(user.pending_rsd - submission.reward_rsd)
        db.add(Notification(user_id=user.id, title="Zadatak nije odobren", body=(payload.note or "Oglašivač nije odobrio poslati dokaz."), status="unread"))
        if submission.task:
            submission.task.used_slots = max(0, int(submission.task.used_slots or 0) - 1)
    _audit(db, actor, "submission_review", "TaskSubmission", submission.id, payload.status)
    db.commit()
    return {"submission": _submission_data(submission)}


@router.patch("/advertiser/submissions/{submission_id}")
def review_advertiser_submission(submission_id: int, payload: AdminStatusPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    """Only the campaign owner decides whether a normal task proof is accepted."""
    advertiser = _require_user(request, db, {"oglasivac", "admin"})
    submission = db.query(TaskSubmission).join(Task).filter(TaskSubmission.id == submission_id, Task.advertiser_id == advertiser.id).first()
    if not submission:
        raise HTTPException(404, "Dokaz za tvoju kampanju nije pronađen.")
    return _review_submission(submission_id, payload, advertiser, db)


@router.patch("/admin/submissions/{submission_id}")
def review_submission(submission_id: int, payload: AdminStatusPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    """Admin only resolves exceptional fraud or dispute cases, never routine proof review."""
    admin = _require_user(request, db, {"admin"})
    raise HTTPException(403, "Dokaze pregleda oglašivač. Admin ih obrađuje samo kroz poseban spor ili anti-fraud postupak.")


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
    if ticket.category == "account_deletion" and payload.status == "closed":
        raise HTTPException(409, "Zahtev za brisanje ne zatvaraj pre dokumentovanog završetka brisanja podataka.")
    ticket.status = payload.status
    ticket.updated_at = datetime.utcnow()
    if payload.note:
        db.add(SupportMessage(ticket_id=ticket.id, sender_id=admin.id, body=payload.note.strip()))
        db.add(Notification(
            user_id=ticket.user_id,
            title=f"Odgovor na tiket #{ticket.id}",
            body=f"Podrška je odgovorila na: {ticket.subject}",
            status="unread",
        ))
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
