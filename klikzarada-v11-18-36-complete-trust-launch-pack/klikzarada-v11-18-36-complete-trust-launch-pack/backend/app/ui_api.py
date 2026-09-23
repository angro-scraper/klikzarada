"""JSON API consumed by the React interface.

The legacy HTML routes intentionally remain available for operations and
backwards compatibility.  This module is the single browser-facing contract
for the new UI, so business data still lives in the existing database.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import get_db
from .models import (
    AdvertiserBudgetTransaction,
    AuditLog,
    SystemSetting,
    Task,
    TaskSourceV11,
    TaskSubmission,
    User,
    WalletTransaction,
    Withdrawal,
)
from .security import create_session_token, hash_password, make_referral_code, read_session_token, verify_password


router = APIRouter(prefix="/api/ui", tags=["KlikZarada UI"])

PLATFORM_FEE_PERCENT = 20.0
MIN_WITHDRAWAL_RSD = 1000.0


class Credentials(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=200)


class Registration(Credentials):
    full_name: str = Field(min_length=2, max_length=160)
    role: Literal["korisnik", "oglasivac"] = "korisnik"
    referral_code: str | None = Field(default=None, max_length=40)


class ProofPayload(BaseModel):
    proof: str = Field(min_length=3, max_length=5000)


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


class AdminStatusPayload(BaseModel):
    status: str = Field(min_length=2, max_length=40)
    note: str | None = Field(default=None, max_length=2000)


class SourcePayload(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    endpoint_url: str = Field(min_length=8, max_length=500)
    api_key: str | None = Field(default=None, max_length=250)
    import_mode: Literal["review", "sync", "manual"] = "review"


def _money(value: float | None) -> float:
    return round(float(value or 0), 2)


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
def login(payload: Credentials, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if not user or user.status != "active" or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Pogrešan email, lozinka ili blokiran nalog.")
    response.set_cookie("kz_session", create_session_token(user.id), httponly=True, samesite="lax", secure=False)
    return {"user": _user_data(user)}


@router.post("/auth/register", status_code=201)
def register(payload: Registration, response: Response, db: Session = Depends(get_db)) -> dict:
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email adresa je već registrovana.")
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
        referral_code=make_referral_code(payload.full_name),
        referred_by_id=referrer.id if referrer else None,
        company_name=payload.full_name.strip() if payload.role == "oglasivac" else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    response.set_cookie("kz_session", create_session_token(user.id), httponly=True, samesite="lax", secure=False)
    return {"user": _user_data(user)}


@router.post("/auth/logout", status_code=204)
def logout(response: Response) -> Response:
    response.delete_cookie("kz_session")
    return response


@router.get("/public/tasks")
def public_tasks(db: Session = Depends(get_db)) -> dict:
    tasks = db.query(Task).filter(Task.status == "active", Task.used_slots < Task.total_slots).order_by(Task.featured.desc(), Task.reward_rsd.desc()).limit(100).all()
    return {"tasks": [_task_data(task) for task in tasks]}


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
    user.full_name = payload.full_name.strip()
    user.phone = (payload.phone or "").strip() or None
    user.city = (payload.city or "").strip() or None
    user.payment_method = (payload.payment_method or "").strip() or None
    user.payment_details = (payload.payment_details or "").strip() or None
    db.commit()
    return {"user": _user_data(user)}


@router.post("/user/tasks/{task_id}/proof", status_code=201)
def submit_proof(task_id: int, payload: ProofPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik", "admin"})
    task = db.query(Task).filter(Task.id == task_id, Task.status == "active", Task.used_slots < Task.total_slots).first()
    if not task:
        raise HTTPException(404, "Zadatak nije dostupan.")
    existing = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id, TaskSubmission.task_id == task.id, TaskSubmission.status.in_(["pending", "approved"])).first()
    if existing:
        raise HTTPException(409, "Za ovaj zadatak je već poslat dokaz.")
    fee = _money(task.reward_rsd * (task.platform_fee_percent or PLATFORM_FEE_PERCENT) / 100)
    submission = TaskSubmission(user_id=user.id, task_id=task.id, proof=payload.proof.strip(), reward_rsd=task.reward_rsd, platform_fee_rsd=fee, advertiser_cost_rsd=_money(task.reward_rsd + fee), status="pending")
    task.used_slots += 1
    user.pending_rsd = _money(user.pending_rsd + task.reward_rsd)
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return {"submission": _submission_data(submission)}


@router.post("/user/withdrawals", status_code=201)
def request_withdrawal(payload: WithdrawalPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"korisnik", "admin"})
    if payload.amount_rsd < MIN_WITHDRAWAL_RSD:
        raise HTTPException(400, f"Minimalna isplata je {MIN_WITHDRAWAL_RSD:.0f} RSD.")
    if payload.amount_rsd > user.balance_rsd:
        raise HTTPException(400, "Nema dovoljno raspoloživog salda.")
    user.balance_rsd = _money(user.balance_rsd - payload.amount_rsd)
    user.payment_method = payload.payment_method.strip()
    user.payment_details = payload.payment_details.strip()
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
    }


@router.post("/advertiser/campaigns", status_code=201)
def create_campaign(payload: CampaignPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    user = _require_user(request, db, {"oglasivac", "admin"})
    total = _money(payload.reward_rsd * payload.total_slots * (1 + PLATFORM_FEE_PERCENT / 100))
    if user.advertiser_budget_rsd < total:
        raise HTTPException(400, f"Nedovoljno budžeta. Potrebno je {total:.0f} RSD.")
    task = Task(advertiser_id=user.id, title=payload.title.strip(), category=payload.category.strip() or "Promo", task_type=payload.task_type.strip(), target_url=(payload.target_url or "").strip() or None, description=payload.description.strip(), instructions=payload.instructions.strip(), proof_required=payload.proof_required.strip(), reward_rsd=payload.reward_rsd, platform_fee_percent=PLATFORM_FEE_PERCENT, total_slots=payload.total_slots, target_city=payload.target_city, target_age_group=payload.target_age_group, target_interests=payload.target_interests, status="pending")
    user.advertiser_budget_rsd = _money(user.advertiser_budget_rsd - total)
    user.advertiser_reserved_rsd = _money(user.advertiser_reserved_rsd + total)
    db.add(task)
    db.add(AdvertiserBudgetTransaction(advertiser_id=user.id, amount_rsd=-total, tx_type="reserve_campaign", description=f"Rezervisan budžet za kampanju: {task.title}"))
    db.commit()
    db.refresh(task)
    return {"campaign": _task_data(task), "reserved_rsd": total}


def _admin_dashboard_data(db: Session) -> dict:
    pending_submissions = db.query(TaskSubmission).filter(TaskSubmission.status == "pending").count()
    pending_withdrawals = db.query(Withdrawal).filter(Withdrawal.status == "pending").count()
    pending_campaigns = db.query(Task).filter(Task.status == "pending").count()
    return {
        "metrics": {
            "users": db.query(User).filter(User.role == "korisnik").count(),
            "advertisers": db.query(User).filter(User.role == "oglasivac").count(),
            "active_tasks": db.query(Task).filter(Task.status == "active").count(),
            "pending_submissions": pending_submissions,
            "pending_withdrawals": pending_withdrawals,
            "pending_campaigns": pending_campaigns,
            "reserved_budget_rsd": _money(db.query(func.coalesce(func.sum(User.advertiser_reserved_rsd), 0)).scalar()),
        }
    }


@router.get("/admin/dashboard")
def admin_dashboard(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    return _admin_dashboard_data(db)


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
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Kampanja nije pronađena.")
    if payload.status not in {"active", "rejected", "paused"}:
        raise HTTPException(400, "Nevažeći status kampanje.")
    task.status = payload.status
    task.moderation_note = payload.note
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
    else:
        user.pending_rsd = _money(user.pending_rsd - submission.reward_rsd)
    _audit(db, admin, "submission_review", "TaskSubmission", submission.id, payload.status)
    db.commit()
    return {"submission": _submission_data(submission)}


@router.get("/admin/withdrawals")
def admin_withdrawals(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    items = db.query(Withdrawal).order_by(Withdrawal.created_at.desc()).limit(300).all()
    return {"withdrawals": [{"id": item.id, "user_name": item.user.full_name if item.user else "Korisnik", "amount_rsd": _money(item.amount_rsd), "payment_method": item.payment_method, "payment_details": item.payment_details, "status": _status(item.status), "created_at": _iso(item.created_at)} for item in items]}


@router.patch("/admin/withdrawals/{withdrawal_id}")
def update_withdrawal(withdrawal_id: int, payload: AdminStatusPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    admin = _require_user(request, db, {"admin"})
    item = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    if not item:
        raise HTTPException(404, "Isplata nije pronađena.")
    if payload.status not in {"paid", "rejected"}:
        raise HTTPException(400, "Status isplate mora biti paid ili rejected.")
    if item.status != "pending":
        raise HTTPException(409, "Ova isplata je već obrađena.")
    item.status = payload.status
    item.admin_note = payload.note
    item.processed_at = datetime.utcnow()
    if payload.status == "rejected":
        item.user.balance_rsd = _money(item.user.balance_rsd + item.amount_rsd)
        db.add(WalletTransaction(user_id=item.user_id, amount_rsd=item.amount_rsd, tx_type="withdrawal_return", description="Vraćena odbijena isplata"))
    _audit(db, admin, "withdrawal_review", "Withdrawal", item.id, payload.status)
    db.commit()
    return {"withdrawal": {"id": item.id, "status": _status(item.status)}}


@router.get("/admin/task-sources")
def admin_task_sources(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_user(request, db, {"admin"})
    sources = db.query(TaskSourceV11).order_by(TaskSourceV11.created_at.desc()).all()
    return {"sources": [{"id": source.id, "name": source.name, "endpoint_url": source.endpoint_url, "source_type": source.source_type, "import_mode": source.import_mode, "status": source.status, "has_api_key": bool(source.api_key), "last_sync_at": _iso(source.last_sync_at), "created_at": _iso(source.created_at)} for source in sources]}


@router.post("/admin/task-sources", status_code=201)
def create_task_source(payload: SourcePayload, request: Request, db: Session = Depends(get_db)) -> dict:
    admin = _require_user(request, db, {"admin"})
    parsed = urlparse(payload.endpoint_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(400, "Endpoint mora biti javno dostupan HTTPS URL.")
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
    settings = db.query(SystemSetting).order_by(SystemSetting.key).all()
    return {"settings": [{"key": item.key, "value": item.value, "description": item.description} for item in settings]}
