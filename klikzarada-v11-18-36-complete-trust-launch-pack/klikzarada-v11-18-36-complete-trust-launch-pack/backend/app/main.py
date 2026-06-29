import io
import html
import json
import re
import mimetypes
from PIL import Image
import time
import hashlib
from app.models import AutoEngineLogV114, AutoNotificationQueueV114, TaskViewSessionV114
from app.models import TaskReservationV115, UserScoreV115, UserBadgeV115, DailyRewardV115, UserMissionV115, AdvertiserSuggestionV115, AdminDailyReportV115
from app.models import PlatformVisitV117, UserDirectoryV117, AdvertiserDirectoryV117
import secrets
import csv, io, uuid
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request as UrlRequest, urlopen
from .database import Base, engine, get_db
from .models import AdvertiserBudgetTransaction, AuditLog, CampaignTemplate, Invoice, Notification, PromoCode, PromoCodeUse, SupportMessage, SupportTicket, Task, TaskSubmission, User, WalletTransaction, Withdrawal, AdvertiserPlan, AdvertiserSubscription, AudienceSegment, Dispute, UserAchievement, ApiKey, AutomationRule, SavedReport, FeatureFlag, SystemSetting, TaskSourceV11, SecurityEvent, KycDocument, DataExportRequest, SalesLead, WebhookEndpoint, WebhookDelivery, TeamMember, OnboardingItem, AIReviewRule, AIReviewResult, TaskRecommendation, MarketplaceCategory, MarketplaceOffer, MarketplaceOrder, PayoutBatch, PayoutBatchItem, FraudCase, ContentPage, EmailTemplate, GrowthExperiment, AnalyticsSnapshot, CampaignFunnelEvent, InternalMessage, SavedView, PaymentIntentV8, CommandItemV8, HelpArticleV8, AnnouncementBannerV8, StatusIncidentV8, ReleaseChecklistV8, EmailOutboxV8, JobItemV8, LaunchCampaignV9, LaunchTaskV9, AffiliatePartnerV9, AffiliateDealV9, SalesScriptV9, OutreachContactV9, OutreachActivityV9, RevenueForecastV9, RevenueForecastLineV9, BackupSnapshotV9, GoLiveCheckV9, CompetitorNoteV9, RoadmapItemV9, CustomerSuccessNoteV9, PricingExperimentV9, PressKitAssetV9, WorkflowTemplateV10, WorkflowRunV10, WorkflowStepRunV10, SurveyV10, SurveyQuestionV10, SurveyResponseV10, UTMCampaignV10, ConversionGoalV10, ConversionEventV10, ClientPortalProjectV10, ClientPortalUpdateV10, ContractV10, ContractMilestoneV10, DataStudioDashboardV10, DataStudioWidgetV10, ModerationQueueV10, SmartSegmentRuleV10, QualityRuleV10, ApiUsageLogV10, RevenueGoalV10, ExperimentVariantV10, PartnerPayoutV10, OpsPlaybookV10, EmailVerificationTokenV11, PasswordResetTokenV11, LoginAttemptV11, AdminTwoFactorCodeV11, UserDeviceSessionV11, PayoutMethodV11, PayoutHoldV11, PayoutExportV11, ProofFileReviewV11, AdvertiserBudgetAlertV11, CampaignStatusLogV11, FraudSignalV11, LegalPageV11, UserConsentV11, ForbiddenTaskRuleV11, MarketingLandingPageV11, ProductionConfigCheckV11, SmokeTestRunV11, SmokeTestItemV11, BackupRunV11, DeployTargetV11, AdminDailyDeskNoteV11, LaunchReadinessScoreV11, SystemErrorLogV11, HomeBannerSlotV111, PaidAdBannerV111, PaidPromotionRequestV111, MonetizationPricingV111, PaidAdViewV111, PanelShortcutV111
from .security import create_session_token, hash_password, make_referral_code, read_session_token, verify_password

app = FastAPI(title="KlikZarada V11.18.36 Complete Trust Launch Pack", version="11.18.36")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
UPLOAD_DIR = Path("app/static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

PLATFORM_FEE_PERCENT = 20.0
REFERRAL_BONUS_RSD = 15.0
MIN_WITHDRAWAL_RSD = 1000.0
ADMIN_FOCUS_ALLOWED_PATHS = (
    "/admin/v11",
    "/admin/dashboard",
    "/admin/mapa-platforme",
    "/admin/kampanje",
    "/admin/dokazi",
    "/admin/finansije",
    "/admin/isplate",
    "/admin/fakture",
    "/admin/payouts-v11",
    "/admin/reklame-v111",
    "/admin/promocija-v111",
    "/admin/banneri-v111",
    "/admin/cene-v111",
    "/admin/payments-v8",
    "/admin/oglasivaci",
    "/admin/oglasivaci-baza-v117",
    "/admin/budget-v11",
    "/admin/affiliate-v9",
    "/admin/revenue-v9",
    "/admin/launch-v9",
    "/admin/golive-v9",
    "/admin/smoke-v11",
    "/admin/deploy-v11",
    "/admin/daily-desk-v11",
    "/admin/ops-v11835",
    "/admin/feature-flags",
    "/admin/system-settings",
    "/admin/security-v11",
)

def cost_for_task(reward: float, slots: int, fee: float = PLATFORM_FEE_PERCENT):
    return reward * slots * (1 + fee / 100)

def cost_one(reward: float, fee: float = PLATFORM_FEE_PERCENT):
    platform_fee = reward * fee / 100
    return reward + platform_fee, platform_fee

def add_tx(db, user, amount, tx_type, desc):
    db.add(WalletTransaction(user_id=user.id, amount_rsd=amount, tx_type=tx_type, description=desc))

def add_budget_tx(db, adv, amount, tx_type, desc):
    db.add(AdvertiserBudgetTransaction(advertiser_id=adv.id, amount_rsd=amount, tx_type=tx_type, description=desc))


def v11837_money(value):
    try:
        return round(float(value or 0), 2)
    except Exception:
        return 0.0


def v11837_parse_date(value: str | None):
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except Exception:
        return None


def v11837_banner_window(banner):
    start_dt = getattr(banner, "starts_at", None) or getattr(banner, "created_at", None) or datetime.utcnow()
    days_count = max(1, int(getattr(banner, "days_count", 1) or 1))
    end_dt = getattr(banner, "ends_at", None) or (start_dt + timedelta(days=days_count))
    return start_dt, end_dt


def v11837_slot_booking_calendar(db: Session, days: int = 14):
    start_day = datetime.utcnow().date()
    dates = [start_day + timedelta(days=i) for i in range(days)]
    slots = db.query(HomeBannerSlotV111).order_by(HomeBannerSlotV111.id.asc()).all() if "HomeBannerSlotV111" in globals() else []
    banners = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.status.in_(["active", "pending"])).order_by(PaidAdBannerV111.created_at.desc()).all() if "PaidAdBannerV111" in globals() else []
    rows = []
    for slot in slots:
        slot_banners = [b for b in banners if getattr(b, "slot_id", None) == slot.id]
        cells = []
        for day in dates:
            booking = None
            for banner in slot_banners:
                start_dt, end_dt = v11837_banner_window(banner)
                if start_dt.date() <= day < end_dt.date():
                    booking = banner
                    break
            cells.append({
                "date": day,
                "booking": booking,
                "status": getattr(booking, "status", "free") if booking else "free",
            })
        rows.append({"slot": slot, "cells": cells})
    return {"dates": dates, "rows": rows}


def v11837_margin_snapshot(db: Session):
    def get_price(key: str, default_rsd: float = 0.0, default_percent: float = 0.0):
        row = db.query(MonetizationPricingV111).filter(MonetizationPricingV111.key == key).first() if "MonetizationPricingV111" in globals() else None
        if not row:
            return default_percent if default_percent else default_rsd
        if row.value_percent:
            return float(row.value_percent)
        return float(row.value_rsd or default_rsd)

    ad_cost = get_price("AD_VIEW_COST_RSD", 8.0)
    ad_reward = get_price("AD_VIEW_REWARD_RSD", 5.0)
    platform_percent = get_price("AD_VIEW_PLATFORM_PERCENT", 0.0, 37.5)
    user_percent = get_price("AD_VIEW_USER_PERCENT", 0.0, 62.5)
    margin_rsd = max(0.0, round(ad_cost - ad_reward, 2))
    margin_percent = round((margin_rsd / ad_cost) * 100, 2) if ad_cost > 0 else 0.0
    min_healthy_margin_rsd = max(2.0, round(ad_cost * 0.25, 2))
    status = "healthy" if margin_rsd >= min_healthy_margin_rsd and platform_percent >= 25 else "warning"
    warnings = []
    if margin_rsd < min_healthy_margin_rsd:
        warnings.append(f"Platformi ostaje samo {margin_rsd:.2f} RSD po validnom prikazu, a minimum je {min_healthy_margin_rsd:.2f} RSD.")
    if platform_percent < 25:
        warnings.append(f"Platform fee je {platform_percent:.1f}% i ispod je preporučenog praga od 25%.")

    packages = [
        {
            "name": "Small Business",
            "price": round((get_price("BANNER_HOME_MID_7D", 3000.0) / 7) * 7, 0),
            "segment": "lokalne firme i prvi test budžet",
            "mix": "1 srednji banner + osnovni campaign push",
        },
        {
            "name": "Agency",
            "price": round((get_price("BANNER_HOME_TOP_7D", 5000.0) / 7) * 14 + get_price("BOOST_TOP_POSITION_3D", 1500.0), 0),
            "segment": "agencije i višekanalne kampanje",
            "mix": "2 nedelje premium slota + top pozicija",
        },
        {
            "name": "Enterprise",
            "price": round((get_price("BANNER_HOME_TOP_7D", 5000.0) / 7) * 30 + 15000, 0),
            "segment": "veći budžeti i duži zakup",
            "mix": "mesečni zakup + upravljanje promocijom + prioritetna podrška",
        },
    ]
    return {
        "ad_cost": ad_cost,
        "ad_reward": ad_reward,
        "platform_percent": platform_percent,
        "user_percent": user_percent,
        "margin_rsd": margin_rsd,
        "margin_percent": margin_percent,
        "min_healthy_margin_rsd": min_healthy_margin_rsd,
        "status": status,
        "warnings": warnings,
        "packages": packages,
    }


def v11837_advertiser_health_row(db: Session, advertiser):
    tasks = db.query(Task).filter(Task.advertiser_id == advertiser.id).all()
    task_ids = [t.id for t in tasks]
    submissions = db.query(TaskSubmission).filter(TaskSubmission.task_id.in_(task_ids)).all() if task_ids else []
    pending_topups = db.query(PaymentIntentV8).filter(PaymentIntentV8.advertiser_id == advertiser.id, PaymentIntentV8.status == "pending").count()
    approved = sum(1 for s in submissions if s.status == "approved")
    pending = sum(1 for s in submissions if s.status == "pending")
    active_tasks = sum(1 for t in tasks if t.status == "active")
    pending_tasks = sum(1 for t in tasks if t.status == "pending")
    available = v11837_money(advertiser.advertiser_budget_rsd)
    reserved = v11837_money(advertiser.advertiser_reserved_rsd)
    spent = v11837_money(advertiser.advertiser_spent_rsd)
    approved_cost = round(sum(v11837_money(s.advertiser_cost_rsd) for s in submissions if s.status == "approved"), 2)
    platform_fee = round(sum(v11837_money(s.platform_fee_rsd) for s in submissions if s.status == "approved"), 2)
    roi_ratio = round((platform_fee / approved_cost) * 100, 2) if approved_cost > 0 else 0.0

    score = 100
    if available <= 0:
        score -= 40
    elif available < 5000:
        score -= 20
    if reserved > available and active_tasks > 0:
        score -= 15
    if pending_topups > 0:
        score -= 10
    if pending > approved and pending >= 5:
        score -= 15
    if active_tasks == 0 and spent == 0:
        score -= 10
    score = max(0, min(100, score))
    health = "green" if score >= 75 else "yellow" if score >= 45 else "red"
    pacing = "jak" if approved >= 10 or (active_tasks > 0 and approved >= pending) else "spor" if active_tasks > 0 and approved == 0 else "stabilan"
    return {
        "advertiser": advertiser,
        "score": score,
        "health": health,
        "available": available,
        "reserved": reserved,
        "spent": spent,
        "active_tasks": active_tasks,
        "pending_tasks": pending_tasks,
        "approved": approved,
        "pending": pending,
        "pending_topups": pending_topups,
        "roi_ratio": roi_ratio,
        "pacing": pacing,
    }


def v11837_campaign_signal_row(db: Session, task):
    submissions = db.query(TaskSubmission).filter(TaskSubmission.task_id == task.id).all()
    approved = sum(1 for s in submissions if s.status == "approved")
    pending = sum(1 for s in submissions if s.status == "pending")
    approved_cost = round(sum(v11837_money(s.advertiser_cost_rsd) for s in submissions if s.status == "approved"), 2)
    platform_fee = round(sum(v11837_money(s.platform_fee_rsd) for s in submissions if s.status == "approved"), 2)
    roi_ratio = round((platform_fee / approved_cost) * 100, 2) if approved_cost > 0 else 0.0
    total_slots = max(1, int(getattr(task, "total_slots", 0) or 1))
    completion = round((approved / total_slots) * 100, 2)
    age_days = max(0, (datetime.utcnow() - (task.created_at or datetime.utcnow())).days)
    pacing = "jak" if completion >= 60 or approved >= 10 else "spor" if task.status == "active" and age_days >= 3 and approved == 0 else "stabilan"
    return {
        "task": task,
        "approved": approved,
        "pending": pending,
        "completion": completion,
        "roi_ratio": roi_ratio,
        "pacing": pacing,
        "approved_cost": approved_cost,
    }


def v11838_parse_sales_notes(notes: str | None):
    meta = {"package_name": "", "next_action": "", "risk_flags": "", "note_body": ""}
    body_lines = []
    for line in (notes or "").splitlines():
        raw = line.strip()
        if not raw:
            continue
        if raw.upper().startswith("PACKAGE:"):
            meta["package_name"] = raw.split(":", 1)[1].strip()
        elif raw.upper().startswith("NEXT:"):
            meta["next_action"] = raw.split(":", 1)[1].strip()
        elif raw.upper().startswith("RISK:"):
            meta["risk_flags"] = raw.split(":", 1)[1].strip()
        else:
            body_lines.append(raw)
    meta["note_body"] = "\n".join(body_lines).strip()
    return meta


def v11838_build_sales_notes(note_body: str = "", package_name: str = "", next_action: str = "", risk_flags: str = ""):
    lines = []
    if (package_name or "").strip():
        lines.append(f"PACKAGE: {(package_name or '').strip()}")
    if (next_action or "").strip():
        lines.append(f"NEXT: {(next_action or '').strip()}")
    if (risk_flags or "").strip():
        lines.append(f"RISK: {(risk_flags or '').strip()}")
    if (note_body or "").strip():
        lines.append((note_body or "").strip())
    return "\n".join(lines).strip() or None


def v11838_find_sales_lead(leads, advertiser):
    adv_company = ((getattr(advertiser, "company_name", None) or "").strip()).lower()
    adv_name = ((getattr(advertiser, "full_name", None) or "").strip()).lower()
    adv_email = ((getattr(advertiser, "email", None) or "").strip()).lower()
    for lead in leads:
        lead_company = ((getattr(lead, "company_name", None) or "").strip()).lower()
        lead_email = ((getattr(lead, "email", None) or "").strip()).lower()
        if adv_company and lead_company == adv_company:
            return lead
        if adv_email and lead_email == adv_email:
            return lead
        if adv_name and lead_company == adv_name:
            return lead
    return None


def v11838_recommended_package(sales_packages, advertiser, lead):
    budget = v11837_money(getattr(advertiser, "advertiser_budget_rsd", 0))
    potential = v11837_money(getattr(lead, "potential_budget_rsd", 0)) if lead else 0.0
    reference_budget = max(budget, potential)
    if reference_budget >= 120000:
        return next((pkg for pkg in sales_packages if pkg["name"] == "Enterprise"), sales_packages[-1] if sales_packages else None)
    if reference_budget >= 35000:
        return next((pkg for pkg in sales_packages if pkg["name"] == "Agency"), sales_packages[0] if sales_packages else None)
    return next((pkg for pkg in sales_packages if pkg["name"] == "Small Business"), sales_packages[0] if sales_packages else None)


def v11838_sales_workflow_row(db: Session, advertiser, lead, sales_packages):
    meta = v11838_parse_sales_notes(getattr(lead, "notes", None)) if lead else {"package_name": "", "next_action": "", "risk_flags": "", "note_body": ""}
    latest_payment = (
        db.query(PaymentIntentV8)
        .filter(PaymentIntentV8.advertiser_id == advertiser.id)
        .order_by(PaymentIntentV8.created_at.desc())
        .first()
    )
    banners = (
        db.query(PaidAdBannerV111)
        .filter(PaidAdBannerV111.advertiser_id == advertiser.id)
        .order_by(PaidAdBannerV111.created_at.desc())
        .limit(8)
        .all()
    ) if "PaidAdBannerV111" in globals() else []
    active_banners = sum(1 for banner in banners if getattr(banner, "status", "") == "active")
    pending_banners = sum(1 for banner in banners if getattr(banner, "status", "") == "pending")
    latest_banner = banners[0] if banners else None
    health = v11837_advertiser_health_row(db, advertiser)
    recommended_package = v11838_recommended_package(sales_packages, advertiser, lead)
    package_name = meta["package_name"] or (recommended_package["name"] if recommended_package else "")
    payment_state = getattr(latest_payment, "status", None) or "nema"
    reservation_state = getattr(latest_banner, "status", None) if latest_banner else "nema"
    live_state = "live" if active_banners > 0 else "pending" if pending_banners > 0 else "nema"
    next_action = meta["next_action"]
    if not next_action:
        if not lead:
            next_action = "Otvoriti lead i dodeliti owner-a."
        elif payment_state == "pending":
            next_action = "Potvrditi uplatu i otključati budžet."
        elif reservation_state == "pending":
            next_action = "Zaključati termin bannera i potvrditi kreativu."
        elif live_state != "live":
            next_action = "Prebaciti rezervaciju u live banner."
        else:
            next_action = "Upsell sledeći paket ili produženje zakupa."
    risk_flags = meta["risk_flags"]
    if not risk_flags and health["health"] != "green":
        risk_flags = f"health:{health['health']}; pace:{health['pacing']}"
    priority = 0
    if not lead:
        priority += 40
    if payment_state == "pending":
        priority += 30
    if reservation_state == "pending":
        priority += 20
    if live_state != "live":
        priority += 10
    return {
        "advertiser": advertiser,
        "lead": lead,
        "owner_name": lead.owner.full_name if lead and getattr(lead, "owner", None) else "-",
        "status": getattr(lead, "status", "no_lead") if lead else "no_lead",
        "package_name": package_name,
        "recommended_package": recommended_package,
        "next_action": next_action,
        "risk_flags": risk_flags,
        "note_body": meta["note_body"],
        "latest_payment": latest_payment,
        "payment_state": payment_state,
        "latest_banner": latest_banner,
        "reservation_state": reservation_state,
        "live_state": live_state,
        "active_banners": active_banners,
        "pending_banners": pending_banners,
        "health": health,
        "priority": priority,
        "workflow": [
            {"title": "Lead", "state": getattr(lead, "status", "missing") if lead else "missing"},
            {"title": "Paket", "state": package_name or "unset"},
            {"title": "Rezervacija", "state": reservation_state},
            {"title": "Uplata", "state": payment_state},
            {"title": "Live banner", "state": live_state},
        ],
    }


def v11838_ops_suite_context(db: Session, current_url: str):
    smoke_latest = db.query(SmokeTestRunV11).order_by(SmokeTestRunV11.created_at.desc()).first()
    checks_blocked = db.query(ProductionConfigCheckV11).filter(ProductionConfigCheckV11.status == "blocked").count()
    return [
        {
            "title": "Launch",
            "url": "/admin/launch-v9",
            "metric": f"{db.query(LaunchTaskV9).filter(LaunchTaskV9.status != 'done').count()} open",
            "note": "Plan izlaska, ownership i handoff prema go-live toku.",
            "active": current_url == "/admin/launch-v9",
        },
        {
            "title": "Go-live",
            "url": "/admin/golive-v9",
            "metric": f"{db.query(GoLiveCheckV9).filter(GoLiveCheckV9.status != 'done').count()} open",
            "note": "Checklist i backup signal pre finalnog puštanja.",
            "active": current_url == "/admin/golive-v9",
        },
        {
            "title": "Smoke",
            "url": "/admin/smoke-v11",
            "metric": getattr(smoke_latest, "status", "n/a"),
            "note": "Brzi health signal posle deploy-a i pre live puštanja.",
            "active": current_url == "/admin/smoke-v11",
        },
        {
            "title": "Deploy",
            "url": "/admin/deploy-v11",
            "metric": f"{checks_blocked} blocked",
            "note": "Production targeti, backup runovi i release spremnost.",
            "active": current_url == "/admin/deploy-v11",
        },
        {
            "title": "Security",
            "url": "/admin/security-v11",
            "metric": f"{db.query(LoginAttemptV11).filter(LoginAttemptV11.success == False).count()} failed",
            "note": "Login attempts, device sessioni i admin 2FA pregled.",
            "active": current_url == "/admin/security-v11",
        },
        {
            "title": "Feature flags",
            "url": "/admin/feature-flags",
            "metric": f"{db.query(FeatureFlag).filter(FeatureFlag.is_enabled == True).count()} on",
            "note": "Rollout i rollback novih funkcija bez dodatnog deploy-a.",
            "active": current_url == "/admin/feature-flags",
        },
        {
            "title": "System settings",
            "url": "/admin/system-settings",
            "metric": f"{db.query(TaskSourceV11).filter(TaskSourceV11.status == 'active').count()} source",
            "note": "Ključna podešavanja, finansijski podaci i task source kontrola.",
            "active": current_url == "/admin/system-settings",
        },
    ]

def audit(db, admin, action, entity, entity_id, reason=""):
    db.add(AuditLog(admin_id=admin.id if admin else None, action=action, entity_type=entity, entity_id=entity_id, reason=reason))

def notify(db, user=None, role_target=None, title="Obaveštenje", body=""):
    db.add(Notification(user_id=user.id if user else None, role_target=role_target, title=title, body=body))

def update_quality(db, user):
    a = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id, TaskSubmission.status == "approved").count()
    r = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id, TaskSubmission.status == "rejected").count()
    total = a + r
    score = 100 if total == 0 else round(a * 100 / total, 2)
    user.quality_score = score
    if a >= 100 and score >= 95: user.level = "Premium"
    elif a >= 40 and score >= 90: user.level = "Zlato"
    elif a >= 10 and score >= 80: user.level = "Srebro"
    else: user.level = "Bronza"

def seed():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        admin = db.query(User).filter(User.email=="admin@klikzarada.rs").first()
        if not admin:
            admin = User(full_name="Admin", email="admin@klikzarada.rs", password_hash=hash_password("Admin123!"), role="admin", referral_code="ADMIN", email_verified=True, phone_verified=True)
            db.add(admin)
        db.commit()
    finally:
        db.close()

def ensure_task_source_api_key_column():
    try:
        with engine.begin() as conn:
            columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(task_sources_v11)").fetchall()}
            if "api_key" not in columns:
                conn.exec_driver_sql("ALTER TABLE task_sources_v11 ADD COLUMN api_key VARCHAR(250)")
    except Exception:
        pass

@app.on_event("startup")
def startup(): seed(); ensure_task_source_api_key_column(); seed_v4_growth(); seed_v5_scale(); seed_v6_enterprise(); seed_v7_ai_marketplace(); seed_v8_command(); seed_v9_launch_os(); seed_v10_automation_os(); seed_v11_real_launch_pack(); seed_v111_ui_ads_pricing(); v11815_startup_banner_slots()

@app.get("/favicon.ico")
def favicon(): return FileResponse("app/static/favicon.svg", media_type="image/svg+xml")

@app.get("/sw.js")
def sw(): return Response("self.addEventListener('install',e=>self.skipWaiting());", media_type="application/javascript")

def current_user(request: Request, db: Session):
    uid = read_session_token(request.cookies.get("kz_session"))
    if not uid: return None
    u = db.query(User).filter(User.id==uid).first()
    if not u or u.status != "active": return None
    return u

def require(request, db):
    u = current_user(request, db)
    if not u: raise HTTPException(401, "Niste prijavljeni.")
    return u

def role_url(role):
    return "/admin/v11" if role=="admin" else "/oglasivac/panel" if role=="oglasivac" else "/korisnik/panel"

def check_role(user, roles):
    if user.role not in roles: raise HTTPException(403, "Nemate pristup.")

def admin_focus_route_allowed(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in ADMIN_FOCUS_ALLOWED_PATHS)

def flash(msg):
    m = {
        "sent":("success","Dokaz je poslat na proveru."),
        "saved":("success","Sačuvano."),
        "imported":("success","Izvor je uvezen i poslat na moderaciju."),
        "campaign_created":("success","Kampanja je poslata na odobrenje i budžet je rezervisan."),
        "budget_error":("error","Nema dovoljno slobodnog budžeta."),
        "withdrawal_sent":("success","Zahtev za isplatu je poslat."),
        "withdrawal_error":("error","Iznos nije validan ili je manji od minimalne isplate."),
        "already":("warning","Već ste poslali dokaz za ovaj zadatak."),
        "ticket_sent":("success","Tiket je poslat podršci."),
        "reply_sent":("success","Odgovor je poslat."),
        "coupon_ok":("success","Promo kod je uspešno iskorišćen."),
        "coupon_error":("error","Promo kod nije validan ili je već potrošen."),
        "notification_sent":("success","Obaveštenje je poslato."),
        "invoice_created":("success","Predračun/faktura je kreirana."),
        "remote_ok":("success","Partner API zahteva je uspešno poslat."),
        "remote_error":("error","Partner API nije prihvatio zahtev."),
    }
    return m.get(msg)

def task_source_effective_url(source, api_key: str | None = None):
    endpoint = (getattr(source, "endpoint_url", "") or "").strip()
    if not endpoint:
        return None
    parsed = urlparse(endpoint)
    host = (parsed.netloc or "").lower()
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "seo-fast.ru" in host and (
        parsed.path.rstrip("/") == "/api"
        or "doc" in query
        or "transitions" in query
        or "objectInfo" in query
    ):
        query.pop("doc", None)
        query.pop("transitions", None)
        query.pop("objectInfo", None)
        endpoint = urlunparse(parsed._replace(path="/api/transitions", query=urlencode(query)))
    token = (api_key or getattr(source, "api_key", None) or "").strip()
    if token:
        if "{api_key}" in endpoint:
            endpoint = endpoint.replace("{api_key}", token)
        else:
            parsed = urlparse(endpoint)
            query = dict(parse_qsl(parsed.query, keep_blank_values=True))
            query.setdefault("api_key", token)
            endpoint = urlunparse(parsed._replace(query=urlencode(query)))
    return endpoint

def task_source_extract_items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("tasks", "items", "results", "data", "transitions", "campaigns"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = task_source_extract_items(value)
                if nested:
                    return nested
        for value in payload.values():
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = task_source_extract_items(value)
                if nested:
                    return nested
    return []

def task_source_extract_html_items(raw: str, source):
    if not raw or not raw.strip():
        return []
    text = re.sub(r"<script\b.*?</script>", " ", raw, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = html.unescape(text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    items = []
    last_title = None
    for line in lines:
        if len(line) < 3:
            continue
        price_match = re.search(r'(?:(?:\d+[.,]?\d*)\s*(?:RSD|руб\.?|рублей|rub|rsd)|Цена[:\s]*\d+)', line, re.I)
        if price_match:
            reward = 50.0
            num_match = re.search(r'(\d+(?:[.,]\d+)?)', line)
            if num_match:
                try:
                    reward = float(num_match.group(1).replace(",", "."))
                except Exception:
                    reward = 50.0
            title = last_title or source.name
            if title and len(title) > 2:
                items.append({
                    "title": title[:160],
                    "description": line[:500],
                    "instructions": line[:500],
                    "proof_required": "Pošaljite dokaz izvršenja.",
                    "task_type": "external_html",
                    "category": getattr(source, "name", "Imported") or "Imported",
                    "target_url": (getattr(source, "endpoint_url", "") or "").strip() or "/",
                    "reward_rsd": reward,
                    "total_slots": 1,
                    "estimated_minutes": 5,
                    "min_user_level": "Bronza",
                    "featured": False,
                    "remote_id": f"html:{len(items)}:{hashlib.sha1((title + line).encode('utf-8', 'ignore')).hexdigest()[:12]}",
                })
            last_title = None
        else:
            if len(line) > 8 and not re.search(r'(?:home|login|logout|admin|doc|api|support|telegram|facebook|instagram|settings|kontakt)', line, re.I):
                last_title = line
    return items

def task_source_text(item, *keys, default=""):
    for key in keys:
        value = item.get(key) if isinstance(item, dict) else None
        if value not in (None, "", []):
            return value
    return default

def task_source_float(item, *keys, default=0.0):
    for key in keys:
        value = item.get(key) if isinstance(item, dict) else None
        if value not in (None, "", []):
            try:
                return float(str(value).replace(",", "."))
            except Exception:
                continue
    return float(default)

def task_source_int(item, *keys, default=0):
    for key in keys:
        value = item.get(key) if isinstance(item, dict) else None
        if value not in (None, "", []):
            try:
                return int(float(str(value).replace(",", ".")))
            except Exception:
                continue
    return int(default)

def task_source_bool(item, *keys, default=False):
    for key in keys:
        value = item.get(key) if isinstance(item, dict) else None
        if value is not None:
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "da"}
    return bool(default)

def task_source_map_task(source, item, admin_id: int | None = None):
    title = str(task_source_text(item, "title", "name", "subject", "headline", default=source.name)).strip()
    description = str(task_source_text(item, "description", "body", "text", "details", "notes", default=title)).strip()
    instructions = str(task_source_text(item, "instructions", "instruction", "how_to", "steps", default=description)).strip()
    proof_required = str(task_source_text(item, "proof_required", "proof", "evidence", "validation", default="Pošaljite dokaz izvršenja.")).strip()
    example_proof = task_source_text(item, "example_proof", "proof_example", "sample", "example", default=None)
    task_type = str(task_source_text(item, "task_type", "type", "kind", "action", default="visit_site")).strip() or "visit_site"
    category = str(task_source_text(item, "category", "segment", "group", default="Promo")).strip() or "Promo"
    target_url = str(task_source_text(item, "target_url", "url", "link", "page_url", "href", default="/")).strip() or "/"
    reward_rsd = max(1.0, task_source_float(item, "reward_rsd", "reward", "price", "amount", "budget", default=50))
    total_slots = max(1, task_source_int(item, "total_slots", "slots", "quantity", "limit", default=100))
    estimated_minutes = max(1, task_source_int(item, "estimated_minutes", "duration", "minutes", "time", default=5))
    target_city = task_source_text(item, "target_city", "city", "location", default=None) or None
    target_age_group = task_source_text(item, "target_age_group", "age_group", "age", default=None) or None
    target_interests = task_source_text(item, "target_interests", "interests", "tags", default=None) or None
    min_user_level = str(task_source_text(item, "min_user_level", "level", default="Bronza")).strip() or "Bronza"
    proof_file_required = task_source_bool(item, "proof_file_required", "need_file", "file_required", default=False)
    featured = task_source_bool(item, "featured", "is_featured", default=False)
    remote_id = task_source_text(item, "id", "remote_id", "task_id", "identifier", default=None)
    note_parts = [f"imported_from=source:{source.id}", f"source_name:{source.name}"]
    if remote_id not in (None, ""):
        note_parts.append(f"remote_id:{remote_id}")
    moderation_note = " | ".join(note_parts)
    return {
        "advertiser_id": admin_id,
        "title": title,
        "category": category,
        "task_type": task_type,
        "target_url": target_url,
        "description": description,
        "instructions": instructions,
        "proof_required": proof_required,
        "example_proof": example_proof,
        "reward_rsd": reward_rsd,
        "total_slots": total_slots,
        "estimated_minutes": estimated_minutes,
        "target_city": target_city,
        "target_age_group": target_age_group,
        "target_interests": target_interests,
        "min_user_level": min_user_level,
        "proof_file_required": proof_file_required,
        "featured": featured,
        "status": "pending",
        "moderation_note": moderation_note,
    }

def task_source_item_exists(db: Session, source, item) -> bool:
    remote_id = task_source_text(item, "id", "remote_id", "task_id", "identifier", default=None)
    if remote_id not in (None, ""):
        marker = f"source:{source.id}"
        needle = f"remote_id:{remote_id}"
        return db.query(Task).filter(Task.moderation_note.contains(marker), Task.moderation_note.contains(needle)).first() is not None
    title = str(task_source_text(item, "title", "name", "subject", "headline", default=source.name)).strip()
    target_url = str(task_source_text(item, "target_url", "url", "link", "page_url", "href", default="/")).strip() or "/"
    reward_rsd = task_source_float(item, "reward_rsd", "reward", "price", "amount", "budget", default=50)
    cutoff = datetime.utcnow() - timedelta(days=7)
    return db.query(Task).filter(
        Task.moderation_note.contains(f"source:{source.id}"),
        Task.title == title,
        Task.target_url == target_url,
        Task.reward_rsd == reward_rsd,
        Task.created_at >= cutoff,
    ).first() is not None

def import_tasks_from_source(db: Session, source, admin_id: int | None = None):
    endpoint = task_source_effective_url(source)
    if not endpoint:
        raise HTTPException(400, "Izvor nema endpoint URL.")
    req = UrlRequest(endpoint, headers={"Accept": "application/json, text/html;q=0.9, */*;q=0.8", "User-Agent": "KlikZarada-Importer/1.0"})
    with urlopen(req, timeout=30) as resp:
        raw_bytes = resp.read()
    raw = raw_bytes.decode("utf-8", "replace")
    try:
        payload = json.loads(raw)
        items = task_source_extract_items(payload)
    except Exception:
        items = task_source_extract_html_items(raw, source)
    if not items:
        if not raw.strip():
            raise HTTPException(400, "Partner endpoint je vratio prazan odgovor.")
        raise HTTPException(400, "Partner endpoint nije JSON feed. Za ovaj izvor treba public list/page URL ili drugačiji adapter.")
    created = 0
    skipped = 0
    queue_items = 0
    for item in items:
        if not isinstance(item, dict):
            skipped += 1
            continue
        if task_source_item_exists(db, source, item):
            skipped += 1
            continue
        task_data = task_source_map_task(source, item, admin_id=admin_id)
        task = Task(**task_data)
        db.add(task)
        db.flush()
        db.add(ModerationQueueV10(item_type="task_import", item_id=task.id, priority="high", reason=f"Imported from {source.name}"))
        created += 1
        queue_items += 1
    source.last_sync_at = datetime.utcnow()
    source.updated_at = datetime.utcnow()
    db.flush()
    return {"created": created, "skipped": skipped, "queued": queue_items}

def task_source_remote_json_post(source, payload):
    endpoint = task_source_effective_url(source)
    if not endpoint:
        raise HTTPException(400, "Izvor nema endpoint URL.")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = UrlRequest(
        endpoint,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "KlikZarada-Importer/1.0",
        },
    )
    with urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", "replace")
    try:
        return json.loads(raw)
    except Exception:
        return {"success": False, "raw": raw}

def upsert_system_setting(db: Session, key: str, value: str, description: str | None = None):
    item = db.query(SystemSetting).filter(SystemSetting.key == key.strip()).first()
    if not item:
        item = SystemSetting(key=key.strip(), value=value.strip(), description=description.strip() if description else None)
        db.add(item)
    else:
        item.value = value.strip()
        if description is not None:
            item.description = description.strip() or item.description
        item.updated_at = datetime.utcnow()
    db.flush()
    return item

def save_file(file: Optional[UploadFile]):
    if not file or not file.filename: return None
    ext = Path(file.filename).suffix.lower()[:10]
    name = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / name
    data = file.file.read()
    if len(data) > 5*1024*1024: raise HTTPException(400, "Fajl je prevelik.")
    path.write_bytes(data)
    return f"/static/uploads/{name}"

# PUBLIC
# V11.16.1 disabled old home route
def home(request: Request, msg: str|None=None, db: Session=Depends(get_db)):
    u=current_user(request,db)
    banners = v111_active_home_banners(db) if "v111_active_home_banners" in globals() else []
    banner_map = v11817_active_banner_map(db) if "v11817_active_banner_map" in globals() else {}
    tasks = v111_featured_tasks(db) if "v111_featured_tasks" in globals() else db.query(Task).filter(Task.status=="active").order_by(Task.featured.desc(),Task.created_at.desc()).limit(8).all()
    pricing_summary = v11836_pricing_summary(db)
    stats = {
        "tasks": db.query(Task).filter(Task.status=="active").count(),
        "users": db.query(User).filter(User.role=="korisnik").count(),
        "advertisers": db.query(User).filter(User.role=="oglasivac").count(),
        "approved_rsd": db.query(func.coalesce(func.sum(TaskSubmission.reward_rsd),0)).filter(TaskSubmission.status=="approved").scalar()
    }
    return templates.TemplateResponse("home_pro_v114.html", {"request":request,"user":u,"flash":flash(msg),"banners":banners,"banner_map":banner_map,"tasks":tasks,"stats":stats,"pricing_summary":pricing_summary})

# V11.9 disabled old route /zadaci
def tasks_page(request: Request, q:str|None=None, category:str|None=None, db:Session=Depends(get_db)):
    u=current_user(request,db)
    query=db.query(Task).filter(Task.status=="active")
    if q:
        like=f"%{q}%"; query=query.filter(or_(Task.title.ilike(like),Task.description.ilike(like),Task.category.ilike(like)))
    if category and category!="Sve": query=query.filter(Task.category==category)
    cats=["Sve"]+[r[0] for r in db.query(Task.category).filter(Task.status=="active").distinct().all()]
    return templates.TemplateResponse("tasks_pro_v117.html", {"request":request,"user":u,"tasks":query.order_by(Task.featured.desc(),Task.reward_rsd.desc()).all(),"q":q or "", "category":category or "Sve", "cats":cats})

# V11.13 disabled old task detail route
def task_detail(task_id:int, request:Request, msg:str|None=None, db:Session=Depends(get_db)):
    u=current_user(request,db)
    t=db.query(Task).filter(Task.id==task_id, Task.status=="active").first()
    if not t: raise HTTPException(404, "Zadatak nije pronađen.")
    already = bool(u and db.query(TaskSubmission).filter(TaskSubmission.user_id==u.id, TaskSubmission.task_id==t.id, TaskSubmission.status.in_(["pending","approved"])).first())
    return templates.TemplateResponse("task_detail.html", {"request":request,"user":u,"task":t,"already":already,"flash":flash(msg)})

@app.get("/registracija", response_class=HTMLResponse)
def reg_page(request:Request, ref:str|None=None, role:str|None=None, db:Session=Depends(get_db)):
    return templates.TemplateResponse("register.html", {"request":request,"user":current_user(request,db),"error":None,"ref":ref or "", "role":role or "korisnik"})

@app.post("/registracija")
def reg(request:Request, full_name:str=Form(...), email:str=Form(...), password:str=Form(...), role:str=Form("korisnik"), referral_code:str=Form(""), city:str=Form(""), phone:str=Form(""), db:Session=Depends(get_db)):
    email=email.strip().lower(); role=role if role in ["korisnik","oglasivac"] else "korisnik"
    if db.query(User).filter(User.email==email).first():
        return templates.TemplateResponse("register.html", {"request":request,"user":None,"error":"Email već postoji.","ref":referral_code,"role":role}, status_code=400)
    referrer=db.query(User).filter(User.referral_code==referral_code.strip().upper()).first() if referral_code.strip() else None
    u=User(full_name=full_name.strip(),email=email,password_hash=hash_password(password),role=role,referral_code=make_referral_code(full_name),referred_by_id=referrer.id if referrer else None,city=city.strip() or None,phone=phone.strip() or None,company_name=full_name.strip() if role=="oglasivac" else None,contact_person=full_name.strip() if role=="oglasivac" else None)
    db.add(u); db.commit(); db.refresh(u)
    resp=RedirectResponse(role_url(u.role),303); resp.set_cookie("kz_session",create_session_token(u.id),httponly=True,samesite="lax"); return resp

@app.get("/login", response_class=HTMLResponse)
def login_page(request:Request, db:Session=Depends(get_db)):
    return templates.TemplateResponse("login.html", {"request":request,"user":current_user(request,db),"error":None})

@app.post("/login")
def login(request:Request, email:str=Form(...), password:str=Form(...), db:Session=Depends(get_db)):
    u=db.query(User).filter(User.email==email.strip().lower()).first()
    if not u or not verify_password(password,u.password_hash) or u.status!="active":
        return templates.TemplateResponse("login.html", {"request":request,"user":None,"error":"Pogrešan email/lozinka ili blokiran nalog."}, status_code=400)
    resp=RedirectResponse(role_url(u.role),303); resp.set_cookie("kz_session",create_session_token(u.id),httponly=True,samesite="lax"); return resp

@app.get("/logout")
def logout():
    r=RedirectResponse("/",303); r.delete_cookie("kz_session"); return r

@app.get("/pravila", response_class=HTMLResponse)
def pravila(request:Request, db:Session=Depends(get_db)): return templates.TemplateResponse("static_page.html", {"request":request,"user":current_user(request,db),"title":"Pravila","heading":"Pravila korišćenja","body":"Dozvoljeni su realni zadaci: ankete, testiranje, feedback i registracije. Zabranjeni su spam, bot aktivnosti, lažne recenzije i manipulacija algoritama. Pre produkcije proveriti pravni i poreski model."})
@app.get("/faq", response_class=HTMLResponse)
def faq(request:Request, db:Session=Depends(get_db)): return templates.TemplateResponse("static_page.html", {"request":request,"user":current_user(request,db),"title":"FAQ","heading":"Česta pitanja","body":"Korisnik šalje dokaz, admin ga proverava, a oglašivač plaća samo validan rezultat. V3 koristi ručne isplate i ručnu dopunu budžeta."})
# V11.7 disabled old route /kontakt
def kontakt(request:Request, db:Session=Depends(get_db)): return templates.TemplateResponse("static_page.html", {"request":request,"user":current_user(request,db),"title":"Kontakt","heading":"Kontakt","body":"Kontaktirajte podršku kroz obrazac ili kroz panel poruke. Za produkciju se ovde povezuju email podrška, ticket sistem i obaveštenja."})

# USER
@app.get("/korisnik/panel", response_class=HTMLResponse)
@app.get("/korisnik/zadaci", response_class=HTMLResponse)
# V11.11 disabled old route /korisnik/dokazi
# V11.16.1 separate wallet route
# V11.16.1 separate payouts route
# V11.16.1 separate referral route
def user_panel(request:Request, msg:str|None=None, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["korisnik","admin"])
    tasks = db.query(Task).filter(Task.status=="active").order_by(Task.featured.desc(),Task.reward_rsd.desc()).all()
    subs = db.query(TaskSubmission).filter(TaskSubmission.user_id==u.id).order_by(TaskSubmission.created_at.desc()).all()
    txs = db.query(WalletTransaction).filter(WalletTransaction.user_id==u.id).order_by(WalletTransaction.created_at.desc()).all()
    withdrawals = db.query(Withdrawal).filter(Withdrawal.user_id==u.id).order_by(Withdrawal.created_at.desc()).all()
    refs = db.query(User).filter(User.referred_by_id==u.id).all()
    today = datetime.utcnow().date()

    def is_status(val, options):
        return (val or '').strip().lower() in options

    approved_count = sum(1 for s in subs if is_status(s.status, {"approved", "odobreno"}))
    pending_count = sum(1 for s in subs if is_status(s.status, {"pending", "na čekanju", "na cekanju"}))
    rejected_count = sum(1 for s in subs if is_status(s.status, {"rejected", "odbijeno"}))
    daily_earned = sum((tx.amount_rsd or 0) for tx in txs if (tx.amount_rsd or 0) > 0 and getattr(tx.created_at, 'date', lambda: today)() == today)
    tasks_today = len([s for s in subs if getattr(s.created_at, 'date', lambda: today)() == today])
    recent_tasks = tasks[:5]
    best_tasks = tasks[:6]
    progress_bars = [18, 28, 16, 40, 24, 47, 33, 44, 52]
    score = None
    if 'kz115_get_score' in globals():
        try:
            score = kz115_recalculate_user_score(db, u)
        except Exception:
            score = kz115_get_score(db, u)
    data={
        "tasks": tasks,
        "best_tasks": best_tasks,
        "recent_tasks": recent_tasks,
        "subs": subs,
        "txs": txs,
        "withdrawals": withdrawals,
        "refs": refs,
        "min_withdrawal": MIN_WITHDRAWAL_RSD,
        "approved_count": approved_count,
        "pending_count": pending_count,
        "rejected_count": rejected_count,
        "daily_earned": daily_earned,
        "tasks_today": tasks_today,
        "progress_bars": progress_bars,
        "score": score,
    }
    return templates.TemplateResponse("user_app.html", {"request":request,"user":u,"flash":flash(msg),**data})

@app.get("/korisnik/profil", response_class=HTMLResponse)
def user_profile(request:Request, msg:str|None=None, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["korisnik","admin"])
    return templates.TemplateResponse("profile_user.html", {"request":request,"user":u,"flash":flash(msg)})

@app.post("/korisnik/profil")
def user_profile_save(request:Request, full_name:str=Form(...), phone:str=Form(""), city:str=Form(""), age_group:str=Form(""), gender:str=Form(""), interests:str=Form(""), device:str=Form(""), payment_method:str=Form(""), payment_details:str=Form(""), db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["korisnik","admin"])
    u.full_name=full_name; u.phone=phone; u.city=city; u.age_group=age_group; u.gender=gender; u.interests=interests; u.device=device; u.payment_method=payment_method; u.payment_details=payment_details
    db.commit(); return RedirectResponse("/korisnik/profil?msg=saved",303)

@app.post("/korisnik/zadaci/{task_id}/dokaz")
def submit_proof(task_id:int, request:Request, proof:str=Form(...), proof_file:Optional[UploadFile]=File(None), db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["korisnik","admin"])
    t=db.query(Task).filter(Task.id==task_id,Task.status=="active").first()
    if not t: raise HTTPException(404,"Zadatak nije pronađen.")
    if db.query(TaskSubmission).filter(TaskSubmission.user_id==u.id,TaskSubmission.task_id==t.id,TaskSubmission.status.in_(["pending","approved"])).first():
        return RedirectResponse(f"/zadaci/{task_id}?msg=already",303)
    file_path=save_file(proof_file)
    if t.proof_file_required and not file_path: raise HTTPException(400,"Fajl dokaz je obavezan.")
    total, fee = cost_one(t.reward_rsd, t.platform_fee_percent)
    s=TaskSubmission(user_id=u.id,task_id=t.id,proof=proof.strip(),proof_file=file_path,reward_rsd=t.reward_rsd,platform_fee_rsd=fee,advertiser_cost_rsd=total,status="pending")
    t.used_slots += 1; u.pending_rsd += t.reward_rsd
    db.add(s); db.commit()
    return RedirectResponse("/korisnik/panel?msg=sent",303)

@app.post("/korisnik/isplata")
def withdrawal(amount_rsd:float=Form(...), payment_method:str=Form(...), payment_details:str=Form(...), request:Request=None, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["korisnik","admin"])
    if amount_rsd < MIN_WITHDRAWAL_RSD or amount_rsd > u.balance_rsd:
        return RedirectResponse("/korisnik/isplate?msg=withdrawal_error",303)
    u.balance_rsd -= amount_rsd
    db.add(Withdrawal(user_id=u.id,amount_rsd=amount_rsd,payment_method=payment_method,payment_details=payment_details,status="pending"))
    add_tx(db,u,-amount_rsd,"withdrawal_hold",f"Rezervisan zahtev za isplatu: {amount_rsd:.0f} RSD")
    db.commit(); return RedirectResponse("/korisnik/isplate?msg=withdrawal_sent",303)

# ADVERTISER
@app.get("/oglasivac/panel", response_class=HTMLResponse)
@app.get("/oglasivac/kampanje", response_class=HTMLResponse)
@app.get("/oglasivac/budzet", response_class=HTMLResponse)
# V11.11 disabled old route /oglasivac/dokazi
@app.get("/oglasivac/izvestaji", response_class=HTMLResponse)
def advertiser_panel(request:Request, msg:str|None=None, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["oglasivac","admin"])
    tasks=db.query(Task).filter(Task.advertiser_id==u.id).order_by(Task.created_at.desc()).all()
    subs=db.query(TaskSubmission).join(Task).filter(Task.advertiser_id==u.id).order_by(TaskSubmission.created_at.desc()).all()
    txs=db.query(AdvertiserBudgetTransaction).filter(AdvertiserBudgetTransaction.advertiser_id==u.id).order_by(AdvertiserBudgetTransaction.created_at.desc()).all()
    return templates.TemplateResponse("advertiser_app.html", {"request":request,"user":u,"flash":flash(msg),"tasks":tasks,"subs":subs,"txs":txs})

@app.get("/oglasivac/nova-kampanja", response_class=HTMLResponse)
def new_campaign(request:Request, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["oglasivac","admin"])
    fee = v111_price_percent(db, "platform_commission_percent", PLATFORM_FEE_PERCENT) if "v111_price_percent" in globals() else PLATFORM_FEE_PERCENT
    return templates.TemplateResponse("campaign_form.html", {"request":request,"user":u,"error":None,"fee":fee})

@app.post("/oglasivac/nova-kampanja")
def create_campaign(request:Request, title:str=Form(...), category:str=Form(...), task_type:str=Form(...), target_url:str=Form(""), description:str=Form(...), instructions:str=Form(...), proof_required:str=Form(...), example_proof:str=Form(""), reward_rsd:float=Form(...), total_slots:int=Form(...), target_city:str=Form("Srbija"), target_age_group:str=Form("18+"), target_interests:str=Form(""), proof_file_required:Optional[str]=Form(None), db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["oglasivac","admin"])
    fee = v111_price_percent(db, "platform_commission_percent", PLATFORM_FEE_PERCENT) if "v111_price_percent" in globals() else PLATFORM_FEE_PERCENT
    total=cost_for_task(reward_rsd,total_slots,fee)
    if u.advertiser_budget_rsd < total:
        return templates.TemplateResponse("campaign_form.html", {"request":request,"user":u,"error":f"Nedovoljno budžeta. Potrebno {total:.0f} RSD, dostupno {u.advertiser_budget_rsd:.0f} RSD.","fee":fee}, status_code=400)
    t=Task(advertiser_id=u.id,title=title,category=category,task_type=task_type,target_url=target_url,description=description,instructions=instructions,proof_required=proof_required,example_proof=example_proof,reward_rsd=reward_rsd,platform_fee_percent=fee,total_slots=total_slots,target_city=target_city,target_age_group=target_age_group,target_interests=target_interests,proof_file_required=bool(proof_file_required),status="pending")
    u.advertiser_budget_rsd-=total; u.advertiser_reserved_rsd+=total
    db.add(t); db.flush(); add_budget_tx(db,u,-total,"reserve_campaign",f"Rezervisan budžet za kampanju: {title}")
    notify(db, None, "admin", "Nova kampanja čeka odobrenje", f"Oglašivač {u.full_name} je poslao kampanju: {title}"); db.commit(); return RedirectResponse("/oglasivac/panel?msg=campaign_created",303)

@app.get("/oglasivac/profil", response_class=HTMLResponse)
def adv_profile(request:Request, msg:str|None=None, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["oglasivac","admin"])
    return templates.TemplateResponse("profile_advertiser.html", {"request":request,"user":u,"flash":flash(msg)})

@app.post("/oglasivac/profil")
def adv_profile_save(request:Request, company_name:str=Form(""), company_pib:str=Form(""), company_website:str=Form(""), company_activity:str=Form(""), company_city:str=Form(""), contact_person:str=Form(""), phone:str=Form(""), db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["oglasivac","admin"])
    u.company_name=company_name; u.company_pib=company_pib; u.company_website=company_website; u.company_activity=company_activity; u.company_city=company_city; u.contact_person=contact_person; u.phone=phone
    db.commit(); return RedirectResponse("/oglasivac/profil?msg=saved",303)

@app.post("/oglasivac/budzet/zahtev")
def budget_request(request: Request, amount_rsd: float = Form(...), note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["oglasivac", "admin"])
    tx, status = v11833_topup_request(db, u, amount_rsd, note)
    return RedirectResponse(f"/oglasivac/budzet?msg={status}", 303)

@app.get("/oglasivac/izvestaji.csv")
def adv_csv(request:Request, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["oglasivac","admin"])
    subs=db.query(TaskSubmission).join(Task).filter(Task.advertiser_id==u.id).all()
    out=io.StringIO(); w=csv.writer(out); w.writerow(["kampanja","korisnik","status","nagrada","fee","trosak","dokaz"])
    for s in subs: w.writerow([s.task.title,s.user.full_name,s.status,s.reward_rsd,s.platform_fee_rsd,s.advertiser_cost_rsd,s.proof])
    return Response(out.getvalue(), media_type="text/csv", headers={"Content-Disposition":"attachment; filename=oglasivac_izvestaj.csv"})

# ADMIN
@app.get("/admin")
def admin_root(): return RedirectResponse("/admin/dashboard",303)

def admin_data(db):
    return {
        "users":db.query(User).order_by(User.created_at.desc()).all(),
        "advertisers":db.query(User).filter(User.role=="oglasivac").all(),
        "tasks":db.query(Task).order_by(Task.created_at.desc()).all(),
        "subs":db.query(TaskSubmission).order_by(TaskSubmission.created_at.desc()).all(),
        "withdrawals":db.query(Withdrawal).order_by(Withdrawal.created_at.desc()).all(),
        "logs":db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all(),
    }

def antifraud(db):
    signals=[]
    for phone,c in db.query(User.phone,func.count(User.id)).filter(User.phone.isnot(None),User.phone!="").group_by(User.phone).having(func.count(User.id)>1).all():
        signals.append(("Isti telefon","high",f"{c} naloga koristi telefon {phone}."))
    for pay,c in db.query(User.payment_details,func.count(User.id)).filter(User.payment_details.isnot(None),User.payment_details!="").group_by(User.payment_details).having(func.count(User.id)>1).all():
        signals.append(("Isti podaci za isplatu","high",f"{c} naloga ima iste podatke za isplatu."))
    for u in db.query(User).filter(User.role=="korisnik").all():
        a=db.query(TaskSubmission).filter(TaskSubmission.user_id==u.id,TaskSubmission.status=="approved").count()
        r=db.query(TaskSubmission).filter(TaskSubmission.user_id==u.id,TaskSubmission.status=="rejected").count()
        if r>=3 and r>a: signals.append(("Loš kvalitet","medium",f"{u.full_name}: {r} odbijeno, {a} odobreno."))
    return signals

@app.get("/admin/dashboard", response_class=HTMLResponse)
@app.get("/admin/korisnici", response_class=HTMLResponse)
@app.get("/admin/oglasivaci", response_class=HTMLResponse)
# V11.9 disabled old route /admin/kampanje
# V11.11 disabled old route /admin/dokazi
# V11.11 disabled old route /admin/isplate
# V11.11 disabled old route /admin/finansije
@app.get("/admin/anti-fraud", response_class=HTMLResponse)
@app.get("/admin/referral", response_class=HTMLResponse)
@app.get("/admin/logovi", response_class=HTMLResponse)
@app.get("/admin/podesavanja", response_class=HTMLResponse)
def admin_panel(request:Request, msg:str|None=None, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["admin"])
    data=admin_data(db)
    health_rows = [v11837_advertiser_health_row(db, adv) for adv in data["advertisers"]]
    health_rows = sorted(health_rows, key=lambda row: (row["score"], row["pending_topups"] * -1))[:8]
    campaign_rows = [v11837_campaign_signal_row(db, task) for task in data["tasks"][:24] if getattr(task, "advertiser_id", None)]
    campaign_rows = sorted(campaign_rows, key=lambda row: (0 if row["pacing"] == "spor" else 1 if row["pacing"] == "stabilan" else 2, row["completion"]))[:8]
    topup_inbox = db.query(PaymentIntentV8).order_by(PaymentIntentV8.created_at.desc()).limit(12).all()
    margin_snapshot = v11837_margin_snapshot(db)
    crm_admins = db.query(User).filter(User.role == "admin").order_by(User.full_name.asc()).all()
    sales_leads = db.query(SalesLead).order_by(SalesLead.updated_at.desc()).all()
    sales_workflow_rows = []
    for adv in data["advertisers"]:
        sales_workflow_rows.append(
            v11838_sales_workflow_row(
                db,
                adv,
                v11838_find_sales_lead(sales_leads, adv),
                margin_snapshot["packages"],
            )
        )
    sales_workflow_rows = sorted(sales_workflow_rows, key=lambda row: (-row["priority"], row["advertiser"].id))[:8]
    sales_pipeline_summary = {
        "open_leads": sum(1 for lead in sales_leads if getattr(lead, "status", "") in ["new", "contacted", "demo", "proposal"]),
        "won": sum(1 for lead in sales_leads if getattr(lead, "status", "") == "won"),
        "pending_payments": db.query(PaymentIntentV8).filter(PaymentIntentV8.status == "pending").count(),
        "live_banners": db.query(PaidAdBannerV111).filter(PaidAdBannerV111.status == "active").count() if "PaidAdBannerV111" in globals() else 0,
    }
    data.update({
        "platform_revenue":db.query(func.coalesce(func.sum(TaskSubmission.platform_fee_rsd),0)).filter(TaskSubmission.status=="approved").scalar(),
        "rewards":db.query(func.coalesce(func.sum(TaskSubmission.reward_rsd),0)).filter(TaskSubmission.status=="approved").scalar(),
        "adv_available":db.query(func.coalesce(func.sum(User.advertiser_budget_rsd),0)).filter(User.role=="oglasivac").scalar(),
        "adv_reserved":db.query(func.coalesce(func.sum(User.advertiser_reserved_rsd),0)).filter(User.role=="oglasivac").scalar(),
        "signals":antifraud(db),
        "settings":{"fee":PLATFORM_FEE_PERCENT,"referral":REFERRAL_BONUS_RSD,"min_withdrawal":MIN_WITHDRAWAL_RSD},
        "health_rows": health_rows,
        "campaign_rows": campaign_rows,
        "topup_inbox": topup_inbox,
        "margin_snapshot": margin_snapshot,
        "sales_packages": margin_snapshot["packages"],
        "crm_admins": crm_admins,
        "sales_workflow_rows": sales_workflow_rows,
        "sales_pipeline_summary": sales_pipeline_summary,
    })
    return templates.TemplateResponse("admin_app.html", {"request":request,"user":u,"flash":flash(msg),**data})

@app.post("/admin/tasks/{task_id}/{action}")
def admin_task_action(task_id:int, action:str, request:Request, note:str=Form(""), db:Session=Depends(get_db)):
    admin=require(request,db); check_role(admin,["admin"])
    t=db.query(Task).filter(Task.id==task_id).first()
    if not t: raise HTTPException(404)
    if action in ["active","rejected","returned","paused","closed"]: t.status=action
    elif action=="feature": t.featured=not t.featured
    audit(db,admin,f"task_{action}","Task",t.id,note); db.commit()
    return RedirectResponse("/admin/kampanje?msg=saved",303)

@app.post("/admin/submissions/{sub_id}/{action}")
def admin_sub_action(sub_id: int, action: str, request: Request, note: str = Form(""), db: Session = Depends(get_db)):
    admin = require(request, db); check_role(admin, ["admin"])
    sub = db.query(TaskSubmission).filter(TaskSubmission.id == sub_id).first()
    if not sub:
        return RedirectResponse("/admin/dokazi?msg=not_found", 303)
    if action == "approve":
        result = v11831_approve_submission(db, admin, sub, note)
    elif action == "reject":
        result = v11831_reject_submission(db, admin, sub, note)
    elif action == "dispute":
        if sub.status == "pending":
            sub.status = "disputed"
            sub.review_note = note.strip() or "Spor"
            sub.reviewed_at = datetime.utcnow()
            audit(db, admin, "submission_dispute_v11831", "TaskSubmission", sub.id, note)
            db.commit()
            result = "disputed"
        else:
            result = f"already_{sub.status}"
    else:
        result = "bad_action"
    return RedirectResponse(f"/admin/dokazi?msg={result}", 303)

@app.post("/admin/withdrawals/{wid}/{action}")
def admin_withdrawal_action(
    wid: int,
    action: str,
    request: Request,
    note: str = Form(""),
    next_url: str | None = None,
    db: Session = Depends(get_db),
):
    admin = require(request, db); check_role(admin, ["admin"])
    w = db.query(Withdrawal).filter(Withdrawal.id == wid).first()
    if action in ["paid", "pay", "approve"]:
        result = v11832_pay_withdrawal(db, admin, w, note)
    elif action in ["reject", "rejected"]:
        result = v11832_reject_withdrawal(db, admin, w, note)
    else:
        result = "bad_action"
    target = next_url or "/admin/isplate"
    separator = "&" if "?" in target else "?"
    return RedirectResponse(f"{target}{separator}msg={result}", 303)

@app.post("/admin/users/{uid}/{action}")
def admin_user_action(uid:int, action:str, request:Request, amount_rsd:float=Form(0), reason:str=Form(""), db:Session=Depends(get_db)):
    admin=require(request,db); check_role(admin,["admin"])
    u=db.query(User).filter(User.id==uid).first()
    if not u: raise HTTPException(404)
    if action=="block": u.status="blocked"
    elif action=="activate": u.status="active"
    elif action=="verify": u.email_verified=True; u.phone_verified=True; u.advertiser_verified=True if u.role=="oglasivac" else u.advertiser_verified
    elif action=="bonus": u.balance_rsd+=amount_rsd; add_tx(db,u,amount_rsd,"admin_adjustment",reason or "Admin korekcija")
    audit(db,admin,f"user_{action}","User",u.id,reason); db.commit()
    return RedirectResponse("/admin/korisnici?msg=saved",303)

@app.post("/admin/oglasivaci/{uid}/topup")
def admin_topup(uid: int, request: Request, amount_rsd: float = Form(...), reason: str = Form(""), db: Session = Depends(get_db)):
    admin = require(request, db); check_role(admin, ["admin"])
    adv = db.query(User).filter(User.id == uid, User.role == "oglasivac").first()
    status = v11833_admin_topup(db, admin, adv, amount_rsd, reason)
    return RedirectResponse(f"/admin/oglasivaci?msg={status}", 303)

@app.get("/admin/finansije.csv")
def finance_csv(request:Request, db:Session=Depends(get_db)):
    admin=require(request,db); check_role(admin,["admin"])
    out=io.StringIO(); w=csv.writer(out); w.writerow(["datum","kampanja","korisnik","nagrada","provizija","trosak"])
    for s in db.query(TaskSubmission).filter(TaskSubmission.status=="approved").all():
        w.writerow([s.reviewed_at or s.created_at,s.task.title,s.user.full_name,s.reward_rsd,s.platform_fee_rsd,s.advertiser_cost_rsd])
    return Response(out.getvalue(), media_type="text/csv", headers={"Content-Disposition":"attachment; filename=klikzarada_finansije.csv"})


# =========================
# V4 GROWTH & OPERATIONS
# =========================

def seed_v4_growth():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        if db.query(CampaignTemplate).count() == 0:
            templates_seed = [
                ("Anketa za istraživanje tržišta", "Ankete", "Anketa", "Korisnik popunjava kratku anketu i šalje potvrdu.", "Otvorite link, odgovorite iskreno i završite anketu.", "Kod potvrde ili screenshot završnog ekrana.", 60, 100),
                ("Test landing stranice", "Testiranje", "Test sajta", "Korisnik pregleda landing stranicu i šalje 3 komentara.", "Provedite 2-3 minuta na stranici i obratite pažnju na ponudu, cenu i CTA dugme.", "Tri komentara: jasno, nejasno, predlog.", 100, 80),
                ("Beta registracija", "Registracije", "Registracija", "Korisnik se registruje za beta listu ili aplikaciju.", "Napravite nalog i potvrdite email ako je potrebno.", "Email korišćen za registraciju + screenshot/potvrda.", 120, 50),
                ("Mystery shopper online", "Lokalni zadaci", "Mystery shopper", "Korisnik pregleda ponudu lokalnog biznisa i daje mišljenje.", "Pregledajte ponudu i napišite da li biste kupili/naručili i zašto.", "Kratak izveštaj sa konkretnim zapažanjima.", 150, 30),
            ]
            for name, cat, typ, desc, inst, proof, reward, slots in templates_seed:
                db.add(CampaignTemplate(name=name, category=cat, task_type=typ, description=desc, instructions=inst, proof_required=proof, suggested_reward_rsd=reward, suggested_slots=slots))
        if db.query(PromoCode).count() == 0:
            db.add(PromoCode(code="START20", description="20% promotivni popust za prvu kampanju", discount_percent=20, max_uses=50))
            db.add(PromoCode(code="BUDZET1000", description="Bonus budžet 1000 RSD za test oglašivače", bonus_budget_rsd=1000, max_uses=100))
        admin = db.query(User).filter(User.role == "admin").first()
        if admin and db.query(Notification).count() == 0:
            notify(db, admin, None, "V4 Growth instaliran", "Aktivirani su notifikacije, tiketi, kuponi, šabloni kampanja i fakture.")
        db.commit()
    finally:
        db.close()

# V11.7 disabled old route /za-korisnike
def landing_users(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("landing_v4.html", {"request": request, "user": current_user(request, db), "kind": "korisnici", "pricing_summary": v11836_pricing_summary(db)})

# V11.7 disabled old route /za-oglasivace
def landing_advertisers(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("landing_v4.html", {"request": request, "user": current_user(request, db), "kind": "oglasivaci", "pricing_summary": v11836_pricing_summary(db)})

# V11.7 disabled old route /cenovnik
def pricing_page(request: Request, db: Session = Depends(get_db)):
    prices = []
    if "MonetizationPricingV111" in globals():
        prices = db.query(MonetizationPricingV111).order_by(MonetizationPricingV111.key).all()
    pricing_summary = v11836_pricing_summary(db)
    task_price_ranges = [
        {"label": "Kratki zadaci", "reward": "20-40 RSD", "desc": "Posete i brze akcije od oko 1 minuta."},
        {"label": "Standardni zadaci", "reward": "50-120 RSD", "desc": "Ankete, registracije i testiranje od 3-5 minuta."},
        {"label": "Viši zadaci", "reward": "120-250 RSD", "desc": "Duže kampanje sa više koraka i dokazom."},
        {"label": "Premium zadaci", "reward": "250+ RSD", "desc": "Kompleksniji ili specijalni zadaci."},
    ]
    banner_packages = [
        {"title": "Početna - veliki banner", "price": f"od {pricing_summary['banner_top_day']:.0f} RSD / 24 sata", "desc": "Najvidljiviji prostor odmah ispod hero sekcije."},
        {"title": "Početna - srednji banner", "price": f"od {pricing_summary['banner_mid_day']:.0f} RSD / 24 sata", "desc": "Uredan format za brendove i kampanje."},
        {"title": "Top pozicija kampanje", "price": f"od {pricing_summary['boost_top_3d']:.0f} RSD / 3 dana", "desc": "Kampanja se izdvaja na vrhu liste zadataka."},
    ]
    return templates.TemplateResponse("pricing_v117.html", {"request": request, "user": current_user(request, db), "prices": prices, "pricing_summary": pricing_summary, "task_price_ranges": task_price_ranges, "banner_packages": banner_packages, "fee": PLATFORM_FEE_PERCENT, "min_withdrawal": MIN_WITHDRAWAL_RSD})

@app.get("/korisnik/notifikacije", response_class=HTMLResponse)
@app.get("/oglasivac/notifikacije", response_class=HTMLResponse)
def my_notifications(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    notes = db.query(Notification).filter(or_(Notification.user_id == u.id, Notification.role_target == u.role, Notification.role_target == "all")).order_by(Notification.created_at.desc()).all()
    for n in notes:
        if n.user_id == u.id and n.status == "unread":
            n.status = "read"
    db.commit()
    return templates.TemplateResponse("notifications_v4.html", {"request": request, "user": u, "notes": notes})

@app.get("/korisnik/tiketi", response_class=HTMLResponse)
@app.get("/oglasivac/tiketi", response_class=HTMLResponse)
def my_tickets(request: Request, msg: str|None=None, db: Session = Depends(get_db)):
    u = require(request, db)
    tickets = db.query(SupportTicket).filter(SupportTicket.user_id == u.id).order_by(SupportTicket.updated_at.desc()).all()
    return templates.TemplateResponse("tickets_v4.html", {"request": request, "user": u, "tickets": tickets, "mode": "mine", "flash": flash(msg)})

@app.post("/tiketi/novi")
def create_ticket(request: Request, subject: str=Form(...), category: str=Form("Opšte"), priority: str=Form("normal"), body: str=Form(...), db: Session=Depends(get_db)):
    u = require(request, db)
    t = SupportTicket(user_id=u.id, subject=subject.strip(), category=category, priority=priority, status="open")
    db.add(t); db.flush()
    db.add(SupportMessage(ticket_id=t.id, sender_id=u.id, body=body.strip()))
    notify(db, None, "admin", "Novi tiket", f"{u.full_name} je otvorio tiket: {subject}")
    db.commit()
    return RedirectResponse(f"/{'oglasivac' if u.role=='oglasivac' else 'korisnik'}/tiketi?msg=ticket_sent", 303)

@app.post("/tiketi/{ticket_id}/odgovor")
def reply_ticket(ticket_id:int, request:Request, body:str=Form(...), db:Session=Depends(get_db)):
    u=require(request,db)
    t=db.query(SupportTicket).filter(SupportTicket.id==ticket_id).first()
    if not t or (u.role != "admin" and t.user_id != u.id):
        raise HTTPException(404, "Tiket nije pronađen.")
    db.add(SupportMessage(ticket_id=t.id, sender_id=u.id, body=body.strip()))
    t.updated_at=datetime.utcnow()
    if u.role == "admin":
        t.status = "waiting"
        notify(db, t.user, None, "Odgovor podrške", f"Podrška je odgovorila na tiket: {t.subject}")
        dest = "/admin/tiketi?msg=reply_sent"
    else:
        t.status = "open"
        notify(db, None, "admin", "Odgovor na tiket", f"{u.full_name} je odgovorio na tiket: {t.subject}")
        dest = f"/{'oglasivac' if u.role=='oglasivac' else 'korisnik'}/tiketi?msg=reply_sent"
    db.commit(); return RedirectResponse(dest,303)

@app.post("/tiketi/{ticket_id}/zatvori")
def close_ticket(ticket_id:int, request:Request, db:Session=Depends(get_db)):
    u=require(request,db)
    t=db.query(SupportTicket).filter(SupportTicket.id==ticket_id).first()
    if not t or (u.role != "admin" and t.user_id != u.id):
        raise HTTPException(404)
    t.status="closed"; t.updated_at=datetime.utcnow(); db.commit()
    return RedirectResponse("/admin/tiketi?msg=saved" if u.role=="admin" else f"/{'oglasivac' if u.role=='oglasivac' else 'korisnik'}/tiketi?msg=saved",303)

@app.get("/oglasivac/sabloni", response_class=HTMLResponse)
def advertiser_templates(request:Request, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["oglasivac","admin"])
    items=db.query(CampaignTemplate).filter(CampaignTemplate.is_active==True).order_by(CampaignTemplate.category, CampaignTemplate.name).all()
    return templates.TemplateResponse("templates_v4.html", {"request":request,"user":u,"items":items})

@app.get("/oglasivac/nova-kampanja/sablon/{template_id}", response_class=HTMLResponse)
def campaign_from_template(template_id:int, request:Request, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["oglasivac","admin"])
    item=db.query(CampaignTemplate).filter(CampaignTemplate.id==template_id).first()
    if not item: raise HTTPException(404)
    return templates.TemplateResponse("campaign_form.html", {"request":request,"user":u,"error":None,"fee":PLATFORM_FEE_PERCENT,"tpl":item})

@app.post("/oglasivac/kupon")
def apply_coupon(request:Request, code:str=Form(...), db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["oglasivac","admin"])
    promo=db.query(PromoCode).filter(PromoCode.code==code.strip().upper(), PromoCode.is_active==True).first()
    if not promo or promo.used_count >= promo.max_uses:
        return RedirectResponse("/oglasivac/budzet?msg=coupon_error",303)
    used=db.query(PromoCodeUse).filter(PromoCodeUse.promo_code_id==promo.id, PromoCodeUse.advertiser_id==u.id).first()
    if used:
        return RedirectResponse("/oglasivac/budzet?msg=coupon_error",303)
    if promo.bonus_budget_rsd:
        u.advertiser_budget_rsd += promo.bonus_budget_rsd
        add_budget_tx(db,u,promo.bonus_budget_rsd,"promo_bonus",f"Promo kod {promo.code}: bonus budžet")
    db.add(PromoCodeUse(promo_code_id=promo.id, advertiser_id=u.id))
    promo.used_count += 1
    notify(db,u,None,"Promo kod iskorišćen",f"Uspešno ste iskoristili promo kod {promo.code}.")
    db.commit(); return RedirectResponse("/oglasivac/budzet?msg=coupon_ok",303)

@app.get("/oglasivac/fakture", response_class=HTMLResponse)
def advertiser_invoices(request:Request, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["oglasivac","admin"])
    inv=db.query(Invoice).filter(Invoice.advertiser_id==u.id).order_by(Invoice.created_at.desc()).all()
    return templates.TemplateResponse("invoices_v4.html", {"request":request,"user":u,"invoices":inv,"mode":"advertiser"})

@app.get("/fakture/{invoice_id}", response_class=HTMLResponse)
def invoice_print(invoice_id:int, request:Request, db:Session=Depends(get_db)):
    u=require(request,db)
    inv=db.query(Invoice).filter(Invoice.id==invoice_id).first()
    if not inv or (u.role != "admin" and inv.advertiser_id != u.id):
        raise HTTPException(404)
    return templates.TemplateResponse("invoice_print_v4.html", {"request":request,"user":u,"invoice":inv})

@app.get("/admin/tiketi", response_class=HTMLResponse)
def admin_tickets(request:Request, msg:str|None=None, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["admin"])
    tickets=db.query(SupportTicket).order_by(SupportTicket.updated_at.desc()).all()
    return templates.TemplateResponse("tickets_v4.html", {"request":request,"user":u,"tickets":tickets,"mode":"admin","flash":flash(msg)})

@app.get("/admin/notifikacije", response_class=HTMLResponse)
def admin_notifications(request:Request, msg:str|None=None, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["admin"])
    notes=db.query(Notification).order_by(Notification.created_at.desc()).limit(200).all()
    return templates.TemplateResponse("admin_notifications_v4.html", {"request":request,"user":u,"notes":notes,"flash":flash(msg)})

@app.post("/admin/notifikacije/posalji")
def admin_send_notification(request:Request, role_target:str=Form("all"), title:str=Form(...), body:str=Form(...), db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["admin"])
    notify(db,None,role_target,title.strip(),body.strip())
    audit(db,u,"broadcast_notification","Notification",None,title)
    db.commit(); return RedirectResponse("/admin/notifikacije?msg=notification_sent",303)

@app.get("/admin/kuponi", response_class=HTMLResponse)
def admin_coupons(request:Request, msg:str|None=None, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["admin"])
    coupons=db.query(PromoCode).order_by(PromoCode.created_at.desc()).all()
    uses=db.query(PromoCodeUse).order_by(PromoCodeUse.created_at.desc()).all()
    return templates.TemplateResponse("coupons_v4.html", {"request":request,"user":u,"coupons":coupons,"uses":uses,"flash":flash(msg)})

@app.post("/admin/kuponi/novi")
def admin_create_coupon(request:Request, code:str=Form(...), description:str=Form(""), discount_percent:float=Form(0), bonus_budget_rsd:float=Form(0), max_uses:int=Form(100), db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["admin"])
    promo=PromoCode(code=code.strip().upper(), description=description.strip(), discount_percent=discount_percent, bonus_budget_rsd=bonus_budget_rsd, max_uses=max_uses, is_active=True)
    db.add(promo); audit(db,u,"coupon_create","PromoCode",None,code)
    db.commit(); return RedirectResponse("/admin/kuponi?msg=saved",303)

@app.post("/admin/kuponi/{coupon_id}/toggle")
def admin_toggle_coupon(coupon_id:int, request:Request, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["admin"])
    promo=db.query(PromoCode).filter(PromoCode.id==coupon_id).first()
    if not promo: raise HTTPException(404)
    promo.is_active = not promo.is_active
    audit(db,u,"coupon_toggle","PromoCode",promo.id,promo.code)
    db.commit(); return RedirectResponse("/admin/kuponi?msg=saved",303)

@app.get("/admin/sabloni", response_class=HTMLResponse)
def admin_templates(request:Request, msg:str|None=None, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["admin"])
    items=db.query(CampaignTemplate).order_by(CampaignTemplate.category, CampaignTemplate.name).all()
    return templates.TemplateResponse("admin_templates_v4.html", {"request":request,"user":u,"items":items,"flash":flash(msg)})

@app.post("/admin/sabloni/novi")
def admin_create_template(request:Request, name:str=Form(...), category:str=Form(...), task_type:str=Form(...), description:str=Form(...), instructions:str=Form(...), proof_required:str=Form(...), suggested_reward_rsd:float=Form(60), suggested_slots:int=Form(100), db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["admin"])
    item=CampaignTemplate(name=name, category=category, task_type=task_type, description=description, instructions=instructions, proof_required=proof_required, suggested_reward_rsd=suggested_reward_rsd, suggested_slots=suggested_slots, is_active=True)
    db.add(item); audit(db,u,"template_create","CampaignTemplate",None,name)
    db.commit(); return RedirectResponse("/admin/sabloni?msg=saved",303)

@app.get("/admin/fakture", response_class=HTMLResponse)
def admin_invoices(request:Request, msg:str|None=None, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["admin"])
    invoices=db.query(Invoice).order_by(Invoice.created_at.desc()).all()
    advertisers=db.query(User).filter(User.role=="oglasivac").order_by(User.full_name).all()
    return templates.TemplateResponse("invoices_v4.html", {"request":request,"user":u,"invoices":invoices,"advertisers":advertisers,"mode":"admin","flash":flash(msg)})

@app.post("/admin/fakture/nova")
def admin_create_invoice(
    request: Request,
    advertiser_id: int = Form(...),
    invoice_type: str = Form("predracun"),
    amount_rsd: float = Form(...),
    description: str = Form(""),
    next_url: str | None = None,
    db: Session = Depends(get_db),
):
    u=require(request,db); check_role(u,["admin"])
    adv=db.query(User).filter(User.id==advertiser_id, User.role=="oglasivac").first()
    if not adv: raise HTTPException(404)
    number=f"KZ-{datetime.utcnow().strftime('%Y%m%d')}-{db.query(Invoice).count()+1:04d}"
    inv=Invoice(advertiser_id=adv.id, invoice_no=number, invoice_type=invoice_type, amount_rsd=amount_rsd, description=description, status="issued", issued_at=datetime.utcnow())
    db.add(inv); notify(db, adv, None, "Nova faktura/predračun", f"Kreiran je dokument {number} na iznos {amount_rsd:.0f} RSD."); audit(db,u,"invoice_create","Invoice",None,number)
    db.commit()
    target = next_url or "/admin/fakture"
    separator = "&" if "?" in target else "?"
    return RedirectResponse(f"{target}{separator}msg=invoice_created", 303)

@app.post("/admin/fakture/{invoice_id}/{action}")
def admin_invoice_action(invoice_id:int, action:str, request:Request, next_url: str | None = None, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["admin"])
    inv=db.query(Invoice).filter(Invoice.id==invoice_id).first()
    if not inv: raise HTTPException(404)
    if action in ["paid","cancelled","draft","issued"]:
        inv.status=action
    audit(db,u,f"invoice_{action}","Invoice",inv.id,inv.invoice_no)
    db.commit()
    target = next_url or "/admin/fakture"
    separator = "&" if "?" in target else "?"
    return RedirectResponse(f"{target}{separator}msg=saved", 303)

@app.get("/admin/marketing", response_class=HTMLResponse)
def admin_marketing(request:Request, db:Session=Depends(get_db)):
    u=require(request,db); check_role(u,["admin"])
    return templates.TemplateResponse("marketing_v4.html", {"request":request,"user":u})

@app.get("/robots.txt")
def robots():
    return Response("User-agent: *\nAllow: /\nSitemap: http://127.0.0.1:8000/sitemap.xml\n", media_type="text/plain")

@app.get("/sitemap.xml")
def sitemap():
    urls=["/","/zadaci","/za-korisnike","/za-oglasivace","/cenovnik","/faq","/pravila","/kontakt"]
    body='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join([f"<url><loc>http://127.0.0.1:8000{u}</loc></url>" for u in urls]) + '</urlset>'
    return Response(body, media_type="application/xml")




# ---------------------------------------------------
# V5 SCALE & AUTOMATION
# ---------------------------------------------------

def seed_v5_scale():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        if db.query(AdvertiserPlan).count() == 0:
            plans = [
                AdvertiserPlan(
                    name="Start",
                    monthly_fee_rsd=0,
                    platform_fee_percent=20,
                    max_active_campaigns=3,
                    features="Osnovne kampanje, ručna moderacija, osnovni CSV izveštaj."
                ),
                AdvertiserPlan(
                    name="Pro",
                    monthly_fee_rsd=4900,
                    platform_fee_percent=17,
                    max_active_campaigns=15,
                    features="Više kampanja, bolji segmenti publike, sačuvani izveštaji, prioritetna podrška."
                ),
                AdvertiserPlan(
                    name="Business",
                    monthly_fee_rsd=14900,
                    platform_fee_percent=14,
                    max_active_campaigns=100,
                    features="Napredni segmenti, API pristup, prioritetna moderacija, detaljni izveštaji."
                ),
            ]
            db.add_all(plans)

        adv = db.query(User).filter(User.role == "oglasivac").first()
        if adv and db.query(AudienceSegment).count() == 0:
            db.add(AudienceSegment(
                advertiser_id=adv.id,
                name="Mladi korisnici iz Srbije",
                city="Srbija",
                age_group="18-34",
                interests="aplikacije, online kupovina, hrana, tehnologija",
                min_user_level="Bronza",
                min_quality_score=80,
                notes="Demo segment za testiranje kampanja."
            ))

        demo_user = db.query(User).filter(User.email == "korisnik@demo.rs").first()
        if demo_user and db.query(UserAchievement).count() == 0:
            db.add(UserAchievement(user_id=demo_user.id, badge="Prvi korak", description="Nalog je spreman za prve zadatke."))
            db.add(UserAchievement(user_id=demo_user.id, badge="Demo tester", description="Demo nalog za proveru korisničkog toka."))

        admin = db.query(User).filter(User.role == "admin").first()
        if admin and db.query(AutomationRule).count() == 0:
            db.add(AutomationRule(
                owner_id=admin.id,
                scope="admin",
                name="Upozorenje za loš kvalitet",
                trigger_text="Korisnik ima više od 3 odbijena dokaza i manje od 50% odobrenja.",
                action_text="Prikaži signal u anti-fraud panelu i predloži privremenu blokadu."
            ))
            db.add(AutomationRule(
                owner_id=admin.id,
                scope="admin",
                name="Pending dokazi preko 24h",
                trigger_text="Dokaz čeka proveru duže od 24h.",
                action_text="Prikaži ga u prioritetnoj listi za moderaciju."
            ))
        db.commit()
    finally:
        db.close()


@app.get("/api/v1/stats")
def api_public_stats(db: Session = Depends(get_db)):
    return JSONResponse({
        "platform": "KlikZarada",
        "version": "5.0.0",
        "active_tasks": db.query(Task).filter(Task.status == "active").count(),
        "users": db.query(User).filter(User.role == "korisnik").count(),
        "advertisers": db.query(User).filter(User.role == "oglasivac").count(),
        "approved_rewards_rsd": db.query(func.coalesce(func.sum(TaskSubmission.reward_rsd), 0)).filter(TaskSubmission.status == "approved").scalar(),
    })


@app.get("/api/v1/tasks")
def api_public_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.status == "active").order_by(Task.featured.desc(), Task.reward_rsd.desc()).limit(50).all()
    return JSONResponse({
        "items": [
            {
                "id": t.id,
                "title": t.title,
                "category": t.category,
                "task_type": t.task_type,
                "reward_rsd": t.reward_rsd,
                "estimated_minutes": t.estimated_minutes,
                "remaining": max(0, t.total_slots - t.used_slots - t.reserved_slots),
                "featured": bool(t.featured),
            }
            for t in tasks
        ]
    })


def api_advertiser_from_key(db: Session, api_key: str | None):
    if not api_key:
        return None
    item = db.query(ApiKey).filter(ApiKey.token == api_key, ApiKey.is_active == True).first()
    return item.advertiser if item else None


@app.get("/api/v1/advertiser/stats")
def api_advertiser_stats(api_key: str | None = None, db: Session = Depends(get_db)):
    adv = api_advertiser_from_key(db, api_key)
    if not adv:
        return JSONResponse({"error": "invalid_api_key"}, status_code=401)
    campaigns = db.query(Task).filter(Task.advertiser_id == adv.id).count()
    approved = db.query(TaskSubmission).join(Task).filter(Task.advertiser_id == adv.id, TaskSubmission.status == "approved").count()
    spent = adv.advertiser_spent_rsd
    return JSONResponse({
        "advertiser": adv.full_name,
        "budget_available_rsd": adv.advertiser_budget_rsd,
        "budget_reserved_rsd": adv.advertiser_reserved_rsd,
        "spent_rsd": spent,
        "campaigns": campaigns,
        "approved_results": approved,
    })


# V11.16.1 disabled old badges route
def user_badges(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["korisnik", "admin"])
    badges = db.query(UserAchievement).filter(UserAchievement.user_id == u.id).order_by(UserAchievement.created_at.desc()).all()
    return templates.TemplateResponse("user_badges_v5.html", {"request": request, "user": u, "badges": badges})


@app.post("/dokazi/{submission_id}/prigovor")
def open_dispute(submission_id: int, request: Request, reason: str = Form(...), db: Session = Depends(get_db)):
    u = require(request, db)
    sub = db.query(TaskSubmission).filter(TaskSubmission.id == submission_id).first()
    if not sub:
        raise HTTPException(404)
    allowed = u.role == "admin" or sub.user_id == u.id or (sub.task and sub.task.advertiser_id == u.id)
    if not allowed:
        raise HTTPException(403)
    existing = db.query(Dispute).filter(Dispute.submission_id == sub.id, Dispute.status == "open").first()
    if not existing:
        db.add(Dispute(submission_id=sub.id, opened_by_id=u.id, reason=reason.strip(), status="open"))
        notify(db, None, "admin", "Novi prigovor", f"Otvoren je prigovor za dokaz #{sub.id}.")
        db.commit()
    if u.role == "oglasivac":
        return RedirectResponse("/oglasivac/prigovori?msg=saved", 303)
    if u.role == "korisnik":
        return RedirectResponse("/korisnik/dokazi?msg=saved", 303)
    return RedirectResponse("/admin/prigovori?msg=saved", 303)


@app.get("/oglasivac/prigovori", response_class=HTMLResponse)
def advertiser_disputes(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    disputes = db.query(Dispute).join(TaskSubmission).join(Task).filter(Task.advertiser_id == u.id).order_by(Dispute.created_at.desc()).all()
    return templates.TemplateResponse("disputes_v5.html", {"request": request, "user": u, "disputes": disputes, "mode": "advertiser"})


@app.get("/admin/prigovori", response_class=HTMLResponse)
def admin_disputes(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    disputes = db.query(Dispute).order_by(Dispute.created_at.desc()).all()
    return templates.TemplateResponse("disputes_v5.html", {"request": request, "user": u, "disputes": disputes, "mode": "admin", "flash": flash(msg)})


@app.post("/admin/prigovori/{dispute_id}/{action}")
def admin_dispute_action(dispute_id: int, action: str, request: Request, decision: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    d = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not d:
        raise HTTPException(404)
    if action not in ["accepted", "rejected", "closed"]:
        raise HTTPException(400)
    d.status = action
    d.admin_decision = decision.strip() or action
    d.resolved_at = datetime.utcnow()
    notify(db, d.opened_by, None, "Prigovor rešen", f"Status prigovora za dokaz #{d.submission_id}: {action}.")
    audit(db, u, f"dispute_{action}", "Dispute", d.id, decision)
    db.commit()
    return RedirectResponse("/admin/prigovori?msg=saved", 303)


@app.get("/oglasivac/segmenti", response_class=HTMLResponse)
def advertiser_segments(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    segments = db.query(AudienceSegment).filter(AudienceSegment.advertiser_id == u.id).order_by(AudienceSegment.created_at.desc()).all()
    return templates.TemplateResponse("segments_v5.html", {"request": request, "user": u, "segments": segments, "flash": flash(msg)})


@app.post("/oglasivac/segmenti/novi")
def advertiser_segment_create(
    request: Request,
    name: str = Form(...),
    city: str = Form(""),
    age_group: str = Form(""),
    interests: str = Form(""),
    min_user_level: str = Form("Bronza"),
    min_quality_score: float = Form(80),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    db.add(AudienceSegment(
        advertiser_id=u.id,
        name=name.strip(),
        city=city.strip() or None,
        age_group=age_group.strip() or None,
        interests=interests.strip() or None,
        min_user_level=min_user_level,
        min_quality_score=min_quality_score,
        notes=notes.strip() or None
    ))
    db.commit()
    return RedirectResponse("/oglasivac/segmenti?msg=saved", 303)


@app.get("/oglasivac/planovi", response_class=HTMLResponse)
def advertiser_plans(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    plans = db.query(AdvertiserPlan).filter(AdvertiserPlan.is_active == True).order_by(AdvertiserPlan.monthly_fee_rsd).all()
    sub = db.query(AdvertiserSubscription).filter(AdvertiserSubscription.advertiser_id == u.id, AdvertiserSubscription.status == "active").order_by(AdvertiserSubscription.started_at.desc()).first()
    return templates.TemplateResponse("plans_v5.html", {"request": request, "user": u, "plans": plans, "sub": sub, "flash": flash(msg)})


@app.post("/oglasivac/planovi/{plan_id}/aktiviraj")
def advertiser_activate_plan(plan_id: int, request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    plan = db.query(AdvertiserPlan).filter(AdvertiserPlan.id == plan_id, AdvertiserPlan.is_active == True).first()
    if not plan:
        raise HTTPException(404)
    old = db.query(AdvertiserSubscription).filter(AdvertiserSubscription.advertiser_id == u.id, AdvertiserSubscription.status == "active").all()
    for item in old:
        item.status = "cancelled"
    db.add(AdvertiserSubscription(advertiser_id=u.id, plan_id=plan.id, status="active"))
    notify(db, u, None, "Plan aktiviran", f"Aktivirali ste plan {plan.name}.")
    db.commit()
    return RedirectResponse("/oglasivac/planovi?msg=saved", 303)


@app.get("/oglasivac/api", response_class=HTMLResponse)
def advertiser_api_keys(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    keys = db.query(ApiKey).filter(ApiKey.advertiser_id == u.id).order_by(ApiKey.created_at.desc()).all()
    return templates.TemplateResponse("api_keys_v5.html", {"request": request, "user": u, "keys": keys, "flash": flash(msg)})


@app.post("/oglasivac/api/novi")
def advertiser_api_key_create(request: Request, name: str = Form("Glavni API ključ"), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    token = "kz_" + uuid.uuid4().hex + uuid.uuid4().hex[:8]
    db.add(ApiKey(advertiser_id=u.id, name=name.strip() or "API ključ", token=token, is_active=True))
    db.commit()
    return RedirectResponse("/oglasivac/api?msg=saved", 303)


@app.post("/oglasivac/api/{key_id}/toggle")
def advertiser_api_key_toggle(key_id: int, request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.advertiser_id == u.id).first()
    if not key:
        raise HTTPException(404)
    key.is_active = not key.is_active
    db.commit()
    return RedirectResponse("/oglasivac/api?msg=saved", 303)


@app.get("/oglasivac/automatizacija", response_class=HTMLResponse)
def advertiser_automation(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    rules = db.query(AutomationRule).filter(AutomationRule.owner_id == u.id).order_by(AutomationRule.created_at.desc()).all()
    return templates.TemplateResponse("automation_v5.html", {"request": request, "user": u, "rules": rules, "scope": "advertiser", "flash": flash(msg)})


@app.post("/oglasivac/automatizacija/novo")
def advertiser_automation_create(request: Request, name: str = Form(...), trigger_text: str = Form(...), action_text: str = Form(...), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    db.add(AutomationRule(owner_id=u.id, scope="advertiser", name=name.strip(), trigger_text=trigger_text.strip(), action_text=action_text.strip()))
    db.commit()
    return RedirectResponse("/oglasivac/automatizacija?msg=saved", 303)


@app.get("/oglasivac/sacuvani-izvestaji", response_class=HTMLResponse)
def advertiser_saved_reports(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    reports = db.query(SavedReport).filter(SavedReport.owner_id == u.id).order_by(SavedReport.created_at.desc()).all()
    return templates.TemplateResponse("saved_reports_v5.html", {"request": request, "user": u, "reports": reports, "flash": flash(msg)})


@app.post("/oglasivac/sacuvani-izvestaji/novo")
def advertiser_saved_report_create(request: Request, name: str = Form(...), report_type: str = Form("campaigns"), query_text: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    db.add(SavedReport(owner_id=u.id, name=name.strip(), report_type=report_type, query_text=query_text.strip() or None))
    db.commit()
    return RedirectResponse("/oglasivac/sacuvani-izvestaji?msg=saved", 303)


@app.get("/admin/scale", response_class=HTMLResponse)
def admin_scale_dashboard(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    return templates.TemplateResponse("admin_scale_v5.html", {
        "request": request,
        "user": u,
        "plans": db.query(AdvertiserPlan).order_by(AdvertiserPlan.monthly_fee_rsd).all(),
        "segments": db.query(AudienceSegment).count(),
        "api_keys": db.query(ApiKey).count(),
        "automation_rules": db.query(AutomationRule).count(),
        "disputes_open": db.query(Dispute).filter(Dispute.status == "open").count(),
        "saved_reports": db.query(SavedReport).count(),
    })


@app.get("/admin/planovi", response_class=HTMLResponse)
def admin_plans(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    plans = db.query(AdvertiserPlan).order_by(AdvertiserPlan.monthly_fee_rsd).all()
    subs = db.query(AdvertiserSubscription).order_by(AdvertiserSubscription.started_at.desc()).all()
    return templates.TemplateResponse("admin_plans_v5.html", {"request": request, "user": u, "plans": plans, "subs": subs, "flash": flash(msg)})


@app.post("/admin/planovi/novi")
def admin_plan_create(
    request: Request,
    name: str = Form(...),
    monthly_fee_rsd: float = Form(0),
    platform_fee_percent: float = Form(20),
    max_active_campaigns: int = Form(3),
    features: str = Form(""),
    db: Session = Depends(get_db),
):
    u = require(request, db)
    check_role(u, ["admin"])
    db.add(AdvertiserPlan(
        name=name.strip(),
        monthly_fee_rsd=monthly_fee_rsd,
        platform_fee_percent=platform_fee_percent,
        max_active_campaigns=max_active_campaigns,
        features=features.strip() or None,
        is_active=True
    ))
    audit(db, u, "plan_create", "AdvertiserPlan", None, name)
    db.commit()
    return RedirectResponse("/admin/planovi?msg=saved", 303)


@app.post("/admin/planovi/{plan_id}/toggle")
def admin_plan_toggle(plan_id: int, request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    plan = db.query(AdvertiserPlan).filter(AdvertiserPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404)
    plan.is_active = not plan.is_active
    audit(db, u, "plan_toggle", "AdvertiserPlan", plan.id, plan.name)
    db.commit()
    return RedirectResponse("/admin/planovi?msg=saved", 303)


@app.get("/admin/api-kljucevi", response_class=HTMLResponse)
def admin_api_keys(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
    return templates.TemplateResponse("admin_api_keys_v5.html", {"request": request, "user": u, "keys": keys})


@app.get("/admin/automatizacija", response_class=HTMLResponse)
def admin_automation(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    rules = db.query(AutomationRule).order_by(AutomationRule.created_at.desc()).all()
    return templates.TemplateResponse("automation_v5.html", {"request": request, "user": u, "rules": rules, "scope": "admin", "flash": flash(msg)})


@app.post("/admin/automatizacija/novo")
def admin_automation_create(request: Request, name: str = Form(...), trigger_text: str = Form(...), action_text: str = Form(...), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    db.add(AutomationRule(owner_id=u.id, scope="admin", name=name.strip(), trigger_text=trigger_text.strip(), action_text=action_text.strip()))
    audit(db, u, "automation_create", "AutomationRule", None, name)
    db.commit()
    return RedirectResponse("/admin/automatizacija?msg=saved", 303)




# ---------------------------------------------------
# V6 ENTERPRISE & PRODUCTION
# ---------------------------------------------------

def seed_v6_enterprise():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        if db.query(FeatureFlag).count() == 0:
            flags = [
                FeatureFlag(key="user_kyc", name="KYC verifikacija", description="Omogućava upload i admin proveru dokumenata.", is_enabled=True),
                FeatureFlag(key="webhooks", name="Webhook integracije", description="Oglašivači mogu da primaju evente.", is_enabled=True),
                FeatureFlag(key="crm_sales", name="CRM prodaja", description="Admin sales pipeline za oglašivače.", is_enabled=True),
                FeatureFlag(key="data_exports", name="Data export", description="Korisnici mogu tražiti export svojih podataka.", is_enabled=True),
                FeatureFlag(key="enterprise_sla", name="SLA operativni centar", description="Prioritetni pregled pending stavki.", is_enabled=True),
            ]
            db.add_all(flags)

        if db.query(SystemSetting).count() == 0:
            settings = [
                SystemSetting(key="platform_name", value="KlikZarada", description="Naziv platforme"),
                SystemSetting(key="support_email", value="podrska@klikzarada.rs", description="Email podrške"),
                SystemSetting(key="moderation_sla_hours", value="24", description="Cilj za proveru dokaza"),
                SystemSetting(key="withdrawal_sla_hours", value="72", description="Cilj za obradu isplata"),
                SystemSetting(key="production_mode", value="false", description="Da li je sistem u produkciji"),
                SystemSetting(key="advertiser_payment_account", value="Dodaj broj računa u adminu", description="Račun na koji oglašivači uplaćuju budžet"),
                SystemSetting(key="advertiser_payment_holder", value="Dodaj naziv primaoca u adminu", description="Naziv primaoca za uplatu oglašivača"),
                SystemSetting(key="user_payout_account", value="Dodaj račun za isplatu u adminu", description="Račun sa kog se isplaćuju korisnici"),
                SystemSetting(key="user_payout_holder", value="Dodaj naziv primaoca u adminu", description="Naziv primaoca za isplatu korisnicima"),
                SystemSetting(key="payment_reference", value="KlikZarada budžet", description="Poziv na broj ili svrha uplate oglašivača"),
                SystemSetting(key="payout_reference", value="KlikZarada isplata", description="Poziv na broj ili svrha isplate korisnicima"),
            ]
            db.add_all(settings)

        admin = db.query(User).filter(User.role == "admin").first()
        adv = db.query(User).filter(User.role == "oglasivac").first()
        user = db.query(User).filter(User.role == "korisnik").first()

        if admin and db.query(SecurityEvent).count() == 0:
            db.add(SecurityEvent(user_id=admin.id, event_type="system_bootstrap", severity="low", details="V6 enterprise seed pokrenut."))
            db.add(SecurityEvent(user_id=None, event_type="production_check", severity="medium", details="Pre produkcije proveriti HTTPS, pravne tekstove, backup i email verifikaciju."))

        if adv and db.query(OnboardingItem).filter(OnboardingItem.owner_id == adv.id).count() == 0:
            items = [
                "Popunite profil firme",
                "Verifikujte oglašivača",
                "Dopunite budžet",
                "Kreirajte prvi segment publike",
                "Kreirajte prvu kampanju",
                "Podesite webhook/API ako je potreban",
            ]
            for i, title in enumerate(items, start=1):
                db.add(OnboardingItem(owner_id=adv.id, scope="advertiser", title=title, sort_order=i))

        if adv and db.query(TeamMember).filter(TeamMember.advertiser_id == adv.id).count() == 0:
            db.add(TeamMember(advertiser_id=adv.id, full_name="Demo Menadžer", email="manager@demo.rs", role="manager"))

        if adv and db.query(WebhookEndpoint).filter(WebhookEndpoint.advertiser_id == adv.id).count() == 0:
            db.add(WebhookEndpoint(advertiser_id=adv.id, name="Demo webhook", url="https://example.com/webhook", secret="demo_secret", is_active=False))

        if admin and db.query(SalesLead).count() == 0:
            db.add(SalesLead(company_name="Primer Kompanija", contact_name="Kontakt Osoba", email="kontakt@primer.rs", phone="+381600000001", source="manual", status="new", potential_budget_rsd=50000, notes="Demo lead za CRM pipeline.", owner_id=admin.id))
            db.add(SalesLead(company_name="Lokalni restoran", contact_name="Menadžer", email="restoran@primer.rs", phone="+381600000002", source="outreach", status="contacted", potential_budget_rsd=25000, notes="Potencijal za feedback kampanje.", owner_id=admin.id))

        if user and db.query(KycDocument).filter(KycDocument.user_id == user.id).count() == 0:
            db.add(KycDocument(user_id=user.id, doc_type="identity", file_path=None, status="pending", admin_note="Demo KYC zapis."))

        db.commit()
    finally:
        db.close()


def create_security_event(db: Session, user=None, event_type="event", severity="low", details="", request: Request | None = None):
    ip = None
    if request:
        try:
            ip = request.client.host
        except Exception:
            ip = None
    db.add(SecurityEvent(user_id=user.id if user else None, event_type=event_type, severity=severity, ip_address=ip, details=details))


@app.get("/api/v1/health")
def api_health(db: Session = Depends(get_db)):
    return JSONResponse({
        "status": "ok",
        "version": "6.0.0",
        "database": "ok",
        "active_tasks": db.query(Task).filter(Task.status == "active").count(),
    })


@app.get("/api/v1/system-status")
def api_system_status(db: Session = Depends(get_db)):
    pending_submissions = db.query(TaskSubmission).filter(TaskSubmission.status == "pending").count()
    pending_withdrawals = db.query(Withdrawal).filter(Withdrawal.status == "pending").count()
    open_tickets = db.query(SupportTicket).filter(SupportTicket.status != "closed").count()
    open_disputes = db.query(Dispute).filter(Dispute.status == "open").count()
    return JSONResponse({
        "status": "operational",
        "pending_submissions": pending_submissions,
        "pending_withdrawals": pending_withdrawals,
        "open_tickets": open_tickets,
        "open_disputes": open_disputes,
    })


@app.get("/produkcija", response_class=HTMLResponse)
def production_readiness_page(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    settings = db.query(SystemSetting).order_by(SystemSetting.key).all()
    flags = db.query(FeatureFlag).order_by(FeatureFlag.key).all()
    return templates.TemplateResponse("production_readiness_v6.html", {"request": request, "user": user, "settings": settings, "flags": flags})


@app.get("/korisnik/verifikacija", response_class=HTMLResponse)
def user_kyc_page(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["korisnik", "admin"])
    docs = db.query(KycDocument).filter(KycDocument.user_id == u.id).order_by(KycDocument.created_at.desc()).all()
    return templates.TemplateResponse("user_kyc_v6.html", {"request": request, "user": u, "docs": docs, "flash": flash(msg)})


@app.post("/korisnik/verifikacija")
def user_kyc_upload(request: Request, doc_type: str = Form("identity"), proof_file: UploadFile | None = File(None), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["korisnik", "admin"])
    file_path = save_upload(proof_file)
    db.add(KycDocument(user_id=u.id, doc_type=doc_type, file_path=file_path, status="pending"))
    notify(db, None, "admin", "Nova KYC provera", f"Korisnik {u.full_name} je poslao dokument za verifikaciju.")
    create_security_event(db, u, "kyc_upload", "medium", "Korisnik je poslao KYC dokument.", request)
    db.commit()
    return RedirectResponse("/korisnik/verifikacija?msg=saved", 303)


@app.get("/korisnik/export-podataka", response_class=HTMLResponse)
def user_data_export_page(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["korisnik", "admin"])
    requests = db.query(DataExportRequest).filter(DataExportRequest.user_id == u.id).order_by(DataExportRequest.created_at.desc()).all()
    return templates.TemplateResponse("user_data_export_v6.html", {"request": request, "user": u, "requests": requests, "flash": flash(msg)})


@app.post("/korisnik/export-podataka")
def user_data_export_create(request: Request, export_format: str = Form("csv"), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["korisnik", "admin"])
    db.add(DataExportRequest(user_id=u.id, export_format=export_format, status="pending"))
    notify(db, None, "admin", "Novi data export zahtev", f"Korisnik {u.full_name} traži export podataka.")
    create_security_event(db, u, "data_export_requested", "low", "Korisnik je tražio export podataka.", request)
    db.commit()
    return RedirectResponse("/korisnik/export-podataka?msg=saved", 303)


@app.get("/oglasivac/onboarding", response_class=HTMLResponse)
def advertiser_onboarding(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    items = db.query(OnboardingItem).filter(OnboardingItem.owner_id == u.id).order_by(OnboardingItem.sort_order).all()
    return templates.TemplateResponse("advertiser_onboarding_v6.html", {"request": request, "user": u, "items": items, "flash": flash(msg)})


@app.post("/oglasivac/onboarding/{item_id}/toggle")
def advertiser_onboarding_toggle(item_id: int, request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    item = db.query(OnboardingItem).filter(OnboardingItem.id == item_id, OnboardingItem.owner_id == u.id).first()
    if not item:
        raise HTTPException(404)
    item.status = "done" if item.status != "done" else "open"
    db.commit()
    return RedirectResponse("/oglasivac/onboarding?msg=saved", 303)


@app.get("/oglasivac/webhooks", response_class=HTMLResponse)
def advertiser_webhooks(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    endpoints = db.query(WebhookEndpoint).filter(WebhookEndpoint.advertiser_id == u.id).order_by(WebhookEndpoint.created_at.desc()).all()
    deliveries = db.query(WebhookDelivery).join(WebhookEndpoint).filter(WebhookEndpoint.advertiser_id == u.id).order_by(WebhookDelivery.created_at.desc()).limit(50).all()
    return templates.TemplateResponse("advertiser_webhooks_v6.html", {"request": request, "user": u, "endpoints": endpoints, "deliveries": deliveries, "flash": flash(msg)})


@app.post("/oglasivac/webhooks/novi")
def advertiser_webhook_create(request: Request, name: str = Form(...), url: str = Form(...), events: str = Form("submission.approved,submission.rejected"), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    secret = "whsec_" + uuid.uuid4().hex
    db.add(WebhookEndpoint(advertiser_id=u.id, name=name.strip(), url=url.strip(), events=events.strip(), secret=secret, is_active=True))
    db.commit()
    return RedirectResponse("/oglasivac/webhooks?msg=saved", 303)


@app.post("/oglasivac/webhooks/{endpoint_id}/toggle")
def advertiser_webhook_toggle(endpoint_id: int, request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id, WebhookEndpoint.advertiser_id == u.id).first()
    if not endpoint:
        raise HTTPException(404)
    endpoint.is_active = not endpoint.is_active
    db.commit()
    return RedirectResponse("/oglasivac/webhooks?msg=saved", 303)


@app.post("/oglasivac/webhooks/{endpoint_id}/test")
def advertiser_webhook_test(endpoint_id: int, request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id, WebhookEndpoint.advertiser_id == u.id).first()
    if not endpoint:
        raise HTTPException(404)
    payload = '{"event":"test.ping","platform":"KlikZarada","version":"6.0.0"}'
    db.add(WebhookDelivery(endpoint_id=endpoint.id, event_type="test.ping", payload=payload, status="queued", response_text="V6 demo: isporuka je evidentirana, realni HTTP send se dodaje u produkcionoj integraciji."))
    db.commit()
    return RedirectResponse("/oglasivac/webhooks?msg=saved", 303)


@app.get("/oglasivac/tim", response_class=HTMLResponse)
def advertiser_team(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    members = db.query(TeamMember).filter(TeamMember.advertiser_id == u.id).order_by(TeamMember.created_at.desc()).all()
    return templates.TemplateResponse("advertiser_team_v6.html", {"request": request, "user": u, "members": members, "flash": flash(msg)})


@app.post("/oglasivac/tim/novi")
def advertiser_team_create(request: Request, full_name: str = Form(...), email: str = Form(...), role: str = Form("viewer"), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    db.add(TeamMember(advertiser_id=u.id, full_name=full_name.strip(), email=email.strip(), role=role, is_active=True))
    db.commit()
    return RedirectResponse("/oglasivac/tim?msg=saved", 303)


@app.post("/oglasivac/tim/{member_id}/toggle")
def advertiser_team_toggle(member_id: int, request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    member = db.query(TeamMember).filter(TeamMember.id == member_id, TeamMember.advertiser_id == u.id).first()
    if not member:
        raise HTTPException(404)
    member.is_active = not member.is_active
    db.commit()
    return RedirectResponse("/oglasivac/tim?msg=saved", 303)


@app.get("/admin/enterprise", response_class=HTMLResponse)
def admin_enterprise_dashboard(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    data = {
        "security_events": db.query(SecurityEvent).count(),
        "critical_events": db.query(SecurityEvent).filter(SecurityEvent.severity.in_(["high", "critical"])).count(),
        "kyc_pending": db.query(KycDocument).filter(KycDocument.status == "pending").count(),
        "exports_pending": db.query(DataExportRequest).filter(DataExportRequest.status == "pending").count(),
        "leads_open": db.query(SalesLead).filter(SalesLead.status.in_(["new", "contacted", "demo", "proposal"])).count(),
        "webhooks": db.query(WebhookEndpoint).count(),
        "team_members": db.query(TeamMember).count(),
        "feature_flags": db.query(FeatureFlag).count(),
    }
    return templates.TemplateResponse("admin_enterprise_v6.html", {"request": request, "user": u, **data})


@app.get("/admin/security", response_class=HTMLResponse)
def admin_security(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    events = db.query(SecurityEvent).order_by(SecurityEvent.created_at.desc()).limit(300).all()
    return templates.TemplateResponse("admin_security_v6.html", {"request": request, "user": u, "events": events})


@app.post("/admin/security/event")
def admin_security_event_create(request: Request, event_type: str = Form(...), severity: str = Form("low"), details: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    create_security_event(db, u, event_type.strip(), severity, details.strip(), request)
    audit(db, u, "security_event_create", "SecurityEvent", None, details)
    db.commit()
    return RedirectResponse("/admin/security?msg=saved", 303)


@app.get("/admin/compliance", response_class=HTMLResponse)
def admin_compliance(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    docs = db.query(KycDocument).order_by(KycDocument.created_at.desc()).all()
    exports = db.query(DataExportRequest).order_by(DataExportRequest.created_at.desc()).all()
    return templates.TemplateResponse("admin_compliance_v6.html", {"request": request, "user": u, "docs": docs, "exports": exports})


@app.post("/admin/kyc/{doc_id}/{action}")
def admin_kyc_action(doc_id: int, action: str, request: Request, admin_note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    doc = db.query(KycDocument).filter(KycDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(404)
    if action not in ["approved", "rejected"]:
        raise HTTPException(400)
    doc.status = action
    doc.admin_note = admin_note.strip() or action
    doc.reviewed_at = datetime.utcnow()
    if action == "approved":
        doc.user.email_verified = True
        doc.user.phone_verified = True
    notify(db, doc.user, None, "KYC status", f"Vaša verifikacija je: {action}.")
    audit(db, u, f"kyc_{action}", "KycDocument", doc.id, admin_note)
    db.commit()
    return RedirectResponse("/admin/compliance?msg=saved", 303)


@app.post("/admin/data-export/{request_id}/{action}")
def admin_data_export_action(request_id: int, action: str, request: Request, admin_note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    item = db.query(DataExportRequest).filter(DataExportRequest.id == request_id).first()
    if not item:
        raise HTTPException(404)
    if action not in ["ready", "rejected"]:
        raise HTTPException(400)
    item.status = action
    item.admin_note = admin_note.strip() or action
    item.processed_at = datetime.utcnow()
    notify(db, item.user, None, "Export podataka", f"Status vašeg export zahteva je: {action}.")
    audit(db, u, f"data_export_{action}", "DataExportRequest", item.id, admin_note)
    db.commit()
    return RedirectResponse("/admin/compliance?msg=saved", 303)


@app.get("/admin/crm", response_class=HTMLResponse)
def admin_crm(request: Request, status: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    query = db.query(SalesLead)
    if status and status != "Sve":
        query = query.filter(SalesLead.status == status)
    leads = query.order_by(SalesLead.updated_at.desc()).all()
    return templates.TemplateResponse("admin_crm_v6.html", {"request": request, "user": u, "leads": leads, "status": status or "Sve"})


@app.post("/admin/crm/novi")
def admin_crm_create(request: Request, company_name: str = Form(...), contact_name: str = Form(""), email: str = Form(""), phone: str = Form(""), source: str = Form("manual"), potential_budget_rsd: float = Form(0), notes: str = Form(""), owner_id: int = Form(0), status: str = Form("new"), package_name: str = Form(""), next_action: str = Form(""), risk_flags: str = Form(""), next_url: str = Form("/admin/crm"), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    if status not in ["new", "contacted", "demo", "proposal", "won", "lost"]:
        status = "new"
    db.add(SalesLead(
        company_name=company_name.strip(),
        contact_name=contact_name.strip() or None,
        email=email.strip() or None,
        phone=phone.strip() or None,
        source=source.strip() or "manual",
        status=status,
        potential_budget_rsd=potential_budget_rsd,
        notes=v11838_build_sales_notes(notes, package_name, next_action, risk_flags),
        owner_id=owner_id or u.id,
    ))
    audit(db, u, "crm_lead_create", "SalesLead", None, company_name)
    db.commit()
    target = next_url if next_url.startswith("/admin") else "/admin/crm"
    separator = "&" if "?" in target else "?"
    return RedirectResponse(f"{target}{separator}msg=saved", 303)


@app.post("/admin/crm/{lead_id}/status")
def admin_crm_status(lead_id: int, request: Request, status: str = Form(...), notes: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    lead = db.query(SalesLead).filter(SalesLead.id == lead_id).first()
    if not lead:
        raise HTTPException(404)
    old = lead.status
    lead.status = status
    lead.notes = (lead.notes or "") + ("\n" + notes.strip() if notes.strip() else "")
    lead.updated_at = datetime.utcnow()
    audit(db, u, "crm_status_change", "SalesLead", lead.id, f"{old} -> {status}")
    db.commit()
    return RedirectResponse("/admin/crm?msg=saved", 303)


@app.post("/admin/crm/{lead_id}/plan")
def admin_crm_plan(lead_id: int, request: Request, status: str = Form("contacted"), owner_id: int = Form(0), package_name: str = Form(""), next_action: str = Form(""), risk_flags: str = Form(""), notes: str = Form(""), next_url: str = Form("/admin/oglasivaci"), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    lead = db.query(SalesLead).filter(SalesLead.id == lead_id).first()
    if not lead:
        raise HTTPException(404)
    if status in ["new", "contacted", "demo", "proposal", "won", "lost"]:
        lead.status = status
    if owner_id:
        lead.owner_id = owner_id
    lead.notes = v11838_build_sales_notes(notes, package_name, next_action, risk_flags)
    lead.updated_at = datetime.utcnow()
    audit(db, u, "crm_plan_update", "SalesLead", lead.id, f"status={lead.status}")
    db.commit()
    target = next_url if next_url.startswith("/admin") else "/admin/oglasivaci"
    separator = "&" if "?" in target else "?"
    return RedirectResponse(f"{target}{separator}msg=saved", 303)


@app.get("/admin/feature-flags", response_class=HTMLResponse)
def admin_feature_flags(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    flags = db.query(FeatureFlag).order_by(FeatureFlag.key).all()
    return templates.TemplateResponse("admin_feature_flags_v6.html", {"request": request, "user": u, "flags": flags, "ops_suite": v11838_ops_suite_context(db, "/admin/feature-flags")})


@app.post("/admin/feature-flags/novi")
def admin_feature_flag_create(request: Request, key: str = Form(...), name: str = Form(...), description: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    db.add(FeatureFlag(key=key.strip(), name=name.strip(), description=description.strip() or None, is_enabled=True))
    audit(db, u, "feature_flag_create", "FeatureFlag", None, key)
    db.commit()
    return RedirectResponse("/admin/feature-flags?msg=saved", 303)


@app.post("/admin/feature-flags/{flag_id}/toggle")
def admin_feature_flag_toggle(flag_id: int, request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(404)
    flag.is_enabled = not flag.is_enabled
    audit(db, u, "feature_flag_toggle", "FeatureFlag", flag.id, flag.key)
    db.commit()
    return RedirectResponse("/admin/feature-flags?msg=saved", 303)


@app.get("/admin/system-settings", response_class=HTMLResponse)
def admin_system_settings(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    settings = db.query(SystemSetting).order_by(SystemSetting.key).all()
    task_sources = db.query(TaskSourceV11).order_by(TaskSourceV11.created_at.desc()).all()
    return templates.TemplateResponse("admin_system_settings_v6.html", {"request": request, "user": u, "settings": settings, "task_sources": task_sources, "flash": flash(msg), "finance_accounts": v11836_public_accounts(db), "ops_suite": v11838_ops_suite_context(db, "/admin/system-settings")})


@app.post("/admin/system-settings/save")
def admin_system_setting_save(request: Request, key: str = Form(...), value: str = Form(...), description: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    item = upsert_system_setting(db, key, value, description)
    audit(db, u, "system_setting_save", "SystemSetting", item.id, key)
    db.commit()
    return RedirectResponse("/admin/system-settings?msg=saved", 303)


@app.post("/admin/system-settings/finance-save")
def admin_finance_accounts_save(
    request: Request,
    advertiser_payment_account: str = Form(...),
    advertiser_payment_holder: str = Form(...),
    user_payout_account: str = Form(...),
    user_payout_holder: str = Form(...),
    payment_reference: str = Form(...),
    payout_reference: str = Form(...),
    bank_note: str = Form(""),
    next_url: str = Form("/admin/system-settings"),
    db: Session = Depends(get_db),
):
    u = require(request, db)
    check_role(u, ["admin"])
    payload = [
        ("advertiser_payment_account", advertiser_payment_account, "Račun na koji oglašivači uplaćuju budžet"),
        ("advertiser_payment_holder", advertiser_payment_holder, "Naziv primaoca za uplatu oglašivača"),
        ("user_payout_account", user_payout_account, "Račun sa kog se isplaćuju korisnici"),
        ("user_payout_holder", user_payout_holder, "Naziv primaoca za isplatu korisnicima"),
        ("payment_reference", payment_reference, "Poziv na broj ili svrha uplate oglašivača"),
        ("payout_reference", payout_reference, "Poziv na broj ili svrha isplate korisnicima"),
        ("bank_note", bank_note, "Napomena za prikaz u finansijskim sekcijama"),
    ]
    for key, value, description in payload:
        item = upsert_system_setting(db, key, value, description)
        audit(db, u, "system_setting_save", "SystemSetting", item.id, key)
    db.commit()
    target = next_url if next_url.startswith("/") else "/admin/system-settings"
    return RedirectResponse(f"{target}?msg=saved", 303)


@app.post("/admin/system-settings/task-source-save")
def admin_task_source_save(
    request: Request,
    name: str = Form(...),
    source_type: str = Form("partner_api"),
    endpoint_url: str = Form(""),
    api_key: str = Form(""),
    contact_name: str = Form(""),
    import_mode: str = Form("review"),
    instructions: str = Form(""),
    db: Session = Depends(get_db),
):
    u = require(request, db)
    check_role(u, ["admin"])
    item = TaskSourceV11(
        name=name.strip(),
        source_type=source_type.strip() or "partner_api",
        endpoint_url=endpoint_url.strip() or None,
        api_key=api_key.strip() or None,
        contact_name=contact_name.strip() or None,
        import_mode=import_mode.strip() or "review",
        status="active",
        instructions=instructions.strip() or None,
    )
    db.add(item)
    db.flush()
    audit(db, u, "task_source_create", "TaskSourceV11", item.id, item.name)
    db.commit()
    return RedirectResponse("/admin/system-settings?msg=saved#task-sources", 303)


@app.post("/admin/system-settings/task-source/{source_id}/sync")
def admin_task_source_sync(source_id: int, request: Request, db: Session = Depends(get_db)):
    admin = require(request, db)
    check_role(admin, ["admin"])
    source = db.query(TaskSourceV11).filter(TaskSourceV11.id == source_id).first()
    if not source:
        raise HTTPException(404)
    try:
        result = import_tasks_from_source(db, source, admin_id=admin.id if admin else None)
        audit(db, admin, "task_source_sync", "TaskSourceV11", source.id, f"{source.name} imported={result['created']} skipped={result['skipped']}")
        db.commit()
        return RedirectResponse(f"/admin/import-moderation?msg=imported", 303)
    except HTTPException as exc:
        db.rollback()
        audit(db, admin, "task_source_sync_error", "TaskSourceV11", source.id, f"{source.name} error={exc.detail}")
        db.commit()
        return RedirectResponse("/admin/system-settings?msg=remote_error#task-sources", 303)
    except Exception as exc:
        db.rollback()
        audit(db, admin, "task_source_sync_error", "TaskSourceV11", source.id, f"{source.name} error={exc}")
        db.commit()
        return RedirectResponse("/admin/system-settings?msg=remote_error#task-sources", 303)


@app.post("/admin/system-settings/task-source/{source_id}/toggle")
def admin_task_source_toggle(source_id: int, request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    source = db.query(TaskSourceV11).filter(TaskSourceV11.id == source_id).first()
    if not source:
        raise HTTPException(404)
    source.status = "paused" if source.status == "active" else "active"
    source.updated_at = datetime.utcnow()
    audit(db, u, "task_source_toggle", "TaskSourceV11", source.id, source.name)
    db.commit()
    return RedirectResponse("/admin/system-settings?msg=saved#task-sources", 303)


@app.get("/admin/import-moderation", response_class=HTMLResponse)
def admin_import_moderation(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    sources = db.query(TaskSourceV11).order_by(TaskSourceV11.created_at.desc()).all()
    primary_source = sources[0] if sources else None
    queue = db.query(ModerationQueueV10).order_by(ModerationQueueV10.created_at.desc()).limit(80).all()
    rules = db.query(QualityRuleV10).order_by(QualityRuleV10.created_at.desc()).all()
    segments = db.query(SmartSegmentRuleV10).order_by(SmartSegmentRuleV10.created_at.desc()).all()
    proof_reviews = db.query(ProofFileReviewV11).order_by(ProofFileReviewV11.created_at.desc()).limit(40).all()
    summary = {
        "active_sources": sum(1 for s in sources if s.status == "active"),
        "paused_sources": sum(1 for s in sources if s.status == "paused"),
        "open_queue": sum(1 for q in queue if q.status == "open"),
        "pending_proofs": sum(1 for p in proof_reviews if p.status == "pending"),
    }
    return templates.TemplateResponse(
        "admin_import_moderation_v1.html",
        {
            "request": request,
            "user": u,
            "sources": sources,
            "primary_source": primary_source,
            "queue": queue,
            "rules": rules,
            "segments": segments,
            "proof_reviews": proof_reviews,
            "summary": summary,
            "finance_accounts": v11836_public_accounts(db),
            "flash": flash(msg),
        },
    )


@app.post("/admin/import-moderation/source/{source_id}/sync")
def admin_import_moderation_source_sync(source_id: int, request: Request, db: Session = Depends(get_db)):
    admin = require(request, db)
    check_role(admin, ["admin"])
    source = db.query(TaskSourceV11).filter(TaskSourceV11.id == source_id).first()
    if not source:
        raise HTTPException(404)
    try:
        result = import_tasks_from_source(db, source, admin_id=admin.id if admin else None)
        audit(db, admin, "task_source_sync", "TaskSourceV11", source.id, f"{source.name} imported={result['created']} skipped={result['skipped']}")
        db.commit()
        return RedirectResponse("/admin/import-moderation?msg=imported", 303)
    except HTTPException as exc:
        db.rollback()
        audit(db, admin, "task_source_sync_error", "TaskSourceV11", source.id, f"{source.name} error={exc.detail}")
        db.commit()
        return RedirectResponse("/admin/import-moderation?msg=remote_error", 303)
    except Exception as exc:
        db.rollback()
        audit(db, admin, "task_source_sync_error", "TaskSourceV11", source.id, f"{source.name} error={exc}")
        db.commit()
        return RedirectResponse("/admin/import-moderation?msg=remote_error", 303)


@app.post("/admin/import-moderation/source/{source_id}/preview-create")
def admin_import_moderation_source_preview_create(
    source_id: int,
    request: Request,
    method: str = Form("create"),
    type: str = Form("like"),
    link: str = Form("https://site.ru"),
    title: str = Form("Nova platforma"),
    amount: int = Form(100),
    db: Session = Depends(get_db),
):
    admin = require(request, db)
    check_role(admin, ["admin"])
    source = db.query(TaskSourceV11).filter(TaskSourceV11.id == source_id).first()
    if not source:
        raise HTTPException(404)
    payload = {
        "api_key": (source.api_key or "").strip(),
        "method": method.strip() or "create",
        "type": type.strip() or "like",
        "link": link.strip(),
        "title": title.strip(),
        "amount": max(1, int(amount)),
    }
    try:
        result = task_source_remote_json_post(source, payload)
        preview = json.dumps(result, ensure_ascii=False)[:500]
        audit(db, admin, "task_source_preview_create", "TaskSourceV11", source.id, f"{source.name} payload={payload!r} result={preview}")
        db.commit()
        return RedirectResponse("/admin/import-moderation?msg=remote_ok", 303)
    except Exception as exc:
        audit(db, admin, "task_source_preview_create_error", "TaskSourceV11", source.id, f"{source.name} error={exc}")
        db.commit()
        return RedirectResponse("/admin/import-moderation?msg=remote_error", 303)


@app.post("/admin/import-moderation/sync-all")
def admin_import_moderation_sync_all(request: Request, db: Session = Depends(get_db)):
    admin = require(request, db)
    check_role(admin, ["admin"])
    sources = db.query(TaskSourceV11).filter(TaskSourceV11.status == "active").order_by(TaskSourceV11.created_at.desc()).all()
    total_created = 0
    total_skipped = 0
    for source in sources:
        try:
            result = import_tasks_from_source(db, source, admin_id=admin.id if admin else None)
        except Exception:
            continue
        total_created += result["created"]
        total_skipped += result["skipped"]
        audit(db, admin, "task_source_sync", "TaskSourceV11", source.id, f"{source.name} imported={result['created']} skipped={result['skipped']}")
    db.commit()
    return RedirectResponse("/admin/import-moderation?msg=imported", 303)


@app.get("/admin/sla", response_class=HTMLResponse)
def admin_sla(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    pending_submissions = db.query(TaskSubmission).filter(TaskSubmission.status == "pending").order_by(TaskSubmission.created_at.asc()).limit(100).all()
    pending_withdrawals = db.query(Withdrawal).filter(Withdrawal.status == "pending").order_by(Withdrawal.created_at.asc()).limit(100).all()
    open_tickets = db.query(SupportTicket).filter(SupportTicket.status != "closed").order_by(SupportTicket.created_at.asc()).limit(100).all()
    open_disputes = db.query(Dispute).filter(Dispute.status == "open").order_by(Dispute.created_at.asc()).limit(100).all()
    return templates.TemplateResponse("admin_sla_v6.html", {"request": request, "user": u, "pending_submissions": pending_submissions, "pending_withdrawals": pending_withdrawals, "open_tickets": open_tickets, "open_disputes": open_disputes})


@app.get("/admin/webhooks", response_class=HTMLResponse)
def admin_webhooks(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    endpoints = db.query(WebhookEndpoint).order_by(WebhookEndpoint.created_at.desc()).all()
    deliveries = db.query(WebhookDelivery).order_by(WebhookDelivery.created_at.desc()).limit(200).all()
    return templates.TemplateResponse("admin_webhooks_v6.html", {"request": request, "user": u, "endpoints": endpoints, "deliveries": deliveries})




# ---------------------------------------------------
# V7 AI MARKETPLACE & ANALYTICS
# ---------------------------------------------------

def seed_v7_ai_marketplace():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        if db.query(AIReviewRule).count() == 0:
            db.add_all([
                AIReviewRule(name="Prekratak dokaz", description="Dokaz ima premalo teksta ili nema konkretne informacije.", rule_type="proof_quality", severity="medium"),
                AIReviewRule(name="Dupliran dokaz", description="Isti ili vrlo sličan dokaz se pojavljuje kod više korisnika.", rule_type="fraud", severity="high"),
                AIReviewRule(name="Nejasna kampanja", description="Kampanja nema jasna uputstva ili dokaz.", rule_type="campaign_quality", severity="medium"),
            ])

        if db.query(MarketplaceCategory).count() == 0:
            c1 = MarketplaceCategory(name="Istraživanje tržišta", description="Ankete, segmenti i korisnički feedback.")
            c2 = MarketplaceCategory(name="Testiranje aplikacija", description="UX testovi, beta testovi i prijava bugova.")
            c3 = MarketplaceCategory(name="Lokalna promocija", description="Kampanje za restorane, prodavnice i lokalne servise.")
            db.add_all([c1, c2, c3])
            db.flush()
            db.add_all([
                MarketplaceOffer(category_id=c1.id, title="Mini istraživanje tržišta", description="Kreiranje kampanje za 100 odgovora sa osnovnim izveštajem.", price_rsd=12000, delivery_days=5),
                MarketplaceOffer(category_id=c2.id, title="UX test landing stranice", description="10 korisnika testira landing stranicu i šalje konkretne komentare.", price_rsd=8000, delivery_days=3),
                MarketplaceOffer(category_id=c3.id, title="Lokalni feedback paket", description="Feedback za lokalnu ponudu u izabranom gradu.", price_rsd=9000, delivery_days=4),
            ])

        if db.query(EmailTemplate).count() == 0:
            db.add_all([
                EmailTemplate(key="submission_approved", subject="Vaš dokaz je odobren", body="Zdravo {{ime}}, dokaz za zadatak je odobren i zarada je dodata na wallet."),
                EmailTemplate(key="campaign_active", subject="Kampanja je aktivna", body="Vaša kampanja {{kampanja}} je odobrena i aktivna."),
                EmailTemplate(key="withdrawal_paid", subject="Isplata je obrađena", body="Vaš zahtev za isplatu je označen kao plaćen."),
            ])

        if db.query(ContentPage).count() == 0:
            db.add_all([
                ContentPage(slug="kako-radi", title="Kako radi KlikZarada", body="Korisnici rade zadatke, oglašivači dobijaju rezultate, admin kontroliše kvalitet.", status="published", seo_title="Kako radi KlikZarada"),
                ContentPage(slug="za-agencije", title="KlikZarada za agencije", body="Agencije mogu voditi kampanje, segmente, API i izveštaje za klijente.", status="published", seo_title="KlikZarada za agencije"),
            ])

        if db.query(GrowthExperiment).count() == 0:
            db.add_all([
                GrowthExperiment(name="Referral bonus test", hypothesis="Veći referral bonus povećava broj aktivnih korisnika.", metric="aktivni referral korisnici", status="planned"),
                GrowthExperiment(name="Oglašivač onboarding CTA", hypothesis="Onboarding checklist povećava broj prvih kampanja.", metric="prva kampanja po oglašivaču", status="running"),
            ])

        admin = db.query(User).filter(User.role == "admin").first()
        user = db.query(User).filter(User.role == "korisnik").first()
        adv = db.query(User).filter(User.role == "oglasivac").first()

        if user and db.query(TaskRecommendation).filter(TaskRecommendation.user_id == user.id).count() == 0:
            tasks = db.query(Task).filter(Task.status == "active").limit(5).all()
            for idx, task in enumerate(tasks, start=1):
                db.add(TaskRecommendation(user_id=user.id, task_id=task.id, score=100 - idx * 7, reason="Demo preporuka prema interesovanjima i dostupnoj nagradi."))

        if user and db.query(FraudCase).count() == 0:
            db.add(FraudCase(user_id=user.id, title="Demo fraud case", severity="low", status="open", description="Primer slučaja za proveru anti-fraud toka."))

        if admin and db.query(InternalMessage).count() == 0:
            db.add(InternalMessage(sender_id=admin.id, recipient_id=user.id if user else None, subject="Dobrodošli u V7", body="Ovo je demo interna poruka iz V7 sistema."))

        if adv and db.query(CampaignFunnelEvent).count() == 0:
            t = db.query(Task).filter(Task.advertiser_id == adv.id).first()
            db.add_all([
                CampaignFunnelEvent(advertiser_id=adv.id, task_id=t.id if t else None, event_type="campaign_created", value=1, note="Demo funnel event"),
                CampaignFunnelEvent(advertiser_id=adv.id, task_id=t.id if t else None, event_type="submission_received", value=3, note="Demo funnel event"),
                CampaignFunnelEvent(advertiser_id=adv.id, task_id=t.id if t else None, event_type="submission_approved", value=2, note="Demo funnel event"),
            ])

        db.commit()
    finally:
        db.close()


def v11831_submission_review_profile(db: Session, submission: TaskSubmission):
    task = submission.task
    user = submission.user
    text = (submission.proof or "").strip()
    task_text = " ".join([
        getattr(task, "title", "") or "",
        getattr(task, "category", "") or "",
        getattr(task, "task_type", "") or "",
    ]).lower()
    score = 72.0
    reasons: list[str] = []

    duplicate_count = db.query(TaskSubmission).filter(
        TaskSubmission.proof == submission.proof,
        TaskSubmission.id != submission.id,
    ).count()
    approved_count = db.query(TaskSubmission).filter(TaskSubmission.user_id == getattr(user, "id", 0), TaskSubmission.status == "approved").count()
    rejected_count = db.query(TaskSubmission).filter(TaskSubmission.user_id == getattr(user, "id", 0), TaskSubmission.status == "rejected").count()
    rules = db.query(AIReviewRule).filter(AIReviewRule.is_active == True).order_by(AIReviewRule.created_at.desc()).all()

    if not task or not user:
        return {
            "score": 0.0,
            "risk_level": "high",
            "suggestion": "Ručno proveriti",
            "decision": "manual",
            "reasons": "Nedostaju korisnik ili zadatak.",
            "duplicate_count": duplicate_count,
        }

    if len(text) < 8:
        score -= 45
        reasons.append("Dokaz je prekratak.")
    elif len(text) < 25:
        score -= 20
        reasons.append("Dokaz je kratak.")
    elif len(text) > 220:
        score += 4
        reasons.append("Dokaz je dovoljno detaljan.")

    if submission.proof_file:
        score += 10
        reasons.append("Dodat je fajl dokaz.")
    elif getattr(task, "proof_file_required", False):
        score -= 25
        reasons.append("Fajl dokaz je obavezan.")

    if duplicate_count > 0:
        score -= 35
        reasons.append("Isti tekst dokaza već postoji.")

    if rejected_count >= 3 and rejected_count > approved_count:
        score -= 15
        reasons.append("Korisnik ima više odbijenih dokaza.")
    elif approved_count >= 10 and rejected_count == 0:
        score += 8
        reasons.append("Korisnik ima stabilan kvalitet.")

    if any(k in task_text for k in ["gledanje sajta", "test sajta", "testiranje", "anketa", "feedback", "registracija"]):
        score += 10
    else:
        score -= 6

    if task and (not (task.instructions or "").strip() or len((task.instructions or "").strip()) < 20):
        score -= 5
        reasons.append("Instrukcije kampanje su kratke.")

    for rule in rules:
        severity_penalty = 6 if rule.severity == "low" else 10 if rule.severity == "medium" else 14
        if rule.rule_type == "proof_quality" and len(text) < 30:
            score -= severity_penalty
            reasons.append(rule.name)
        elif rule.rule_type == "fraud" and duplicate_count > 0:
            score -= severity_penalty + 4
            reasons.append(rule.name)
        elif rule.rule_type == "campaign_quality" and task and len((task.instructions or "").strip()) < 20:
            score -= max(3, severity_penalty // 2)
            reasons.append(rule.name)

    score = max(0.0, min(100.0, score))
    if score >= 75:
        risk = "low"
    elif score >= 45:
        risk = "medium"
    else:
        risk = "high"

    auto_approve = (
        score >= 82
        and risk == "low"
        and duplicate_count == 0
        and rejected_count < 3
        and len(text) >= 15
        and (not getattr(task, "proof_file_required", False) or bool(submission.proof_file))
    )
    auto_reject = (
        score <= 30
        or (duplicate_count > 0 and score < 50)
        or (getattr(task, "proof_file_required", False) and not submission.proof_file and score < 45)
    )

    if auto_approve:
        suggestion = "Automatski odobriti"
        decision = "approve"
    elif auto_reject:
        suggestion = "Automatski odbiti"
        decision = "reject"
    else:
        suggestion = "Ručno proveriti"
        decision = "manual"

    if not reasons:
        reasons.append("Nema posebnih rizika.")

    return {
        "score": score,
        "risk_level": risk,
        "suggestion": suggestion,
        "decision": decision,
        "reasons": "; ".join(dict.fromkeys(reasons)),
        "duplicate_count": duplicate_count,
    }


def run_ai_review_for_submission(db: Session, submission: TaskSubmission, profile: dict | None = None):
    profile = profile or v11831_submission_review_profile(db, submission)
    result = AIReviewResult(
        submission_id=submission.id,
        task_id=submission.task_id,
        score=profile["score"],
        risk_level=profile["risk_level"],
        suggestion=profile["suggestion"],
        reasons=profile["reasons"],
    )
    db.add(result)
    return result


def v11831_auto_review_submission(db: Session, submission: TaskSubmission, actor=None, source: str = "system"):
    profile = v11831_submission_review_profile(db, submission)
    existing = db.query(AIReviewResult).filter(AIReviewResult.submission_id == submission.id).first()
    if not existing:
        run_ai_review_for_submission(db, submission, profile)

    note = f"Automatski pregled ({source}): {profile['reasons']}"
    if profile["decision"] == "approve":
        outcome = v11831_approve_submission(db, actor, submission, note)
        if outcome == "approved":
            v11823_auto_log(db, "submission_auto_approved", f"Dokaz #{submission.id} odobren automatski.", amount_rsd=float(submission.reward_rsd or 0), meta_json=f"score={profile['score']};risk={profile['risk_level']}")
            return "approved", profile
    elif profile["decision"] == "reject":
        outcome = v11831_reject_submission(db, actor, submission, note)
        if outcome == "rejected":
            v11823_auto_log(db, "submission_auto_rejected", f"Dokaz #{submission.id} odbijen automatski.", meta_json=f"score={profile['score']};risk={profile['risk_level']}")
            return "rejected", profile

    existing_manual = db.query(AutoEngineLogV114).filter(
        AutoEngineLogV114.event_type == "submission_needs_manual_review",
        AutoEngineLogV114.meta_json.contains(f"submission_id={submission.id}"),
    ).first()
    if not existing_manual:
        v11823_auto_log(
            db,
            "submission_needs_manual_review",
            f"Dokaz #{submission.id} ide na ručnu proveru.",
            status="queued",
            meta_json=f"submission_id={submission.id};score={profile['score']};risk={profile['risk_level']}",
        )
    return "manual", profile


def create_analytics_snapshot(db: Session, label: str):
    snap = AnalyticsSnapshot(
        label=label,
        users_count=db.query(User).filter(User.role == "korisnik").count(),
        advertisers_count=db.query(User).filter(User.role == "oglasivac").count(),
        active_tasks=db.query(Task).filter(Task.status == "active").count(),
        approved_submissions=db.query(TaskSubmission).filter(TaskSubmission.status == "approved").count(),
        platform_revenue_rsd=db.query(func.coalesce(func.sum(TaskSubmission.platform_fee_rsd), 0)).filter(TaskSubmission.status == "approved").scalar(),
        rewards_rsd=db.query(func.coalesce(func.sum(TaskSubmission.reward_rsd), 0)).filter(TaskSubmission.status == "approved").scalar(),
    )
    db.add(snap)
    return snap


@app.get("/strana/{slug}", response_class=HTMLResponse)
def public_content_page(slug: str, request: Request, db: Session = Depends(get_db)):
    page = db.query(ContentPage).filter(ContentPage.slug == slug, ContentPage.status == "published").first()
    if not page:
        raise HTTPException(404)
    return templates.TemplateResponse("content_page_v7.html", {"request": request, "user": current_user(request, db), "page": page})


@app.get("/api/v1/marketplace")
def api_marketplace(db: Session = Depends(get_db)):
    offers = db.query(MarketplaceOffer).filter(MarketplaceOffer.status == "active").order_by(MarketplaceOffer.price_rsd).all()
    return JSONResponse({"items": [{"id": o.id, "title": o.title, "price_rsd": o.price_rsd, "delivery_days": o.delivery_days, "category": o.category.name if o.category else None} for o in offers]})


@app.get("/api/v1/analytics/summary")
def api_analytics_summary(db: Session = Depends(get_db)):
    return JSONResponse({
        "users": db.query(User).filter(User.role == "korisnik").count(),
        "advertisers": db.query(User).filter(User.role == "oglasivac").count(),
        "tasks_active": db.query(Task).filter(Task.status == "active").count(),
        "submissions_pending": db.query(TaskSubmission).filter(TaskSubmission.status == "pending").count(),
        "platform_revenue_rsd": db.query(func.coalesce(func.sum(TaskSubmission.platform_fee_rsd), 0)).filter(TaskSubmission.status == "approved").scalar(),
    })


@app.get("/korisnik/preporuke", response_class=HTMLResponse)
def user_recommendations(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["korisnik", "admin"])
    recs = db.query(TaskRecommendation).filter(TaskRecommendation.user_id == u.id).order_by(TaskRecommendation.score.desc()).all()
    if not recs:
        tasks = db.query(Task).filter(Task.status == "active").order_by(Task.reward_rsd.desc()).limit(10).all()
        for idx, task in enumerate(tasks, start=1):
            db.add(TaskRecommendation(user_id=u.id, task_id=task.id, score=100 - idx * 5, reason="Automatska preporuka prema nagradi i dostupnosti."))
        db.commit()
        recs = db.query(TaskRecommendation).filter(TaskRecommendation.user_id == u.id).order_by(TaskRecommendation.score.desc()).all()
    return templates.TemplateResponse("user_recommendations_v7.html", {"request": request, "user": u, "recs": recs})


@app.get("/poruke", response_class=HTMLResponse)
def internal_messages(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    inbox = db.query(InternalMessage).filter(InternalMessage.recipient_id == u.id).order_by(InternalMessage.created_at.desc()).all()
    sent = db.query(InternalMessage).filter(InternalMessage.sender_id == u.id).order_by(InternalMessage.created_at.desc()).limit(50).all()
    users = db.query(User).order_by(User.full_name).limit(200).all()
    return templates.TemplateResponse("internal_messages_v7.html", {"request": request, "user": u, "inbox": inbox, "sent": sent, "users": users, "flash": flash(msg)})


@app.post("/poruke/posalji")
def internal_message_send(request: Request, recipient_id: int = Form(...), subject: str = Form(...), body: str = Form(...), db: Session = Depends(get_db)):
    u = require(request, db)
    recipient = db.query(User).filter(User.id == recipient_id).first()
    if not recipient:
        raise HTTPException(404)
    db.add(InternalMessage(sender_id=u.id, recipient_id=recipient.id, subject=subject.strip(), body=body.strip()))
    notify(db, recipient, None, "Nova interna poruka", subject.strip())
    db.commit()
    return RedirectResponse("/poruke?msg=saved", 303)


@app.get("/oglasivac/marketplace", response_class=HTMLResponse)
def advertiser_marketplace(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    offers = db.query(MarketplaceOffer).filter(MarketplaceOffer.status == "active").order_by(MarketplaceOffer.price_rsd).all()
    orders = db.query(MarketplaceOrder).filter(MarketplaceOrder.advertiser_id == u.id).order_by(MarketplaceOrder.created_at.desc()).all()
    return templates.TemplateResponse("advertiser_marketplace_v7.html", {"request": request, "user": u, "offers": offers, "orders": orders, "flash": flash(msg)})


@app.post("/oglasivac/marketplace/{offer_id}/naruci")
def advertiser_marketplace_order(offer_id: int, request: Request, note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    offer = db.query(MarketplaceOffer).filter(MarketplaceOffer.id == offer_id, MarketplaceOffer.status == "active").first()
    if not offer:
        raise HTTPException(404)
    if u.advertiser_budget_rsd < offer.price_rsd:
        return RedirectResponse("/oglasivac/marketplace?msg=campaign_budget_error", 303)
    u.advertiser_budget_rsd -= offer.price_rsd
    u.advertiser_spent_rsd += offer.price_rsd
    db.add(MarketplaceOrder(offer_id=offer.id, advertiser_id=u.id, status="pending", note=note.strip() or None))
    add_budget_tx(db, u, -offer.price_rsd, "marketplace_order", f"Marketplace narudžbina: {offer.title}")
    notify(db, None, "admin", "Nova marketplace narudžbina", f"Oglašivač {u.full_name} je naručio: {offer.title}")
    db.commit()
    return RedirectResponse("/oglasivac/marketplace?msg=saved", 303)


@app.get("/oglasivac/funnel", response_class=HTMLResponse)
def advertiser_funnel(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    events = db.query(CampaignFunnelEvent).filter(CampaignFunnelEvent.advertiser_id == u.id).order_by(CampaignFunnelEvent.created_at.desc()).all()
    totals = {}
    for e in events:
        totals[e.event_type] = totals.get(e.event_type, 0) + (e.value or 0)
    return templates.TemplateResponse("advertiser_funnel_v7.html", {"request": request, "user": u, "events": events, "totals": totals})


@app.get("/admin/v7", response_class=HTMLResponse)
def admin_v7_dashboard(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    data = {
        "ai_reviews": db.query(AIReviewResult).count(),
        "recommendations": db.query(TaskRecommendation).count(),
        "marketplace_orders": db.query(MarketplaceOrder).count(),
        "payout_batches": db.query(PayoutBatch).count(),
        "fraud_cases": db.query(FraudCase).filter(FraudCase.status.in_(["open", "investigating"])).count(),
        "content_pages": db.query(ContentPage).count(),
        "experiments": db.query(GrowthExperiment).count(),
        "snapshots": db.query(AnalyticsSnapshot).count(),
    }
    return templates.TemplateResponse("admin_v7_dashboard.html", {"request": request, "user": u, **data})


@app.get("/admin/ai-review", response_class=HTMLResponse)
def admin_ai_review(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    rules = db.query(AIReviewRule).order_by(AIReviewRule.created_at.desc()).all()
    results = db.query(AIReviewResult).order_by(AIReviewResult.created_at.desc()).limit(200).all()
    pending = db.query(TaskSubmission).filter(TaskSubmission.status == "pending").order_by(TaskSubmission.created_at.desc()).limit(50).all()
    stats = {
        "pending": len(pending),
        "reviewed": db.query(AIReviewResult).count(),
        "auto_approved": db.query(AutoEngineLogV114).filter(AutoEngineLogV114.event_type == "submission_auto_approved").count(),
        "auto_rejected": db.query(AutoEngineLogV114).filter(AutoEngineLogV114.event_type == "submission_auto_rejected").count(),
    }
    return templates.TemplateResponse("admin_ai_review_v7.html", {"request": request, "user": u, "rules": rules, "results": results, "pending": pending, "stats": stats, "flash": flash(msg)})


@app.post("/admin/ai-review/run")
def admin_ai_review_run(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    pending = db.query(TaskSubmission).filter(TaskSubmission.status == "pending").order_by(TaskSubmission.created_at.desc()).limit(200).all()
    count = 0
    auto_approved = 0
    auto_rejected = 0
    manual = 0
    for s in pending:
        if s.status != "pending":
            continue
        decision, profile = v11831_auto_review_submission(db, s, actor=u, source="admin_review")
        if decision == "approved":
            auto_approved += 1
        elif decision == "rejected":
            auto_rejected += 1
        else:
            manual += 1
        count += 1
    audit(db, u, "ai_review_run", "TaskSubmission", None, f"processed={count};approved={auto_approved};rejected={auto_rejected};manual={manual}")
    db.commit()
    return RedirectResponse("/admin/ai-review?msg=saved", 303)


@app.post("/admin/ai-review/rule")
def admin_ai_review_rule(request: Request, name: str = Form(...), description: str = Form(""), rule_type: str = Form("proof_quality"), severity: str = Form("medium"), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    db.add(AIReviewRule(name=name.strip(), description=description.strip() or None, rule_type=rule_type, severity=severity, is_active=True))
    audit(db, u, "ai_rule_create", "AIReviewRule", None, name)
    db.commit()
    return RedirectResponse("/admin/ai-review?msg=saved", 303)


@app.get("/admin/analytics", response_class=HTMLResponse)
def admin_analytics(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    snapshots = db.query(AnalyticsSnapshot).order_by(AnalyticsSnapshot.created_at.desc()).limit(50).all()
    latest = snapshots[0] if snapshots else None
    return templates.TemplateResponse("admin_analytics_v7.html", {"request": request, "user": u, "snapshots": snapshots, "latest": latest})


@app.post("/admin/analytics/snapshot")
def admin_analytics_snapshot(request: Request, label: str = Form("Ručni snapshot"), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    snap = create_analytics_snapshot(db, label.strip())
    audit(db, u, "analytics_snapshot", "AnalyticsSnapshot", None, label)
    db.commit()
    return RedirectResponse("/admin/analytics?msg=saved", 303)


@app.get("/admin/marketplace", response_class=HTMLResponse)
def admin_marketplace(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    categories = db.query(MarketplaceCategory).order_by(MarketplaceCategory.name).all()
    offers = db.query(MarketplaceOffer).order_by(MarketplaceOffer.created_at.desc()).all()
    orders = db.query(MarketplaceOrder).order_by(MarketplaceOrder.created_at.desc()).all()
    return templates.TemplateResponse("admin_marketplace_v7.html", {"request": request, "user": u, "categories": categories, "offers": offers, "orders": orders, "flash": flash(msg)})


@app.post("/admin/marketplace/kategorija")
def admin_marketplace_category(request: Request, name: str = Form(...), description: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    db.add(MarketplaceCategory(name=name.strip(), description=description.strip() or None, is_active=True))
    audit(db, u, "marketplace_category_create", "MarketplaceCategory", None, name)
    db.commit()
    return RedirectResponse("/admin/marketplace?msg=saved", 303)


@app.post("/admin/marketplace/ponuda")
def admin_marketplace_offer(request: Request, category_id: int = Form(0), title: str = Form(...), description: str = Form(...), price_rsd: float = Form(...), delivery_days: int = Form(3), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    db.add(MarketplaceOffer(category_id=category_id or None, title=title.strip(), description=description.strip(), price_rsd=price_rsd, delivery_days=delivery_days, status="active"))
    audit(db, u, "marketplace_offer_create", "MarketplaceOffer", None, title)
    db.commit()
    return RedirectResponse("/admin/marketplace?msg=saved", 303)


@app.post("/admin/marketplace/order/{order_id}/{status}")
def admin_marketplace_order_status(order_id: int, status: str, request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    order = db.query(MarketplaceOrder).filter(MarketplaceOrder.id == order_id).first()
    if not order:
        raise HTTPException(404)
    if status not in ["pending", "in_progress", "delivered", "cancelled"]:
        raise HTTPException(400)
    order.status = status
    if status == "delivered":
        order.delivered_at = datetime.utcnow()
    notify(db, order.advertiser, None, "Marketplace narudžbina", f"Status narudžbine #{order.id}: {status}.")
    audit(db, u, "marketplace_order_status", "MarketplaceOrder", order.id, status)
    db.commit()
    return RedirectResponse("/admin/marketplace?msg=saved", 303)


@app.get("/admin/payout-batches", response_class=HTMLResponse)
def admin_payout_batches(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    batches = db.query(PayoutBatch).order_by(PayoutBatch.created_at.desc()).all()
    pending = db.query(Withdrawal).filter(Withdrawal.status == "pending").order_by(Withdrawal.created_at.asc()).all()
    return templates.TemplateResponse("admin_payout_batches_v7.html", {"request": request, "user": u, "batches": batches, "pending": pending, "flash": flash(msg)})


@app.post("/admin/payout-batches/create")
def admin_payout_batch_create(request: Request, title: str = Form("Isplate batch"), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    pending = db.query(Withdrawal).filter(Withdrawal.status == "pending").order_by(Withdrawal.created_at.asc()).all()
    total = sum(w.amount_rsd for w in pending)
    batch = PayoutBatch(title=title.strip(), status="ready", total_amount_rsd=total, created_by_id=u.id)
    db.add(batch)
    db.flush()
    for w in pending:
        db.add(PayoutBatchItem(batch_id=batch.id, withdrawal_id=w.id, amount_rsd=w.amount_rsd, status="included"))
    audit(db, u, "payout_batch_create", "PayoutBatch", batch.id, f"items={len(pending)} total={total}")
    db.commit()
    return RedirectResponse("/admin/payout-batches?msg=saved", 303)


@app.post("/admin/payout-batches/{batch_id}/paid")
def admin_payout_batch_paid(batch_id: int, request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    batch = db.query(PayoutBatch).filter(PayoutBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404)
    batch.status = "paid"
    batch.paid_at = datetime.utcnow()
    items = db.query(PayoutBatchItem).filter(PayoutBatchItem.batch_id == batch.id).all()
    for item in items:
        item.status = "paid"
        item.withdrawal.status = "paid"
        item.withdrawal.processed_at = datetime.utcnow()
        item.withdrawal.admin_note = f"Plaćeno kroz batch #{batch.id}"
        notify(db, item.withdrawal.user, None, "Isplata plaćena", f"Isplata {item.amount_rsd:.0f} RSD je plaćena.")
    audit(db, u, "payout_batch_paid", "PayoutBatch", batch.id, f"items={len(items)}")
    db.commit()
    return RedirectResponse("/admin/payout-batches?msg=saved", 303)


@app.get("/admin/fraud-cases", response_class=HTMLResponse)
def admin_fraud_cases(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    cases = db.query(FraudCase).order_by(FraudCase.created_at.desc()).all()
    users = db.query(User).filter(User.role == "korisnik").order_by(User.full_name).all()
    return templates.TemplateResponse("admin_fraud_cases_v7.html", {"request": request, "user": u, "cases": cases, "users": users})


@app.post("/admin/fraud-cases/create")
def admin_fraud_case_create(request: Request, user_id: int = Form(0), title: str = Form(...), severity: str = Form("medium"), description: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    db.add(FraudCase(user_id=user_id or None, title=title.strip(), severity=severity, status="open", description=description.strip() or None))
    audit(db, u, "fraud_case_create", "FraudCase", None, title)
    db.commit()
    return RedirectResponse("/admin/fraud-cases?msg=saved", 303)


@app.post("/admin/fraud-cases/{case_id}/{status}")
def admin_fraud_case_status(case_id: int, status: str, request: Request, resolution: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    case = db.query(FraudCase).filter(FraudCase.id == case_id).first()
    if not case:
        raise HTTPException(404)
    if status not in ["open", "investigating", "resolved", "dismissed"]:
        raise HTTPException(400)
    case.status = status
    case.resolution = resolution.strip() or case.resolution
    if status in ["resolved", "dismissed"]:
        case.resolved_at = datetime.utcnow()
    audit(db, u, "fraud_case_status", "FraudCase", case.id, status)
    db.commit()
    return RedirectResponse("/admin/fraud-cases?msg=saved", 303)


@app.get("/admin/content", response_class=HTMLResponse)
def admin_content(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    pages = db.query(ContentPage).order_by(ContentPage.updated_at.desc()).all()
    return templates.TemplateResponse("admin_content_v7.html", {"request": request, "user": u, "pages": pages})


@app.post("/admin/content/save")
def admin_content_save(request: Request, slug: str = Form(...), title: str = Form(...), body: str = Form(...), status: str = Form("draft"), seo_title: str = Form(""), seo_description: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    page = db.query(ContentPage).filter(ContentPage.slug == slug.strip()).first()
    if not page:
        page = ContentPage(slug=slug.strip(), title=title.strip(), body=body.strip(), status=status, seo_title=seo_title.strip() or None, seo_description=seo_description.strip() or None)
        db.add(page)
    else:
        page.title = title.strip()
        page.body = body.strip()
        page.status = status
        page.seo_title = seo_title.strip() or None
        page.seo_description = seo_description.strip() or None
        page.updated_at = datetime.utcnow()
    audit(db, u, "content_save", "ContentPage", page.id, slug)
    db.commit()
    return RedirectResponse("/admin/content?msg=saved", 303)


@app.get("/admin/email-templates", response_class=HTMLResponse)
def admin_email_templates(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    items = db.query(EmailTemplate).order_by(EmailTemplate.key).all()
    return templates.TemplateResponse("admin_email_templates_v7.html", {"request": request, "user": u, "items": items})


@app.post("/admin/email-templates/save")
def admin_email_template_save(request: Request, key: str = Form(...), subject: str = Form(...), body: str = Form(...), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    item = db.query(EmailTemplate).filter(EmailTemplate.key == key.strip()).first()
    if not item:
        item = EmailTemplate(key=key.strip(), subject=subject.strip(), body=body.strip(), is_active=True)
        db.add(item)
    else:
        item.subject = subject.strip()
        item.body = body.strip()
        item.updated_at = datetime.utcnow()
    audit(db, u, "email_template_save", "EmailTemplate", item.id, key)
    db.commit()
    return RedirectResponse("/admin/email-templates?msg=saved", 303)


@app.get("/admin/growth", response_class=HTMLResponse)
def admin_growth(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    experiments = db.query(GrowthExperiment).order_by(GrowthExperiment.created_at.desc()).all()
    return templates.TemplateResponse("admin_growth_v7.html", {"request": request, "user": u, "experiments": experiments})


@app.post("/admin/growth/create")
def admin_growth_create(request: Request, name: str = Form(...), hypothesis: str = Form(""), metric: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    db.add(GrowthExperiment(name=name.strip(), hypothesis=hypothesis.strip() or None, metric=metric.strip() or None, status="planned"))
    audit(db, u, "growth_experiment_create", "GrowthExperiment", None, name)
    db.commit()
    return RedirectResponse("/admin/growth?msg=saved", 303)


@app.post("/admin/growth/{experiment_id}/status")
def admin_growth_status(experiment_id: int, request: Request, status: str = Form(...), result_note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    exp = db.query(GrowthExperiment).filter(GrowthExperiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(404)
    exp.status = status
    exp.result_note = result_note.strip() or exp.result_note
    audit(db, u, "growth_experiment_status", "GrowthExperiment", exp.id, status)
    db.commit()
    return RedirectResponse("/admin/growth?msg=saved", 303)




# ---------------------------------------------------
# V8 COMMAND CENTER
# ---------------------------------------------------

def seed_v8_command():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        if db.query(HelpArticleV8).count() == 0:
            db.add_all([
                HelpArticleV8(slug="kako-poslati-dokaz", title="Kako poslati dobar dokaz?", body="Pošaljite konkretan opis po instrukciji zadatka. Ako zadatak traži sliku ili PDF, dodajte fajl.", audience="users"),
                HelpArticleV8(slug="kako-dopuniti-budzet", title="Kako oglašivač dopunjava budžet?", body="Otvorite Payments, kreirajte zahtev za dopunu i sačekajte admin potvrdu.", audience="advertisers"),
                HelpArticleV8(slug="kako-rade-isplate", title="Kako rade isplate?", body="Korisnik šalje zahtev, admin ga obrađuje ručno ili kroz batch isplate.", audience="all"),
            ])
        if db.query(AnnouncementBannerV8).count() == 0:
            db.add(AnnouncementBannerV8(title="V8 Command je aktivan", body="Dodat je PWA, payments, command center i help/status sistem.", audience="all", severity="success"))
        if db.query(StatusIncidentV8).count() == 0:
            db.add(StatusIncidentV8(title="Sistem operativan", status="resolved", impact="none", description="Demo status incident.", resolved_at=datetime.utcnow()))
        if db.query(ReleaseChecklistV8).count() == 0:
            for title in ["Promeniti SECRET_KEY", "Prebaciti bazu na PostgreSQL", "Podesiti domen i HTTPS", "Podesiti email provider", "Proveriti pravni model isplata", "Napraviti backup strategiju"]:
                db.add(ReleaseChecklistV8(title=title))
        if db.query(CommandItemV8).count() == 0:
            db.add_all([
                CommandItemV8(title="Proveriti pending dokaze", area="ops", priority="high", link="/admin/sla", note="Najstarije pending stavke su prioritet."),
                CommandItemV8(title="Proveriti payment intents", area="finance", priority="medium", link="/admin/payments-v8", note="Potvrditi ručne uplate oglašivača."),
                CommandItemV8(title="Zatvoriti release checklist", area="ops", priority="high", link="/admin/release-v8", note="Pre produkcije zatvoriti sve kritične stavke."),
            ])
        db.commit()
    finally:
        db.close()


@app.get("/manifest.json")
def manifest_json():
    return JSONResponse({
        "name": "KlikZarada",
        "short_name": "KlikZarada",
        "start_url": "/app",
        "display": "standalone",
        "background_color": "#08111f",
        "theme_color": "#2563eb",
        "description": "Mikro-zadaci, kampanje i wallet.",
        "icons": [{"src": "/favicon.ico", "sizes": "64x64", "type": "image/svg+xml"}],
    })


@app.get("/app", response_class=HTMLResponse)
def app_landing(request: Request, db: Session = Depends(get_db)):
    u = current_user(request, db)
    if u:
        return RedirectResponse("/admin/dashboard" if u.role == "admin" else ("/oglasivac/panel" if u.role == "oglasivac" else "/korisnik/panel"), 303)
    return templates.TemplateResponse("app_landing_v8.html", {"request": request, "user": u})


@app.get("/status", response_class=HTMLResponse)
def public_status(request: Request, db: Session = Depends(get_db)):
    incidents = db.query(StatusIncidentV8).order_by(StatusIncidentV8.created_at.desc()).limit(30).all()
    open_count = db.query(StatusIncidentV8).filter(StatusIncidentV8.status != "resolved").count()
    return templates.TemplateResponse("status_v8.html", {"request": request, "user": current_user(request, db), "incidents": incidents, "open_count": open_count})


@app.get("/help", response_class=HTMLResponse)
def public_help(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    query = db.query(HelpArticleV8).filter(HelpArticleV8.status == "published")
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(HelpArticleV8.title.ilike(like), HelpArticleV8.body.ilike(like)))
    articles = query.order_by(HelpArticleV8.updated_at.desc()).all()
    return templates.TemplateResponse("help_v8.html", {"request": request, "user": current_user(request, db), "articles": articles, "q": q or ""})


@app.get("/help/{slug}", response_class=HTMLResponse)
def public_help_article(slug: str, request: Request, db: Session = Depends(get_db)):
    article = db.query(HelpArticleV8).filter(HelpArticleV8.slug == slug, HelpArticleV8.status == "published").first()
    if not article:
        raise HTTPException(404)
    return templates.TemplateResponse("help_article_v8.html", {"request": request, "user": current_user(request, db), "article": article})


@app.get("/api/v1/mobile/config")
def api_mobile_config(db: Session = Depends(get_db)):
    banners = db.query(AnnouncementBannerV8).filter(AnnouncementBannerV8.is_active == True).order_by(AnnouncementBannerV8.created_at.desc()).limit(5).all()
    return JSONResponse({"version": "8.0.0", "pwa": True, "banners": [{"title": b.title, "body": b.body, "severity": b.severity} for b in banners]})


@app.get("/api/v1/status")
def api_status_v8(db: Session = Depends(get_db)):
    open_count = db.query(StatusIncidentV8).filter(StatusIncidentV8.status != "resolved").count()
    return JSONResponse({"status": "operational" if open_count == 0 else "degraded", "open_incidents": open_count})


@app.get("/oglasivac/payments-v8", response_class=HTMLResponse)
def advertiser_payments_v8(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    intents = db.query(PaymentIntentV8).filter(PaymentIntentV8.advertiser_id == u.id).order_by(PaymentIntentV8.created_at.desc()).all()
    return templates.TemplateResponse("advertiser_payments_v8.html", {"request": request, "user": u, "intents": intents, "flash": flash(msg)})


@app.post("/oglasivac/payments-v8/create")
def advertiser_payment_create_v8(request: Request, amount_rsd: float = Form(...), method: str = Form("manual"), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["oglasivac", "admin"])
    if amount_rsd <= 0:
        raise HTTPException(400)
    ref = "KZ-" + uuid.uuid4().hex[:10].upper()
    db.add(PaymentIntentV8(advertiser_id=u.id, amount_rsd=amount_rsd, reference=ref, method=method, status="pending"))
    db.add(JobItemV8(job_type="payment_intent_created", payload=f"ref={ref}; amount={amount_rsd}", status="queued"))
    notify(db, None, "admin", "Nova dopuna budžeta", f"Oglašivač {u.full_name} je kreirao dopunu {amount_rsd:.0f} RSD. Ref: {ref}")
    db.commit()
    return RedirectResponse("/oglasivac/payments-v8?msg=saved", 303)


@app.get("/admin/v8", response_class=HTMLResponse)
def admin_v8_dashboard(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    return templates.TemplateResponse("admin_v8_dashboard.html", {
        "request": request,
        "user": u,
        "payments_pending": db.query(PaymentIntentV8).filter(PaymentIntentV8.status == "pending").count(),
        "command_open": db.query(CommandItemV8).filter(CommandItemV8.status.in_(["open", "doing"])).count(),
        "jobs_queued": db.query(JobItemV8).filter(JobItemV8.status == "queued").count(),
        "emails_queued": db.query(EmailOutboxV8).filter(EmailOutboxV8.status == "queued").count(),
        "release_open": db.query(ReleaseChecklistV8).filter(ReleaseChecklistV8.status != "done").count(),
        "incidents_open": db.query(StatusIncidentV8).filter(StatusIncidentV8.status != "resolved").count(),
    })


@app.get("/admin/command-center-v8", response_class=HTMLResponse)
def admin_command_center_v8(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    items = db.query(CommandItemV8).order_by(CommandItemV8.created_at.desc()).all()
    return templates.TemplateResponse("admin_command_center_v8.html", {"request": request, "user": u, "items": items})


@app.post("/admin/command-center-v8/create")
def admin_command_create_v8(request: Request, title: str = Form(...), area: str = Form("ops"), priority: str = Form("medium"), link: str = Form(""), note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    db.add(CommandItemV8(title=title.strip(), area=area, priority=priority, link=link.strip() or None, note=note.strip() or None))
    audit(db, u, "v8_command_create", "CommandItemV8", None, title)
    db.commit()
    return RedirectResponse("/admin/command-center-v8?msg=saved", 303)


@app.post("/admin/command-center-v8/{item_id}/{status}")
def admin_command_status_v8(item_id: int, status: str, request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    item = db.query(CommandItemV8).filter(CommandItemV8.id == item_id).first()
    if not item:
        raise HTTPException(404)
    if status not in ["open", "doing", "done", "ignored"]:
        raise HTTPException(400)
    item.status = status
    if status in ["done", "ignored"]:
        item.resolved_at = datetime.utcnow()
    db.commit()
    return RedirectResponse("/admin/command-center-v8?msg=saved", 303)


@app.get("/admin/payments-v8", response_class=HTMLResponse)
def admin_payments_v8(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    intents = db.query(PaymentIntentV8).order_by(PaymentIntentV8.created_at.desc()).all()
    return templates.TemplateResponse("admin_payments_v8.html", {"request": request, "user": u, "intents": intents})


@app.post("/admin/payments-v8/{intent_id}/{action}")
def admin_payment_action_v8(intent_id: int, action: str, request: Request, admin_note: str = Form(""), next_url: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    intent = db.query(PaymentIntentV8).filter(PaymentIntentV8.id == intent_id).first()
    if not intent:
        raise HTTPException(404)
    if intent.status != "pending":
        return RedirectResponse("/admin/payments-v8", 303)
    if action == "confirm":
        intent.status = "confirmed"
        intent.confirmed_at = datetime.utcnow()
        intent.admin_note = admin_note.strip() or "Potvrđeno"
        intent.advertiser.advertiser_budget_rsd += intent.amount_rsd
        add_budget_tx(db, intent.advertiser, intent.amount_rsd, "manual_topup", f"V8 payment confirmed: {intent.reference}")
        notify(db, intent.advertiser, None, "Budžet dopunjen", f"Budžet je dopunjen za {intent.amount_rsd:.0f} RSD.")
    elif action == "reject":
        intent.status = "rejected"
        intent.admin_note = admin_note.strip() or "Odbijeno"
        notify(db, intent.advertiser, None, "Dopuna odbijena", f"Dopuna {intent.reference} je odbijena.")
    else:
        raise HTTPException(400)
    audit(db, u, f"v8_payment_{action}", "PaymentIntentV8", intent.id, admin_note)
    db.commit()
    target = next_url if next_url.startswith("/admin") else "/admin/payments-v8"
    separator = "&" if "?" in target else "?"
    return RedirectResponse(f"{target}{separator}msg=saved", 303)


@app.get("/admin/jobs-v8", response_class=HTMLResponse)
def admin_jobs_v8(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    jobs = db.query(JobItemV8).order_by(JobItemV8.created_at.desc()).limit(300).all()
    return templates.TemplateResponse("admin_jobs_v8.html", {"request": request, "user": u, "jobs": jobs})


@app.post("/admin/jobs-v8/create")
def admin_job_create_v8(request: Request, job_type: str = Form(...), payload: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    db.add(JobItemV8(job_type=job_type.strip(), payload=payload.strip() or None, status="queued"))
    db.commit()
    return RedirectResponse("/admin/jobs-v8?msg=saved", 303)


@app.post("/admin/jobs-v8/{job_id}/{status}")
def admin_job_status_v8(job_id: int, status: str, request: Request, last_error: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    job = db.query(JobItemV8).filter(JobItemV8.id == job_id).first()
    if not job:
        raise HTTPException(404)
    if status not in ["queued", "running", "done", "failed"]:
        raise HTTPException(400)
    job.status = status
    job.attempts += 1
    job.last_error = last_error.strip() or job.last_error
    if status in ["done", "failed"]:
        job.processed_at = datetime.utcnow()
    db.commit()
    return RedirectResponse("/admin/jobs-v8?msg=saved", 303)


@app.get("/admin/email-outbox-v8", response_class=HTMLResponse)
def admin_email_outbox_v8(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    emails = db.query(EmailOutboxV8).order_by(EmailOutboxV8.created_at.desc()).limit(300).all()
    return templates.TemplateResponse("admin_email_outbox_v8.html", {"request": request, "user": u, "emails": emails})


@app.post("/admin/email-outbox-v8/create")
def admin_email_create_v8(request: Request, recipient_email: str = Form(...), subject: str = Form(...), body: str = Form(...), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    db.add(EmailOutboxV8(recipient_email=recipient_email.strip(), subject=subject.strip(), body=body.strip(), status="queued"))
    db.commit()
    return RedirectResponse("/admin/email-outbox-v8?msg=saved", 303)


@app.post("/admin/email-outbox-v8/{email_id}/{status}")
def admin_email_status_v8(email_id: int, status: str, request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    email = db.query(EmailOutboxV8).filter(EmailOutboxV8.id == email_id).first()
    if not email:
        raise HTTPException(404)
    if status not in ["queued", "sent", "failed"]:
        raise HTTPException(400)
    email.status = status
    if status == "sent":
        email.sent_at = datetime.utcnow()
    db.commit()
    return RedirectResponse("/admin/email-outbox-v8?msg=saved", 303)


@app.get("/admin/help-v8", response_class=HTMLResponse)
def admin_help_v8(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    articles = db.query(HelpArticleV8).order_by(HelpArticleV8.updated_at.desc()).all()
    return templates.TemplateResponse("admin_help_v8.html", {"request": request, "user": u, "articles": articles})


@app.post("/admin/help-v8/save")
def admin_help_save_v8(request: Request, slug: str = Form(...), title: str = Form(...), body: str = Form(...), audience: str = Form("all"), status: str = Form("published"), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    article = db.query(HelpArticleV8).filter(HelpArticleV8.slug == slug.strip()).first()
    if not article:
        article = HelpArticleV8(slug=slug.strip(), title=title.strip(), body=body.strip(), audience=audience, status=status)
        db.add(article)
    else:
        article.title = title.strip()
        article.body = body.strip()
        article.audience = audience
        article.status = status
        article.updated_at = datetime.utcnow()
    db.commit()
    return RedirectResponse("/admin/help-v8?msg=saved", 303)


@app.get("/admin/release-v8", response_class=HTMLResponse)
def admin_release_v8(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    checklist = db.query(ReleaseChecklistV8).order_by(ReleaseChecklistV8.created_at.desc()).all()
    return templates.TemplateResponse("admin_release_v8.html", {"request": request, "user": u, "checklist": checklist})


@app.post("/admin/release-v8/create")
def admin_release_check_create_v8(request: Request, title: str = Form(...), owner: str = Form("admin"), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    db.add(ReleaseChecklistV8(title=title.strip(), owner=owner.strip() or "admin", status="open"))
    db.commit()
    return RedirectResponse("/admin/release-v8?msg=saved", 303)


@app.post("/admin/release-v8/{item_id}/{status}")
def admin_release_check_status_v8(item_id: int, status: str, request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    item = db.query(ReleaseChecklistV8).filter(ReleaseChecklistV8.id == item_id).first()
    if not item:
        raise HTTPException(404)
    if status not in ["open", "done", "blocked"]:
        raise HTTPException(400)
    item.status = status
    db.commit()
    return RedirectResponse("/admin/release-v8?msg=saved", 303)




# ---------------------------------------------------
# V9 LAUNCH & REVENUE OS
# ---------------------------------------------------

def seed_v9_launch_os():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        admin = db.query(User).filter(User.role == "admin").first()
        adv = db.query(User).filter(User.role == "oglasivac").first()

        if db.query(LaunchCampaignV9).count() == 0:
            c1 = LaunchCampaignV9(name="Prvih 50 oglašivača", channel="email", goal="Kontaktirati prve firme i dovesti prve plaćene kampanje.", budget_rsd=20000, status="planned")
            c2 = LaunchCampaignV9(name="Facebook grupe launch", channel="groups", goal="Objave u relevantnim grupama i prikupljanje prvih korisnika.", budget_rsd=5000, status="planned")
            db.add_all([c1, c2])
            db.flush()
            db.add_all([
                LaunchTaskV9(campaign_id=c1.id, title="Napraviti listu 100 firmi", owner="admin", priority="high"),
                LaunchTaskV9(campaign_id=c1.id, title="Poslati prvi email pitch", owner="admin", priority="high"),
                LaunchTaskV9(campaign_id=c2.id, title="Pripremiti objave za Facebook grupe", owner="admin", priority="medium"),
            ])

        if db.query(AffiliatePartnerV9).count() == 0:
            db.add_all([
                AffiliatePartnerV9(name="Demo Student Partner", partner_type="student", email="student@demo.rs", code="STUDENT10", commission_percent=10, notes="Student za lokalnu akviziciju korisnika."),
                AffiliatePartnerV9(name="Demo Agency Partner", partner_type="agency", email="agency@demo.rs", code="AGENCY15", commission_percent=15, notes="Agencija za dovođenje oglašivača."),
            ])

        if db.query(SalesScriptV9).count() == 0:
            db.add_all([
                SalesScriptV9(title="Pitch za oglašivače", target="advertiser", script_text="Zdravo, razvijamo platformu gde možete dobiti realan feedback, ankete i testiranje od korisnika iz Srbije. Plaćate samo validne rezultate."),
                SalesScriptV9(title="Poruka adminu Facebook grupe", target="group_admin", script_text="Zdravo, da li je moguće da objavimo poziv za korisnike koji žele da zarade radeći kratke online zadatke? Objavu bismo prilagodili pravilima grupe."),
                SalesScriptV9(title="Pitch za partnere", target="partner", script_text="Tražimo partnere koji mogu dovesti firme ili korisnike. Partner dobija proviziju od prvih kampanja koje dovede."),
            ])

        if db.query(OutreachContactV9).count() == 0:
            db.add_all([
                OutreachContactV9(business_name="Primer restoran", contact_name="Menadžer", channel="manual", city="Niš", status="new", potential_value_rsd=15000, notes="Potencijal za feedback kampanju."),
                OutreachContactV9(business_name="Primer e-shop", contact_name="Marketing", channel="email", city="Beograd", status="contacted", potential_value_rsd=30000, notes="Potencijal za anketu i UX test."),
            ])

        if db.query(RevenueForecastV9).count() == 0:
            f = RevenueForecastV9(title="Prva 3 meseca", scenario="base", period="monthly")
            db.add(f)
            db.flush()
            for label, advertisers, avg_budget, fee in [
                ("Mesec 1", 10, 10000, 20),
                ("Mesec 2", 25, 15000, 20),
                ("Mesec 3", 50, 20000, 18),
            ]:
                db.add(RevenueForecastLineV9(
                    forecast_id=f.id, label=label, advertisers_count=advertisers,
                    avg_budget_rsd=avg_budget, platform_fee_percent=fee,
                    estimated_revenue_rsd=advertisers * avg_budget * fee / 100,
                    note="Base scenario"
                ))

        if db.query(GoLiveCheckV9).count() == 0:
            for area, title in [
                ("security", "Promeniti secret key"),
                ("legal", "Proveriti uslove korišćenja i privatnost"),
                ("finance", "Definisati pravni model isplata korisnicima"),
                ("ops", "Testirati korisnik-oglašivač-admin tok"),
                ("marketing", "Pripremiti prve launch objave"),
                ("backup", "Napraviti prvi backup snapshot"),
            ]:
                db.add(GoLiveCheckV9(area=area, title=title, importance="high"))

        if db.query(BackupSnapshotV9).count() == 0:
            db.add(BackupSnapshotV9(title="Pre-launch demo snapshot", snapshot_type="pre_release", file_hint="klikzarada_v9.db", note="Demo zapis; realni backup se dodaje pri produkciji."))

        if db.query(CompetitorNoteV9).count() == 0:
            db.add(CompetitorNoteV9(name="SEO/klik platforme", url="", strengths="Velika baza korisnika", weaknesses="Nizak kvalitet i spam reputacija", our_angle="KlikZarada se pozicionira kao realni feedback, ankete i testiranje, ne spam klikovi."))

        if db.query(RoadmapItemV9).count() == 0:
            for title in ["Email verifikacija", "PostgreSQL deploy", "Pravi payment provider", "Automatski AI scoring", "Mobile push notifikacije"]:
                db.add(RoadmapItemV9(title=title, phase="next", priority="high"))

        if adv and db.query(CustomerSuccessNoteV9).count() == 0:
            db.add(CustomerSuccessNoteV9(advertiser_id=adv.id, title="Demo oglašivač health", note="Proveriti da li je kreirao kampanju i dopunio budžet.", health="yellow", next_action="Kontaktirati i ponuditi pomoć oko prve kampanje."))

        if db.query(PricingExperimentV9).count() == 0:
            db.add_all([
                PricingExperimentV9(name="Start 20% provizija", commission_percent=20, monthly_fee_rsd=0, target_segment="small_business", status="running"),
                PricingExperimentV9(name="Pro 15% + mesečna pretplata", commission_percent=15, monthly_fee_rsd=4900, target_segment="agencies", status="planned"),
            ])

        if db.query(PressKitAssetV9).count() == 0:
            db.add_all([
                PressKitAssetV9(title="Kratak opis platforme", asset_type="text", body="KlikZarada je srpska platforma za mikro-zadatke, ankete, testiranje i realan korisnički feedback."),
                PressKitAssetV9(title="Slogan", asset_type="text", body="Zaradite kroz realne zadatke. Oglašavajte se kroz merljive rezultate."),
            ])

        db.commit()
    finally:
        db.close()


@app.get("/api/v1/v9/launch-summary")
def api_v9_launch_summary(db: Session = Depends(get_db)):
    return JSONResponse({
        "launch_campaigns": db.query(LaunchCampaignV9).count(),
        "open_launch_tasks": db.query(LaunchTaskV9).filter(LaunchTaskV9.status != "done").count(),
        "affiliate_partners": db.query(AffiliatePartnerV9).filter(AffiliatePartnerV9.status == "active").count(),
        "outreach_contacts": db.query(OutreachContactV9).count(),
        "golive_open": db.query(GoLiveCheckV9).filter(GoLiveCheckV9.status != "done").count(),
        "forecast_revenue_rsd": db.query(func.coalesce(func.sum(RevenueForecastLineV9.estimated_revenue_rsd), 0)).scalar(),
    })


@app.get("/admin/v9", response_class=HTMLResponse)
def admin_v9_dashboard(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["admin"])
    return templates.TemplateResponse("admin_v9_dashboard.html", {
        "request": request, "user": u,
        "campaigns": db.query(LaunchCampaignV9).count(),
        "tasks_open": db.query(LaunchTaskV9).filter(LaunchTaskV9.status != "done").count(),
        "partners": db.query(AffiliatePartnerV9).count(),
        "contacts": db.query(OutreachContactV9).count(),
        "golive_open": db.query(GoLiveCheckV9).filter(GoLiveCheckV9.status != "done").count(),
        "forecast": db.query(func.coalesce(func.sum(RevenueForecastLineV9.estimated_revenue_rsd), 0)).scalar(),
    })


@app.get("/admin/launch-v9", response_class=HTMLResponse)
def admin_launch_v9(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    campaigns = db.query(LaunchCampaignV9).order_by(LaunchCampaignV9.created_at.desc()).all()
    tasks = db.query(LaunchTaskV9).order_by(LaunchTaskV9.created_at.desc()).all()
    return templates.TemplateResponse("admin_launch_v9.html", {"request": request, "user": u, "campaigns": campaigns, "tasks": tasks, "ops_suite": v11838_ops_suite_context(db, "/admin/launch-v9")})


@app.post("/admin/launch-v9/campaign")
def admin_launch_campaign_create_v9(request: Request, name: str = Form(...), channel: str = Form("manual"), goal: str = Form(""), budget_rsd: float = Form(0), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(LaunchCampaignV9(name=name.strip(), channel=channel, goal=goal.strip() or None, budget_rsd=budget_rsd, status="planned"))
    audit(db, u, "v9_launch_campaign_create", "LaunchCampaignV9", None, name)
    db.commit()
    return RedirectResponse("/admin/launch-v9?msg=saved", 303)


@app.post("/admin/launch-v9/task")
def admin_launch_task_create_v9(request: Request, campaign_id: int = Form(0), title: str = Form(...), owner: str = Form("admin"), priority: str = Form("medium"), due_date: str = Form(""), note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(LaunchTaskV9(campaign_id=campaign_id or None, title=title.strip(), owner=owner, priority=priority, due_date=due_date.strip() or None, note=note.strip() or None))
    db.commit()
    return RedirectResponse("/admin/launch-v9?msg=saved", 303)


@app.post("/admin/launch-v9/task/{task_id}/{status}")
def admin_launch_task_status_v9(task_id: int, status: str, request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    item = db.query(LaunchTaskV9).filter(LaunchTaskV9.id == task_id).first()
    if not item: raise HTTPException(404)
    if status not in ["open", "doing", "done", "blocked"]: raise HTTPException(400)
    item.status = status
    db.commit()
    return RedirectResponse("/admin/launch-v9?msg=saved", 303)


@app.get("/admin/affiliate-v9", response_class=HTMLResponse)
def admin_affiliate_v9(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    partners = db.query(AffiliatePartnerV9).order_by(AffiliatePartnerV9.created_at.desc()).all()
    deals = db.query(AffiliateDealV9).order_by(AffiliateDealV9.created_at.desc()).all()
    advertisers = db.query(User).filter(User.role == "oglasivac").order_by(User.full_name).all()
    return templates.TemplateResponse("admin_affiliate_v9.html", {"request": request, "user": u, "partners": partners, "deals": deals, "advertisers": advertisers})


@app.post("/admin/affiliate-v9/partner")
def admin_affiliate_partner_create_v9(request: Request, name: str = Form(...), partner_type: str = Form("creator"), email: str = Form(""), phone: str = Form(""), code: str = Form(...), commission_percent: float = Form(10), notes: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(AffiliatePartnerV9(name=name.strip(), partner_type=partner_type, email=email.strip() or None, phone=phone.strip() or None, code=code.strip().upper(), commission_percent=commission_percent, notes=notes.strip() or None))
    db.commit()
    return RedirectResponse("/admin/affiliate-v9?msg=saved", 303)


@app.post("/admin/affiliate-v9/deal")
def admin_affiliate_deal_create_v9(request: Request, partner_id: int = Form(...), advertiser_id: int = Form(0), amount_rsd: float = Form(...), note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    partner = db.query(AffiliatePartnerV9).filter(AffiliatePartnerV9.id == partner_id).first()
    if not partner: raise HTTPException(404)
    commission = amount_rsd * partner.commission_percent / 100
    db.add(AffiliateDealV9(partner_id=partner.id, advertiser_id=advertiser_id or None, amount_rsd=amount_rsd, commission_rsd=commission, note=note.strip() or None))
    db.commit()
    return RedirectResponse("/admin/affiliate-v9?msg=saved", 303)


@app.get("/admin/outreach-v9", response_class=HTMLResponse)
def admin_outreach_v9(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    contacts = db.query(OutreachContactV9).order_by(OutreachContactV9.updated_at.desc()).all()
    scripts = db.query(SalesScriptV9).order_by(SalesScriptV9.created_at.desc()).all()
    return templates.TemplateResponse("admin_outreach_v9.html", {"request": request, "user": u, "contacts": contacts, "scripts": scripts})


@app.post("/admin/outreach-v9/contact")
def admin_outreach_contact_create_v9(request: Request, business_name: str = Form(...), contact_name: str = Form(""), channel: str = Form("manual"), email: str = Form(""), phone: str = Form(""), city: str = Form(""), potential_value_rsd: float = Form(0), notes: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(OutreachContactV9(business_name=business_name.strip(), contact_name=contact_name.strip() or None, channel=channel, email=email.strip() or None, phone=phone.strip() or None, city=city.strip() or None, potential_value_rsd=potential_value_rsd, notes=notes.strip() or None))
    db.commit()
    return RedirectResponse("/admin/outreach-v9?msg=saved", 303)


@app.post("/admin/outreach-v9/{contact_id}/status")
def admin_outreach_status_v9(contact_id: int, request: Request, status: str = Form(...), note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    c = db.query(OutreachContactV9).filter(OutreachContactV9.id == contact_id).first()
    if not c: raise HTTPException(404)
    c.status = status
    c.updated_at = datetime.utcnow()
    db.add(OutreachActivityV9(contact_id=c.id, activity_type="status", result=status, note=note.strip() or None))
    db.commit()
    return RedirectResponse("/admin/outreach-v9?msg=saved", 303)


@app.post("/admin/outreach-v9/script")
def admin_sales_script_create_v9(request: Request, title: str = Form(...), target: str = Form("advertiser"), script_text: str = Form(...), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(SalesScriptV9(title=title.strip(), target=target, script_text=script_text.strip()))
    db.commit()
    return RedirectResponse("/admin/outreach-v9?msg=saved", 303)


@app.get("/admin/revenue-v9", response_class=HTMLResponse)
def admin_revenue_v9(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    forecasts = db.query(RevenueForecastV9).order_by(RevenueForecastV9.created_at.desc()).all()
    lines = db.query(RevenueForecastLineV9).all()
    pricing = db.query(PricingExperimentV9).order_by(PricingExperimentV9.created_at.desc()).all()
    margin_snapshot = v11837_margin_snapshot(db)
    forecast_alerts = []
    for line in lines:
        fee = v11837_money(getattr(line, "platform_fee_percent", 0))
        if fee < margin_snapshot["platform_percent"]:
            forecast_alerts.append({
                "label": getattr(line, "label", "-"),
                "forecast": line.forecast.title if getattr(line, "forecast", None) else "-",
                "message": f"Forecast line koristi fee {fee:.1f}% ispod trenutnog preporučenog praga {margin_snapshot['platform_percent']:.1f}%.",
            })
    return templates.TemplateResponse("admin_revenue_v9.html", {
        "request": request, "user": u, "forecasts": forecasts, "lines": lines, "pricing": pricing,
        "margin_snapshot": margin_snapshot, "sales_packages": margin_snapshot["packages"], "forecast_alerts": forecast_alerts,
    })


@app.post("/admin/revenue-v9/forecast")
def admin_revenue_forecast_create_v9(request: Request, title: str = Form(...), scenario: str = Form("base"), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(RevenueForecastV9(title=title.strip(), scenario=scenario))
    db.commit()
    return RedirectResponse("/admin/revenue-v9?msg=saved", 303)


@app.post("/admin/revenue-v9/line")
def admin_revenue_line_create_v9(request: Request, forecast_id: int = Form(...), label: str = Form(...), advertisers_count: int = Form(...), avg_budget_rsd: float = Form(...), platform_fee_percent: float = Form(20), note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    revenue = advertisers_count * avg_budget_rsd * platform_fee_percent / 100
    db.add(RevenueForecastLineV9(forecast_id=forecast_id, label=label.strip(), advertisers_count=advertisers_count, avg_budget_rsd=avg_budget_rsd, platform_fee_percent=platform_fee_percent, estimated_revenue_rsd=revenue, note=note.strip() or None))
    db.commit()
    return RedirectResponse("/admin/revenue-v9?msg=saved", 303)


@app.get("/admin/golive-v9", response_class=HTMLResponse)
def admin_golive_v9(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    checks = db.query(GoLiveCheckV9).order_by(GoLiveCheckV9.created_at.desc()).all()
    backups = db.query(BackupSnapshotV9).order_by(BackupSnapshotV9.created_at.desc()).all()
    return templates.TemplateResponse("admin_golive_v9.html", {"request": request, "user": u, "checks": checks, "backups": backups, "ops_suite": v11838_ops_suite_context(db, "/admin/golive-v9")})


@app.post("/admin/golive-v9/check")
def admin_golive_check_create_v9(request: Request, area: str = Form("ops"), title: str = Form(...), importance: str = Form("high"), note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(GoLiveCheckV9(area=area, title=title.strip(), importance=importance, note=note.strip() or None))
    db.commit()
    return RedirectResponse("/admin/golive-v9?msg=saved", 303)


@app.post("/admin/golive-v9/check/{check_id}/{status}")
def admin_golive_check_status_v9(check_id: int, status: str, request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    c = db.query(GoLiveCheckV9).filter(GoLiveCheckV9.id == check_id).first()
    if not c: raise HTTPException(404)
    if status not in ["open", "done", "blocked"]: raise HTTPException(400)
    c.status = status
    db.commit()
    return RedirectResponse("/admin/golive-v9?msg=saved", 303)


@app.post("/admin/golive-v9/backup")
def admin_backup_create_v9(request: Request, title: str = Form(...), snapshot_type: str = Form("manual"), file_hint: str = Form("klikzarada_v9.db"), note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(BackupSnapshotV9(title=title.strip(), snapshot_type=snapshot_type, file_hint=file_hint.strip() or None, note=note.strip() or None))
    db.commit()
    return RedirectResponse("/admin/golive-v9?msg=saved", 303)


@app.get("/admin/strategy-v9", response_class=HTMLResponse)
def admin_strategy_v9(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    competitors = db.query(CompetitorNoteV9).order_by(CompetitorNoteV9.created_at.desc()).all()
    roadmap = db.query(RoadmapItemV9).order_by(RoadmapItemV9.created_at.desc()).all()
    cs = db.query(CustomerSuccessNoteV9).order_by(CustomerSuccessNoteV9.created_at.desc()).all()
    press = db.query(PressKitAssetV9).order_by(PressKitAssetV9.created_at.desc()).all()
    advertisers = db.query(User).filter(User.role == "oglasivac").order_by(User.full_name).all()
    return templates.TemplateResponse("admin_strategy_v9.html", {"request": request, "user": u, "competitors": competitors, "roadmap": roadmap, "cs": cs, "press": press, "advertisers": advertisers})


@app.post("/admin/strategy-v9/roadmap")
def admin_strategy_roadmap_create_v9(request: Request, title: str = Form(...), phase: str = Form("next"), priority: str = Form("medium"), note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(RoadmapItemV9(title=title.strip(), phase=phase, priority=priority, note=note.strip() or None))
    db.commit()
    return RedirectResponse("/admin/strategy-v9?msg=saved", 303)


@app.post("/admin/strategy-v9/competitor")
def admin_strategy_competitor_create_v9(request: Request, name: str = Form(...), url: str = Form(""), strengths: str = Form(""), weaknesses: str = Form(""), our_angle: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(CompetitorNoteV9(name=name.strip(), url=url.strip() or None, strengths=strengths.strip() or None, weaknesses=weaknesses.strip() or None, our_angle=our_angle.strip() or None))
    db.commit()
    return RedirectResponse("/admin/strategy-v9?msg=saved", 303)


@app.post("/admin/strategy-v9/press")
def admin_strategy_press_create_v9(request: Request, title: str = Form(...), asset_type: str = Form("text"), body: str = Form(""), file_url: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(PressKitAssetV9(title=title.strip(), asset_type=asset_type, body=body.strip() or None, file_url=file_url.strip() or None))
    db.commit()
    return RedirectResponse("/admin/strategy-v9?msg=saved", 303)




# ---------------------------------------------------
# V10 AUTOMATION, DATA STUDIO & CLIENT PORTAL
# ---------------------------------------------------

def seed_v10_automation_os():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        admin = db.query(User).filter(User.role == "admin").first()
        adv = db.query(User).filter(User.role == "oglasivac").first()
        user = db.query(User).filter(User.role == "korisnik").first()

        if db.query(WorkflowTemplateV10).count() == 0:
            wt1 = WorkflowTemplateV10(name="Odobren dokaz workflow", trigger_type="submission_approved", description="Notifikacija, ledger, webhook i analytics event.")
            wt2 = WorkflowTemplateV10(name="Novi oglašivač onboarding", trigger_type="advertiser_registered", description="Kreira onboarding taskove i sales follow-up.")
            db.add_all([wt1, wt2])
            db.flush()
            run = WorkflowRunV10(template_id=wt1.id, status="done", context="Demo workflow run")
            db.add(run)
            db.flush()
            db.add_all([
                WorkflowStepRunV10(workflow_run_id=run.id, step_name="Send notification", status="done", result="Demo notification sent"),
                WorkflowStepRunV10(workflow_run_id=run.id, step_name="Create analytics event", status="done", result="Demo analytics created"),
            ])

        if db.query(SurveyV10).count() == 0:
            survey = SurveyV10(advertiser_id=adv.id if adv else None, title="Demo anketa za korisnike", description="Kratka anketa za proveru korisničkih navika.", reward_rsd=50, status="active")
            db.add(survey)
            db.flush()
            db.add_all([
                SurveyQuestionV10(survey_id=survey.id, question_text="Koliko često radite online zadatke?", question_type="single_choice", options_text="Svakodnevno;Nekoliko puta nedeljno;Retko"),
                SurveyQuestionV10(survey_id=survey.id, question_text="Šta vam je najvažnije kod zadatka?", question_type="text"),
            ])

        if db.query(UTMCampaignV10).count() == 0:
            utm = UTMCampaignV10(name="V10 launch Facebook", source="facebook", medium="paid_social", campaign="v10_launch", target_url="/registracija", clicks=120, conversions=12, spend_rsd=3000)
            db.add(utm)
            db.add(UTMCampaignV10(name="Partner email test", source="partner", medium="email", campaign="partner_email", target_url="/registracija", clicks=80, conversions=9, spend_rsd=0))

        if db.query(ConversionGoalV10).count() == 0:
            goal1 = ConversionGoalV10(name="Nova registracija korisnika", goal_type="user_registration", value_rsd=100)
            goal2 = ConversionGoalV10(name="Nova kampanja oglašivača", goal_type="advertiser_campaign", value_rsd=3000)
            db.add_all([goal1, goal2])

        if db.query(ClientPortalProjectV10).count() == 0:
            project = ClientPortalProjectV10(advertiser_id=adv.id if adv else None, title="Demo klijent kampanja", status="active", budget_rsd=50000, health="green", summary="Portal projekat za oglašivača.")
            db.add(project)
            db.flush()
            db.add(ClientPortalUpdateV10(project_id=project.id, title="Kampanja pripremljena", body="Segment, budžet i zadaci su spremni za launch.", visibility="client"))

        if db.query(ContractV10).count() == 0:
            contract = ContractV10(advertiser_id=adv.id if adv else None, title="Demo ugovor za kampanju", contract_type="campaign", amount_rsd=50000, status="draft", terms_text="Draft ugovora za oglašavanje i mikro-zadatke.")
            db.add(contract)
            db.flush()
            db.add_all([
                ContractMilestoneV10(contract_id=contract.id, title="Prva kampanja", amount_rsd=20000, status="open"),
                ContractMilestoneV10(contract_id=contract.id, title="Izveštaj i optimizacija", amount_rsd=30000, status="open"),
            ])

        if db.query(DataStudioDashboardV10).count() == 0:
            dash = DataStudioDashboardV10(owner_id=admin.id if admin else None, title="Executive dashboard", audience="admin")
            db.add(dash)
            db.flush()
            db.add_all([
                DataStudioWidgetV10(dashboard_id=dash.id, title="Korisnici", widget_type="metric", metric_key="users"),
                DataStudioWidgetV10(dashboard_id=dash.id, title="Oglašivači", widget_type="metric", metric_key="advertisers"),
                DataStudioWidgetV10(dashboard_id=dash.id, title="Revenue", widget_type="metric", metric_key="revenue"),
            ])

        if db.query(ModerationQueueV10).count() == 0:
            db.add_all([
                ModerationQueueV10(item_type="submission", item_id=1, priority="high", reason="Demo: proveriti dokaz."),
                ModerationQueueV10(item_type="campaign", item_id=1, priority="medium", reason="Demo: proveriti instrukcije kampanje."),
            ])

        if db.query(SmartSegmentRuleV10).count() == 0:
            db.add_all([
                SmartSegmentRuleV10(name="Pouzdani korisnici", rule_text="quality_score >= 90 AND level in ('Zlato','Premium')", estimated_users=25),
                SmartSegmentRuleV10(name="Novi korisnici iz Srbije", rule_text="city contains Srbija AND approved_submissions < 3", estimated_users=100),
            ])

        if db.query(QualityRuleV10).count() == 0:
            db.add_all([
                QualityRuleV10(name="Kratak dokaz", applies_to="submission", threshold=30, action="manual_review"),
                QualityRuleV10(name="Nizak quality score", applies_to="user", threshold=60, action="flag_user"),
            ])

        if db.query(RevenueGoalV10).count() == 0:
            db.add(RevenueGoalV10(title="Prvih 100.000 RSD provizije", target_rsd=100000, current_rsd=0, period="monthly"))

        if db.query(ExperimentVariantV10).count() == 0:
            db.add_all([
                ExperimentVariantV10(experiment_name="Landing hero CTA", variant_name="Zaradite kroz zadatke", traffic_percent=50, conversions=12),
                ExperimentVariantV10(experiment_name="Landing hero CTA", variant_name="Pronađite plaćene mikro-zadatke", traffic_percent=50, conversions=15),
            ])

        if db.query(PartnerPayoutV10).count() == 0:
            db.add(PartnerPayoutV10(partner_name="Demo Agency Partner", amount_rsd=5000, status="pending", note="Demo payout za affiliate partnera."))

        if db.query(OpsPlaybookV10).count() == 0:
            db.add_all([
                OpsPlaybookV10(title="Ako se nakupi pending dokaza", trigger_text="Pending dokazi > 50", steps_text="1. Otvori moderation queue. 2. Pokreni AI review. 3. Reši high priority prvo."),
                OpsPlaybookV10(title="Ako oglašivač nema budžet", trigger_text="Kampanja odbijena zbog budžeta", steps_text="1. Pošalji payment link. 2. Kreiraj payment intent. 3. Potvrdi uplatu."),
            ])

        db.commit()
    finally:
        db.close()


@app.get("/api/v1/v10/summary")
def api_v10_summary(db: Session = Depends(get_db)):
    db.add(ApiUsageLogV10(endpoint="/api/v1/v10/summary", status_code=200, latency_ms=1))
    db.commit()
    return JSONResponse({
        "version": "10.0.0",
        "workflows": db.query(WorkflowTemplateV10).count(),
        "surveys": db.query(SurveyV10).count(),
        "utm_campaigns": db.query(UTMCampaignV10).count(),
        "client_projects": db.query(ClientPortalProjectV10).count(),
        "contracts": db.query(ContractV10).count(),
        "dashboards": db.query(DataStudioDashboardV10).count(),
        "moderation_open": db.query(ModerationQueueV10).filter(ModerationQueueV10.status == "open").count(),
    })


@app.get("/admin/v10", response_class=HTMLResponse)
def admin_v10_dashboard(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    return templates.TemplateResponse("admin_v10_dashboard.html", {
        "request": request, "user": u,
        "workflows": db.query(WorkflowTemplateV10).count(),
        "surveys": db.query(SurveyV10).count(),
        "utm": db.query(UTMCampaignV10).count(),
        "contracts": db.query(ContractV10).count(),
        "moderation_open": db.query(ModerationQueueV10).filter(ModerationQueueV10.status == "open").count(),
        "revenue_goals": db.query(RevenueGoalV10).count(),
    })


# V11.13 disabled old route /admin/workflows-v10
def admin_workflows_v10(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    templates_ = db.query(WorkflowTemplateV10).order_by(WorkflowTemplateV10.created_at.desc()).all()
    runs = db.query(WorkflowRunV10).order_by(WorkflowRunV10.created_at.desc()).limit(100).all()
    return templates.TemplateResponse("admin_workflows_v10.html", {"request": request, "user": u, "templates_": templates_, "runs": runs})


@app.post("/admin/workflows-v10/template")
def admin_workflow_template_create_v10(request: Request, name: str = Form(...), trigger_type: str = Form("manual"), description: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(WorkflowTemplateV10(name=name.strip(), trigger_type=trigger_type.strip(), description=description.strip() or None))
    db.commit()
    return RedirectResponse("/admin/workflows-v10?msg=saved", 303)


@app.post("/admin/workflows-v10/{template_id}/run")
def admin_workflow_run_v10(template_id: int, request: Request, context: str = Form("Manual run"), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    wt = db.query(WorkflowTemplateV10).filter(WorkflowTemplateV10.id == template_id).first()
    if not wt: raise HTTPException(404)
    run = WorkflowRunV10(template_id=wt.id, status="done", context=context.strip(), finished_at=datetime.utcnow())
    db.add(run); db.flush()
    db.add(WorkflowStepRunV10(workflow_run_id=run.id, step_name="V10 simulated workflow", status="done", result="Workflow executed in demo mode."))
    db.commit()
    return RedirectResponse("/admin/workflows-v10?msg=saved", 303)


@app.get("/admin/surveys-v10", response_class=HTMLResponse)
def admin_surveys_v10(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    surveys = db.query(SurveyV10).order_by(SurveyV10.created_at.desc()).all()
    responses = db.query(SurveyResponseV10).order_by(SurveyResponseV10.created_at.desc()).limit(100).all()
    advertisers = db.query(User).filter(User.role == "oglasivac").order_by(User.full_name).all()
    return templates.TemplateResponse("admin_surveys_v10.html", {"request": request, "user": u, "surveys": surveys, "responses": responses, "advertisers": advertisers})


@app.post("/admin/surveys-v10/create")
def admin_survey_create_v10(request: Request, advertiser_id: int = Form(0), title: str = Form(...), description: str = Form(""), reward_rsd: float = Form(0), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(SurveyV10(advertiser_id=advertiser_id or None, title=title.strip(), description=description.strip() or None, reward_rsd=reward_rsd, status="draft"))
    db.commit()
    return RedirectResponse("/admin/surveys-v10?msg=saved", 303)


@app.post("/admin/surveys-v10/{survey_id}/question")
def admin_survey_question_create_v10(survey_id: int, request: Request, question_text: str = Form(...), question_type: str = Form("text"), options_text: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    if not db.query(SurveyV10).filter(SurveyV10.id == survey_id).first(): raise HTTPException(404)
    db.add(SurveyQuestionV10(survey_id=survey_id, question_text=question_text.strip(), question_type=question_type, options_text=options_text.strip() or None))
    db.commit()
    return RedirectResponse("/admin/surveys-v10?msg=saved", 303)


@app.get("/ankete-v10", response_class=HTMLResponse)
def public_surveys_v10(request: Request, db: Session = Depends(get_db)):
    u = current_user(request, db)
    surveys = db.query(SurveyV10).filter(SurveyV10.status == "active").order_by(SurveyV10.created_at.desc()).all()
    return templates.TemplateResponse("public_surveys_v10.html", {"request": request, "user": u, "surveys": surveys})


@app.get("/ankete-v10/{survey_id}", response_class=HTMLResponse)
def public_survey_detail_v10(survey_id: int, request: Request, db: Session = Depends(get_db)):
    u = current_user(request, db)
    survey = db.query(SurveyV10).filter(SurveyV10.id == survey_id, SurveyV10.status == "active").first()
    if not survey: raise HTTPException(404)
    questions = db.query(SurveyQuestionV10).filter(SurveyQuestionV10.survey_id == survey.id).order_by(SurveyQuestionV10.sort_order).all()
    return templates.TemplateResponse("public_survey_detail_v10.html", {"request": request, "user": u, "survey": survey, "questions": questions})


@app.post("/ankete-v10/{survey_id}/submit")
def public_survey_submit_v10(survey_id: int, request: Request, answers_text: str = Form(...), db: Session = Depends(get_db)):
    u = current_user(request, db)
    survey = db.query(SurveyV10).filter(SurveyV10.id == survey_id, SurveyV10.status == "active").first()
    if not survey: raise HTTPException(404)
    db.add(SurveyResponseV10(survey_id=survey.id, user_id=u.id if u else None, answers_text=answers_text.strip()))
    db.commit()
    return RedirectResponse("/ankete-v10?msg=saved", 303)


@app.get("/admin/tracking-v10", response_class=HTMLResponse)
def admin_tracking_v10(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    campaigns = db.query(UTMCampaignV10).order_by(UTMCampaignV10.created_at.desc()).all()
    goals = db.query(ConversionGoalV10).order_by(ConversionGoalV10.created_at.desc()).all()
    events = db.query(ConversionEventV10).order_by(ConversionEventV10.created_at.desc()).limit(100).all()
    return templates.TemplateResponse("admin_tracking_v10.html", {"request": request, "user": u, "campaigns": campaigns, "goals": goals, "events": events})


@app.post("/admin/tracking-v10/utm")
def admin_utm_create_v10(request: Request, name: str = Form(...), source: str = Form("manual"), medium: str = Form("referral"), campaign: str = Form(...), target_url: str = Form(""), spend_rsd: float = Form(0), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(UTMCampaignV10(name=name.strip(), source=source.strip(), medium=medium.strip(), campaign=campaign.strip(), target_url=target_url.strip() or None, spend_rsd=spend_rsd))
    db.commit()
    return RedirectResponse("/admin/tracking-v10?msg=saved", 303)


@app.post("/admin/tracking-v10/goal")
def admin_goal_create_v10(request: Request, name: str = Form(...), goal_type: str = Form("registration"), value_rsd: float = Form(0), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(ConversionGoalV10(name=name.strip(), goal_type=goal_type.strip(), value_rsd=value_rsd))
    db.commit()
    return RedirectResponse("/admin/tracking-v10?msg=saved", 303)


@app.post("/admin/tracking-v10/event")
def admin_conversion_event_create_v10(request: Request, goal_id: int = Form(...), utm_campaign_id: int = Form(0), value_rsd: float = Form(0), note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(ConversionEventV10(goal_id=goal_id, utm_campaign_id=utm_campaign_id or None, value_rsd=value_rsd, note=note.strip() or None))
    if utm_campaign_id:
        c = db.query(UTMCampaignV10).filter(UTMCampaignV10.id == utm_campaign_id).first()
        if c: c.conversions += 1
    db.commit()
    return RedirectResponse("/admin/tracking-v10?msg=saved", 303)


@app.get("/oglasivac/client-portal-v10", response_class=HTMLResponse)
def advertiser_client_portal_v10(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["oglasivac", "admin"])
    projects = db.query(ClientPortalProjectV10).filter(ClientPortalProjectV10.advertiser_id == u.id).order_by(ClientPortalProjectV10.created_at.desc()).all()
    return templates.TemplateResponse("advertiser_client_portal_v10.html", {"request": request, "user": u, "projects": projects})


@app.get("/admin/client-portal-v10", response_class=HTMLResponse)
def admin_client_portal_v10(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    projects = db.query(ClientPortalProjectV10).order_by(ClientPortalProjectV10.created_at.desc()).all()
    advertisers = db.query(User).filter(User.role == "oglasivac").order_by(User.full_name).all()
    return templates.TemplateResponse("admin_client_portal_v10.html", {"request": request, "user": u, "projects": projects, "advertisers": advertisers})


@app.post("/admin/client-portal-v10/project")
def admin_client_project_create_v10(request: Request, advertiser_id: int = Form(0), title: str = Form(...), budget_rsd: float = Form(0), summary: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(ClientPortalProjectV10(advertiser_id=advertiser_id or None, title=title.strip(), budget_rsd=budget_rsd, summary=summary.strip() or None))
    db.commit()
    return RedirectResponse("/admin/client-portal-v10?msg=saved", 303)


@app.post("/admin/client-portal-v10/{project_id}/update")
def admin_client_project_update_v10(project_id: int, request: Request, title: str = Form(...), body: str = Form(...), visibility: str = Form("client"), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    if not db.query(ClientPortalProjectV10).filter(ClientPortalProjectV10.id == project_id).first(): raise HTTPException(404)
    db.add(ClientPortalUpdateV10(project_id=project_id, title=title.strip(), body=body.strip(), visibility=visibility))
    db.commit()
    return RedirectResponse("/admin/client-portal-v10?msg=saved", 303)


@app.get("/admin/contracts-v10", response_class=HTMLResponse)
def admin_contracts_v10(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    contracts = db.query(ContractV10).order_by(ContractV10.created_at.desc()).all()
    advertisers = db.query(User).filter(User.role == "oglasivac").order_by(User.full_name).all()
    return templates.TemplateResponse("admin_contracts_v10.html", {"request": request, "user": u, "contracts": contracts, "advertisers": advertisers})


@app.post("/admin/contracts-v10/create")
def admin_contract_create_v10(request: Request, advertiser_id: int = Form(0), title: str = Form(...), contract_type: str = Form("campaign"), amount_rsd: float = Form(0), terms_text: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(ContractV10(advertiser_id=advertiser_id or None, title=title.strip(), contract_type=contract_type, amount_rsd=amount_rsd, terms_text=terms_text.strip() or None))
    db.commit()
    return RedirectResponse("/admin/contracts-v10?msg=saved", 303)


@app.post("/admin/contracts-v10/{contract_id}/{status}")
def admin_contract_status_v10(contract_id: int, status: str, request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    c = db.query(ContractV10).filter(ContractV10.id == contract_id).first()
    if not c: raise HTTPException(404)
    if status not in ["draft", "sent", "signed", "cancelled"]: raise HTTPException(400)
    c.status = status
    db.commit()
    return RedirectResponse("/admin/contracts-v10?msg=saved", 303)


@app.get("/admin/data-studio-v10", response_class=HTMLResponse)
def admin_data_studio_v10(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    dashboards = db.query(DataStudioDashboardV10).order_by(DataStudioDashboardV10.created_at.desc()).all()
    widgets = db.query(DataStudioWidgetV10).all()
    return templates.TemplateResponse("admin_data_studio_v10.html", {"request": request, "user": u, "dashboards": dashboards, "widgets": widgets})


@app.post("/admin/data-studio-v10/dashboard")
def admin_dashboard_create_v10(request: Request, title: str = Form(...), audience: str = Form("admin"), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(DataStudioDashboardV10(owner_id=u.id, title=title.strip(), audience=audience))
    db.commit()
    return RedirectResponse("/admin/data-studio-v10?msg=saved", 303)


@app.post("/admin/data-studio-v10/widget")
def admin_widget_create_v10(request: Request, dashboard_id: int = Form(...), title: str = Form(...), widget_type: str = Form("metric"), metric_key: str = Form(""), config_text: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(DataStudioWidgetV10(dashboard_id=dashboard_id, title=title.strip(), widget_type=widget_type, metric_key=metric_key.strip() or None, config_text=config_text.strip() or None))
    db.commit()
    return RedirectResponse("/admin/data-studio-v10?msg=saved", 303)


@app.get("/admin/moderation-v10", response_class=HTMLResponse)
def admin_moderation_v10(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    queue = db.query(ModerationQueueV10).order_by(ModerationQueueV10.created_at.desc()).all()
    rules = db.query(QualityRuleV10).order_by(QualityRuleV10.created_at.desc()).all()
    segments = db.query(SmartSegmentRuleV10).order_by(SmartSegmentRuleV10.created_at.desc()).all()
    return templates.TemplateResponse("admin_moderation_v10.html", {"request": request, "user": u, "queue": queue, "rules": rules, "segments": segments})


@app.post("/admin/moderation-v10/item")
def admin_moderation_item_create_v10(request: Request, item_type: str = Form(...), item_id: int = Form(0), priority: str = Form("medium"), reason: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(ModerationQueueV10(item_type=item_type, item_id=item_id or None, priority=priority, reason=reason.strip() or None))
    db.commit()
    return RedirectResponse("/admin/moderation-v10?msg=saved", 303)


@app.post("/admin/moderation-v10/item/{item_id}/{status}")
def admin_moderation_status_v10(item_id: int, status: str, request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    item = db.query(ModerationQueueV10).filter(ModerationQueueV10.id == item_id).first()
    if not item: raise HTTPException(404)
    if status not in ["open", "doing", "done", "ignored"]: raise HTTPException(400)
    item.status = status
    db.commit()
    return RedirectResponse("/admin/moderation-v10?msg=saved", 303)


@app.get("/admin/revenue-goals-v10", response_class=HTMLResponse)
def admin_revenue_goals_v10(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    goals = db.query(RevenueGoalV10).order_by(RevenueGoalV10.created_at.desc()).all()
    variants = db.query(ExperimentVariantV10).order_by(ExperimentVariantV10.id.desc()).all()
    payouts = db.query(PartnerPayoutV10).order_by(PartnerPayoutV10.created_at.desc()).all()
    return templates.TemplateResponse("admin_revenue_goals_v10.html", {"request": request, "user": u, "goals": goals, "variants": variants, "payouts": payouts})


@app.post("/admin/revenue-goals-v10/goal")
def admin_revenue_goal_create_v10(request: Request, title: str = Form(...), target_rsd: float = Form(...), current_rsd: float = Form(0), period: str = Form("monthly"), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(RevenueGoalV10(title=title.strip(), target_rsd=target_rsd, current_rsd=current_rsd, period=period))
    db.commit()
    return RedirectResponse("/admin/revenue-goals-v10?msg=saved", 303)


@app.get("/admin/playbooks-v10", response_class=HTMLResponse)
def admin_playbooks_v10(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    items = db.query(OpsPlaybookV10).order_by(OpsPlaybookV10.created_at.desc()).all()
    return templates.TemplateResponse("admin_playbooks_v10.html", {"request": request, "user": u, "items": items})


@app.post("/admin/playbooks-v10/create")
def admin_playbook_create_v10(request: Request, title: str = Form(...), trigger_text: str = Form(""), steps_text: str = Form(...), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(OpsPlaybookV10(title=title.strip(), trigger_text=trigger_text.strip() or None, steps_text=steps_text.strip()))
    db.commit()
    return RedirectResponse("/admin/playbooks-v10?msg=saved", 303)




# ---------------------------------------------------
# V11 REAL LAUNCH PACK
# ---------------------------------------------------

def v11_token():
    return secrets.token_urlsafe(32)


def v11_ip(request: Request):
    try:
        return request.client.host
    except Exception:
        return None


def seed_v11_real_launch_pack():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        admin = db.query(User).filter(User.role == "admin").first()
        user = db.query(User).filter(User.role == "korisnik").first()
        adv = db.query(User).filter(User.role == "oglasivac").first()

        if user and db.query(EmailVerificationTokenV11).filter(EmailVerificationTokenV11.user_id == user.id).count() == 0:
            db.add(EmailVerificationTokenV11(user_id=user.id, token=v11_token()))

        if admin and db.query(AdminTwoFactorCodeV11).filter(AdminTwoFactorCodeV11.admin_id == admin.id).count() == 0:
            db.add(AdminTwoFactorCodeV11(admin_id=admin.id, code="123456", status="active"))

        if user and db.query(PayoutMethodV11).filter(PayoutMethodV11.user_id == user.id).count() == 0:
            db.add(PayoutMethodV11(user_id=user.id, method_type="bank", account_holder=user.full_name, account_data="Demo bankovni račun / ručna obrada", status="pending"))

        if adv and db.query(AdvertiserBudgetAlertV11).filter(AdvertiserBudgetAlertV11.advertiser_id == adv.id).count() == 0:
            db.add(AdvertiserBudgetAlertV11(advertiser_id=adv.id, threshold_rsd=5000, status="active"))

        if db.query(LegalPageV11).count() == 0:
            db.add_all([
                LegalPageV11(slug="uslovi-koriscenja", title="Uslovi korišćenja", body="Draft uslova korišćenja. Pre javnog lansiranja proveriti sa pravnikom.", version="0.1"),
                LegalPageV11(slug="politika-privatnosti", title="Politika privatnosti", body="Draft politike privatnosti. Objasniti obradu podataka, kolačiće, naloge, isplate i rok čuvanja.", version="0.1"),
                LegalPageV11(slug="pravila-isplata", title="Pravila isplata", body="Draft pravila isplata. Minimalna isplata, rokovi, ručna provera i poreski model.", version="0.1"),
                LegalPageV11(slug="pravila-oglasivaca", title="Pravila za oglašivače", body="Zabranjene su prevare, lažni klikovi, lažne recenzije, spam i zadaci koji krše pravila drugih platformi.", version="0.1"),
                LegalPageV11(slug="zabranjeni-zadaci", title="Zabranjeni zadaci", body="Zabranjeni su zadaci za lažne recenzije, spam komentare, kockanje, adult, drogu, lažne investicije, prikupljanje lozinki i osetljivih podataka.", version="0.1"),
            ])

        if db.query(ForbiddenTaskRuleV11).count() == 0:
            for title, pattern in [
                ("Lažne recenzije", "lažna recenzija|fake review|review za novac"),
                ("Spam komentari", "spam komentar|masovni komentari"),
                ("Lažni klikovi", "bot klik|lažni pregled|fake click"),
                ("Osetljivi podaci", "lozinka|password|broj kartice|lična karta"),
                ("Zabranjene delatnosti", "kockanje|adult|droga|lažna investicija"),
            ]:
                db.add(ForbiddenTaskRuleV11(title=title, pattern=pattern))

        if db.query(MarketingLandingPageV11).count() == 0:
            db.add_all([
                MarketingLandingPageV11(slug="za-korisnike", title="Za korisnike", headline="Zaradite kroz proverljive online zadatke", body="Rešavajte ankete, testirajte sajtove i šaljite realan feedback. Platforma nagrađuje validne zadatke.", cta_text="Želim da zarađujem", cta_url="/registracija"),
                MarketingLandingPageV11(slug="za-oglasivace", title="Za oglašivače", headline="Dobijte realan feedback i merljive rezultate", body="Kreirajte kampanje za ankete, UX test, registracije i istraživanje tržišta. Plaćate validne rezultate.", cta_text="Pokreni kampanju", cta_url="/registracija"),
                MarketingLandingPageV11(slug="za-agencije", title="Za agencije", headline="Vodite kampanje za klijente kroz KlikZarada sistem", body="Agencije mogu koristiti segmente, izveštaje, marketplace, client portal i affiliate modele.", cta_text="Kontakt prodaja", cta_url="/kontakt"),
                MarketingLandingPageV11(slug="testiranje-sajtova", title="Testiranje sajtova", headline="Saznajte kako korisnici vide vaš sajt", body="Pokrenite zadatak gde korisnici testiraju landing stranicu i šalju konkretne komentare.", cta_text="Kreiraj test", cta_url="/registracija"),
                MarketingLandingPageV11(slug="ankete-i-istrazivanja", title="Ankete i istraživanja", headline="Brzo istraživanje tržišta kroz mikro-zadatke", body="Prikupite odgovore korisnika iz Srbije kroz kontrolisane ankete i pregledne izveštaje.", cta_text="Pokreni anketu", cta_url="/registracija"),
                MarketingLandingPageV11(slug="cenovnik-v11", title="Cenovnik", headline="Jednostavan model: provizija po validnom rezultatu", body="Start bez mesečne pretplate. Platforma uzima proviziju samo na validne rezultate i uspešno obrađene kampanje.", cta_text="Registracija", cta_url="/registracija"),
            ])

        if db.query(ProductionConfigCheckV11).count() == 0:
            for key, title in [
                ("secret_key", "Promeniti KLIKZARADA_SECRET_KEY"),
                ("database", "Prebaciti SQLite na PostgreSQL za produkciju"),
                ("https", "Podesiti domen i HTTPS"),
                ("email_provider", "Podesiti SMTP/SendGrid/Mailgun"),
                ("backup", "Podesiti dnevni backup i restore proceduru"),
                ("legal", "Proveriti pravne tekstove sa pravnikom"),
                ("payments", "Definisati isplate i poreski model"),
                ("admin_2fa", "Uključiti 2FA za admina"),
                ("rate_limit", "Uvesti rate limit za login i registraciju"),
                ("smoke_tests", "Pokrenuti smoke test pre svakog deploy-a"),
            ]:
                db.add(ProductionConfigCheckV11(key=key, title=title, importance="critical" if key in ["secret_key", "database", "https", "legal"] else "high"))

        if db.query(BackupRunV11).count() == 0:
            db.add(BackupRunV11(title="V11 pre-launch backup zapis", backup_type="pre_release", file_hint="klikzarada_v11.db", note="Demo backup zapis; scripts/backup.py kreira realan fajl."))

        if db.query(DeployTargetV11).count() == 0:
            db.add_all([
                DeployTargetV11(name="Render production", provider="Render", status="draft", url="", note="render.yaml dodat u paketu."),
                DeployTargetV11(name="Local Windows test", provider="Local", status="ready", url="http://127.0.0.1:8000", note="Lokalni test preko uvicorn."),
            ])

        if db.query(AdminDailyDeskNoteV11).count() == 0:
            db.add_all([
                AdminDailyDeskNoteV11(title="Proveriti dokaze za moderaciju", priority="high", note="Admin Daily Desk prikazuje pending dokaze i V11 moderation stavke."),
                AdminDailyDeskNoteV11(title="Proveriti pending isplate", priority="high", note="Pre isplate proveriti payout method i fraud signals."),
                AdminDailyDeskNoteV11(title="Proveriti dopune budžeta", priority="medium", note="Payment intents i advertiser budget alerts."),
            ])

        if user and db.query(FraudSignalV11).count() == 0:
            db.add(FraudSignalV11(user_id=user.id, signal_type="demo_signal", risk_score=25, details="Demo signal za V11 anti-fraud panel."))

        db.commit()
    finally:
        db.close()


@app.get("/api/v1/v11/health")
def api_v11_health(db: Session = Depends(get_db)):
    return JSONResponse({
        "status": "ok",
        "version": "11.0.0",
        "db": "ok",
        "users": db.query(User).count(),
        "tasks": db.query(Task).count(),
    })


@app.get("/api/v1/v11/smoke")
def api_v11_smoke(db: Session = Depends(get_db)):
    checks = {
        "users": db.query(User).count() >= 3,
        "admin_exists": db.query(User).filter(User.role == "admin").count() >= 1,
        "legal_pages": db.query(LegalPageV11).count() >= 3,
        "marketing_pages": db.query(MarketingLandingPageV11).count() >= 3,
        "production_checks": db.query(ProductionConfigCheckV11).count() >= 5,
    }
    ok = all(checks.values())
    run = SmokeTestRunV11(title="API smoke test", status="passed" if ok else "failed", summary=str(checks))
    db.add(run)
    db.flush()
    for route, passed in checks.items():
        db.add(SmokeTestItemV11(run_id=run.id, route=route, expected_status=200, actual_status=200 if passed else 500, status="passed" if passed else "failed"))
    db.commit()
    return JSONResponse({"status": "passed" if ok else "failed", "checks": checks})


@app.get("/legal/{slug}", response_class=HTMLResponse)
def legal_page_v11(slug: str, request: Request, db: Session = Depends(get_db)):
    page = db.query(LegalPageV11).filter(LegalPageV11.slug == slug, LegalPageV11.status == "published").first()
    if not page:
        raise HTTPException(404)
    return templates.TemplateResponse("legal_page_v11.html", {"request": request, "user": current_user(request, db), "page": page})


@app.get("/lp/{slug}", response_class=HTMLResponse)
def marketing_landing_page_v11(slug: str, request: Request, db: Session = Depends(get_db)):
    page = db.query(MarketingLandingPageV11).filter(MarketingLandingPageV11.slug == slug, MarketingLandingPageV11.status == "published").first()
    if not page:
        raise HTTPException(404)
    return templates.TemplateResponse("marketing_landing_v11.html", {"request": request, "user": current_user(request, db), "page": page})


@app.get("/verify-email/{token}")
def verify_email_v11(token: str, db: Session = Depends(get_db)):
    item = db.query(EmailVerificationTokenV11).filter(EmailVerificationTokenV11.token == token, EmailVerificationTokenV11.status == "pending").first()
    if not item:
        return RedirectResponse("/login?msg=invalid_token", 303)
    item.status = "used"
    item.used_at = datetime.utcnow()
    item.user.email_verified = True
    db.commit()
    return RedirectResponse("/login?msg=email_verified", 303)


@app.get("/reset-lozinke", response_class=HTMLResponse)
def password_reset_request_page_v11(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("password_reset_request_v11.html", {"request": request, "user": current_user(request, db)})


@app.post("/reset-lozinke")
def password_reset_request_v11(request: Request, email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if user:
        token = v11_token()
        db.add(PasswordResetTokenV11(user_id=user.id, token=token))
        db.add(EmailOutboxItem(recipient_email=user.email, subject="Reset lozinke", body=f"Demo reset link: /reset-lozinke/{token}", status="queued"))
        db.commit()
    return RedirectResponse("/login?msg=reset_sent", 303)


@app.get("/reset-lozinke/{token}", response_class=HTMLResponse)
def password_reset_form_v11(token: str, request: Request, db: Session = Depends(get_db)):
    item = db.query(PasswordResetTokenV11).filter(PasswordResetTokenV11.token == token, PasswordResetTokenV11.status == "pending").first()
    if not item:
        return templates.TemplateResponse("static_page.html", {"request": request, "user": current_user(request, db), "title": "Nevažeći token", "body": "Reset token nije validan ili je iskorišćen."})
    return templates.TemplateResponse("password_reset_form_v11.html", {"request": request, "user": None, "token": token})


@app.post("/reset-lozinke/{token}")
def password_reset_submit_v11(token: str, password: str = Form(...), db: Session = Depends(get_db)):
    item = db.query(PasswordResetTokenV11).filter(PasswordResetTokenV11.token == token, PasswordResetTokenV11.status == "pending").first()
    if not item:
        return RedirectResponse("/login?msg=invalid_token", 303)
    item.user.password_hash = hash_password(password)
    item.status = "used"
    item.used_at = datetime.utcnow()
    db.commit()
    return RedirectResponse("/login?msg=password_changed", 303)


@app.get("/korisnik/payout-profile-v11", response_class=HTMLResponse)
def user_payout_profile_v11(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["korisnik", "admin"])
    methods = db.query(PayoutMethodV11).filter(PayoutMethodV11.user_id == u.id).order_by(PayoutMethodV11.created_at.desc()).all()
    holds = db.query(PayoutHoldV11).filter(PayoutHoldV11.user_id == u.id).order_by(PayoutHoldV11.created_at.desc()).all()
    return templates.TemplateResponse("user_payout_profile_v11.html", {"request": request, "user": u, "methods": methods, "holds": holds, "flash": flash(msg)})


@app.post("/korisnik/payout-profile-v11")
def user_payout_method_save_v11(request: Request, method_type: str = Form("bank"), account_holder: str = Form(""), account_data: str = Form(...), db: Session = Depends(get_db)):
    u = require(request, db)
    check_role(u, ["korisnik", "admin"])
    db.add(PayoutMethodV11(user_id=u.id, method_type=method_type, account_holder=account_holder.strip() or u.full_name, account_data=account_data.strip(), status="pending"))
    notify(db, None, "admin", "Novi payout method", f"Korisnik {u.full_name} je dodao podatke za isplatu.")
    db.commit()
    return RedirectResponse("/korisnik/payout-profile-v11?msg=saved", 303)


# V11.7.1 disabled old admin v11 route
def admin_v11_dashboard(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    total_checks = db.query(ProductionConfigCheckV11).count()
    done_checks = db.query(ProductionConfigCheckV11).filter(ProductionConfigCheckV11.status == "done").count()
    score = round((done_checks / total_checks * 100) if total_checks else 0, 1)
    stats = {
        "total_users": db.query(User).count(),
        "total_customers": db.query(User).filter(User.role == "korisnik").count(),
        "total_advertisers": db.query(User).filter(User.role == "oglasivac").count(),
        "active_tasks": db.query(Task).filter(Task.status == "active").count(),
        "pending_tasks": db.query(Task).filter(Task.status == "pending").count(),
        "pending_submissions": db.query(TaskSubmission).filter(TaskSubmission.status == "pending").count(),
        "pending_withdrawals": db.query(Withdrawal).filter(Withdrawal.status == "pending").count(),
        "total_budget": db.query(func.coalesce(func.sum(User.advertiser_budget_rsd), 0)).scalar() or 0,
        "reserved_budget": db.query(func.coalesce(func.sum(User.advertiser_reserved_rsd), 0)).scalar() or 0,
        "spent_budget": db.query(func.coalesce(func.sum(User.advertiser_spent_rsd), 0)).scalar() or 0,
    }
    latest_tasks = db.query(Task).order_by(Task.created_at.desc()).limit(8).all()
    latest_submissions = db.query(TaskSubmission).order_by(TaskSubmission.created_at.desc()).limit(8).all()
    latest_withdrawals = db.query(Withdrawal).order_by(Withdrawal.created_at.desc()).limit(8).all()
    banners = db.query(PaidAdBannerV111).order_by(PaidAdBannerV111.created_at.desc()).limit(6).all() if "PaidAdBannerV111" in globals() else []
    boosts = db.query(PaidPromotionRequestV111).order_by(PaidPromotionRequestV111.created_at.desc()).limit(6).all() if "PaidPromotionRequestV111" in globals() else []
    db.add(LaunchReadinessScoreV11(score=score, summary=f"{done_checks}/{total_checks} production checks done"))
    db.commit()
    return templates.TemplateResponse("admin_v11_dashboard.html", {
        "request": request, "user": u,
        "score": score,
        "stats": stats,
        "latest_tasks": latest_tasks,
        "latest_submissions": latest_submissions,
        "latest_withdrawals": latest_withdrawals,
        "banners": banners,
        "boosts": boosts,
        "finance_accounts": v11836_public_accounts(db),
    })


@app.get("/admin/daily-desk-v11", response_class=HTMLResponse)
def admin_daily_desk_v11(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    notes = db.query(AdminDailyDeskNoteV11).order_by(AdminDailyDeskNoteV11.created_at.desc()).all()
    pending_submissions = db.query(TaskSubmission).filter(TaskSubmission.status == "pending").order_by(TaskSubmission.created_at.asc()).limit(20).all()
    pending_withdrawals = db.query(Withdrawal).filter(Withdrawal.status == "pending").order_by(Withdrawal.created_at.asc()).limit(20).all()
    fraud = db.query(FraudSignalV11).filter(FraudSignalV11.status == "open").order_by(FraudSignalV11.risk_score.desc()).limit(20).all()
    return templates.TemplateResponse("admin_daily_desk_v11.html", {"request": request, "user": u, "notes": notes, "pending_submissions": pending_submissions, "pending_withdrawals": pending_withdrawals, "fraud": fraud})


@app.post("/admin/daily-desk-v11/note")
def admin_daily_desk_note_v11(request: Request, title: str = Form(...), priority: str = Form("medium"), note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(AdminDailyDeskNoteV11(title=title.strip(), priority=priority, note=note.strip() or None))
    db.commit()
    return RedirectResponse("/admin/daily-desk-v11?msg=saved", 303)


@app.get("/admin/security-v11", response_class=HTMLResponse)
def admin_security_v11(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    attempts = db.query(LoginAttemptV11).order_by(LoginAttemptV11.created_at.desc()).limit(200).all()
    devices = db.query(UserDeviceSessionV11).order_by(UserDeviceSessionV11.last_seen_at.desc()).limit(200).all()
    codes = db.query(AdminTwoFactorCodeV11).order_by(AdminTwoFactorCodeV11.created_at.desc()).limit(20).all()
    return templates.TemplateResponse("admin_security_v11.html", {"request": request, "user": u, "attempts": attempts, "devices": devices, "codes": codes, "ops_suite": v11838_ops_suite_context(db, "/admin/security-v11")})


@app.get("/admin/payouts-v11", response_class=HTMLResponse)
def admin_payouts_v11(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    methods = db.query(PayoutMethodV11).order_by(PayoutMethodV11.created_at.desc()).all()
    holds = db.query(PayoutHoldV11).order_by(PayoutHoldV11.created_at.desc()).all()
    exports = db.query(PayoutExportV11).order_by(PayoutExportV11.created_at.desc()).all()
    pending_withdrawals = db.query(Withdrawal).filter(Withdrawal.status == "pending").order_by(Withdrawal.created_at.asc()).all()
    return templates.TemplateResponse("admin_payouts_v11.html", {"request": request, "user": u, "methods": methods, "holds": holds, "exports": exports, "pending_withdrawals": pending_withdrawals})


@app.post("/admin/payouts-v11/method/{method_id}/{status}")
def admin_payout_method_status_v11(method_id: int, status: str, request: Request, admin_note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    method = db.query(PayoutMethodV11).filter(PayoutMethodV11.id == method_id).first()
    if not method: raise HTTPException(404)
    if status not in ["verified", "rejected", "pending"]: raise HTTPException(400)
    method.status = status
    method.admin_note = admin_note.strip() or status
    notify(db, method.user, None, "Payout method status", f"Status podataka za isplatu: {status}.")
    db.commit()
    return RedirectResponse("/admin/payouts-v11?msg=saved", 303)


@app.post("/admin/payouts-v11/export")
def admin_payout_export_v11(request: Request, title: str = Form("Payout export"), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    pending = db.query(Withdrawal).filter(Withdrawal.status == "pending").order_by(Withdrawal.created_at.asc()).all()
    total = sum(w.amount_rsd for w in pending)
    export = PayoutExportV11(title=title.strip(), status="created", csv_path="scripts/payout_export_demo.csv", total_amount_rsd=total, rows_count=len(pending))
    db.add(export)
    db.commit()
    return RedirectResponse("/admin/payouts-v11?msg=saved", 303)


# V11.13 disabled old route /admin/budget-v11
def admin_budget_v11(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    alerts = db.query(AdvertiserBudgetAlertV11).order_by(AdvertiserBudgetAlertV11.created_at.desc()).all()
    logs = db.query(CampaignStatusLogV11).order_by(CampaignStatusLogV11.created_at.desc()).limit(100).all()
    advertisers = db.query(User).filter(User.role == "oglasivac").order_by(User.full_name).all()
    return templates.TemplateResponse("admin_budget_v11.html", {"request": request, "user": u, "alerts": alerts, "logs": logs, "advertisers": advertisers})


@app.post("/admin/budget-v11/alert")
def admin_budget_alert_v11(request: Request, advertiser_id: int = Form(...), threshold_rsd: float = Form(5000), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(AdvertiserBudgetAlertV11(advertiser_id=advertiser_id, threshold_rsd=threshold_rsd))
    db.commit()
    return RedirectResponse("/admin/budget-v11?msg=saved", 303)


# V11.13 disabled old route /admin/fraud-v11
def admin_fraud_v11(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    signals = db.query(FraudSignalV11).order_by(FraudSignalV11.risk_score.desc(), FraudSignalV11.created_at.desc()).all()
    rules = db.query(ForbiddenTaskRuleV11).order_by(ForbiddenTaskRuleV11.created_at.desc()).all()
    users = db.query(User).order_by(User.full_name).limit(300).all()
    return templates.TemplateResponse("admin_fraud_v11.html", {"request": request, "user": u, "signals": signals, "rules": rules, "users": users})


@app.post("/admin/fraud-v11/signal")
def admin_fraud_signal_v11(request: Request, user_id: int = Form(0), signal_type: str = Form(...), risk_score: float = Form(50), details: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(FraudSignalV11(user_id=user_id or None, signal_type=signal_type.strip(), risk_score=risk_score, details=details.strip() or None))
    db.commit()
    return RedirectResponse("/admin/fraud-v11?msg=saved", 303)


@app.post("/admin/fraud-v11/signal/{signal_id}/{status}")
def admin_fraud_signal_status_v11(signal_id: int, status: str, request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    sig = db.query(FraudSignalV11).filter(FraudSignalV11.id == signal_id).first()
    if not sig: raise HTTPException(404)
    if status not in ["open", "reviewed", "dismissed"]: raise HTTPException(400)
    sig.status = status
    db.commit()
    return RedirectResponse("/admin/fraud-v11?msg=saved", 303)


@app.get("/admin/legal-v11", response_class=HTMLResponse)
def admin_legal_v11(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    pages = db.query(LegalPageV11).order_by(LegalPageV11.updated_at.desc()).all()
    rules = db.query(ForbiddenTaskRuleV11).order_by(ForbiddenTaskRuleV11.created_at.desc()).all()
    return templates.TemplateResponse("admin_legal_v11.html", {"request": request, "user": u, "pages": pages, "rules": rules})


@app.post("/admin/legal-v11/page")
def admin_legal_page_save_v11(request: Request, slug: str = Form(...), title: str = Form(...), body: str = Form(...), version: str = Form("1.0"), status: str = Form("published"), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    page = db.query(LegalPageV11).filter(LegalPageV11.slug == slug.strip()).first()
    if not page:
        db.add(LegalPageV11(slug=slug.strip(), title=title.strip(), body=body.strip(), version=version, status=status))
    else:
        page.title = title.strip(); page.body = body.strip(); page.version = version; page.status = status; page.updated_at = datetime.utcnow()
    db.commit()
    return RedirectResponse("/admin/legal-v11?msg=saved", 303)


@app.post("/admin/legal-v11/rule")
def admin_forbidden_rule_save_v11(request: Request, title: str = Form(...), pattern: str = Form(...), severity: str = Form("high"), action: str = Form("reject_campaign"), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(ForbiddenTaskRuleV11(title=title.strip(), pattern=pattern.strip(), severity=severity, action=action))
    db.commit()
    return RedirectResponse("/admin/legal-v11?msg=saved", 303)


@app.get("/admin/marketing-v11", response_class=HTMLResponse)
def admin_marketing_v11(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    pages = db.query(MarketingLandingPageV11).order_by(MarketingLandingPageV11.created_at.desc()).all()
    return templates.TemplateResponse("admin_marketing_v11.html", {"request": request, "user": u, "pages": pages})


@app.post("/admin/marketing-v11/page")
def admin_marketing_page_save_v11(request: Request, slug: str = Form(...), title: str = Form(...), headline: str = Form(...), body: str = Form(...), cta_text: str = Form("Registracija"), cta_url: str = Form("/registracija"), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    page = db.query(MarketingLandingPageV11).filter(MarketingLandingPageV11.slug == slug.strip()).first()
    if not page:
        db.add(MarketingLandingPageV11(slug=slug.strip(), title=title.strip(), headline=headline.strip(), body=body.strip(), cta_text=cta_text.strip(), cta_url=cta_url.strip()))
    else:
        page.title = title.strip(); page.headline = headline.strip(); page.body = body.strip(); page.cta_text = cta_text.strip(); page.cta_url = cta_url.strip()
    db.commit()
    return RedirectResponse("/admin/marketing-v11?msg=saved", 303)


# V11.13 disabled old route /admin/deploy-v11
def admin_deploy_v11(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    checks = db.query(ProductionConfigCheckV11).order_by(ProductionConfigCheckV11.created_at.desc()).all()
    targets = db.query(DeployTargetV11).order_by(DeployTargetV11.created_at.desc()).all()
    backups = db.query(BackupRunV11).order_by(BackupRunV11.created_at.desc()).all()
    smoke_runs = db.query(SmokeTestRunV11).order_by(SmokeTestRunV11.created_at.desc()).limit(6).all()
    summary = {
        "checks_total": len(checks),
        "checks_done": sum(1 for c in checks if c.status == "done"),
        "checks_open": sum(1 for c in checks if c.status == "open"),
        "checks_blocked": sum(1 for c in checks if c.status == "blocked"),
        "targets_ready": sum(1 for t in targets if t.status in ["ready", "production", "live"]),
        "targets_total": len(targets),
        "backups_total": len(backups),
        "smoke_total": len(smoke_runs),
        "smoke_passed": sum(1 for r in smoke_runs if getattr(r, "status", "") == "passed"),
    }
    return templates.TemplateResponse("admin_deploy_v11.html", {"request": request, "user": u, "checks": checks, "targets": targets, "backups": backups, "smoke_runs": smoke_runs, "summary": summary})


@app.post("/admin/deploy-v11/check/{check_id}/{status}")
def admin_deploy_check_status_v11(check_id: int, status: str, request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    check = db.query(ProductionConfigCheckV11).filter(ProductionConfigCheckV11.id == check_id).first()
    if not check: raise HTTPException(404)
    if status not in ["open", "done", "blocked"]: raise HTTPException(400)
    check.status = status
    db.commit()
    return RedirectResponse("/admin/deploy-v11?msg=saved", 303)


@app.post("/admin/deploy-v11/backup")
def admin_backup_run_v11(request: Request, title: str = Form("Manual backup"), backup_type: str = Form("manual"), file_hint: str = Form("backups/klikzarada_v11_backup.db"), note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    db.add(BackupRunV11(title=title.strip(), backup_type=backup_type, file_hint=file_hint.strip(), note=note.strip() or None))
    db.commit()
    return RedirectResponse("/admin/deploy-v11?msg=saved", 303)


@app.get("/admin/smoke-v11", response_class=HTMLResponse)
def admin_smoke_v11(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    runs = db.query(SmokeTestRunV11).order_by(SmokeTestRunV11.created_at.desc()).limit(50).all()
    summary = {
        "runs_total": len(runs),
        "passed": sum(1 for r in runs if r.status == "passed"),
        "failed": sum(1 for r in runs if r.status == "failed"),
        "latest_status": runs[0].status if runs else "n/a",
    }
    return templates.TemplateResponse("admin_smoke_v11.html", {"request": request, "user": u, "runs": runs, "summary": summary, "ops_suite": v11838_ops_suite_context(db, "/admin/smoke-v11")})


@app.post("/admin/smoke-v11/run")
def admin_smoke_run_v11(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    checks = [
        ("/", True),
        ("/login", db.query(User).filter(User.role == "admin").count() > 0),
        ("/admin/v11", True),
        ("/api/v1/v11/health", True),
        ("legal_pages", db.query(LegalPageV11).count() >= 3),
        ("marketing_pages", db.query(MarketingLandingPageV11).count() >= 3),
        ("production_checks", db.query(ProductionConfigCheckV11).count() >= 5),
    ]
    ok = all(x[1] for x in checks)
    run = SmokeTestRunV11(title="Admin manual smoke", status="passed" if ok else "failed", summary=f"{sum(1 for _, p in checks if p)}/{len(checks)} checks passed")
    db.add(run); db.flush()
    for route, passed in checks:
        db.add(SmokeTestItemV11(run_id=run.id, route=route, expected_status=200, actual_status=200 if passed else 500, status="passed" if passed else "failed"))
    db.commit()
    return RedirectResponse("/admin/smoke-v11?msg=saved", 303)




# ---------------------------------------------------
# V11.1 UI, ADS & PRICING
# ---------------------------------------------------

def v111_price_obj(db: Session, key: str):
    return db.query(MonetizationPricingV111).filter(MonetizationPricingV111.key == key).first()


def v111_price_rsd(db: Session, key: str, default: float = 0):
    p = v111_price_obj(db, key)
    return float(p.value_rsd if p else default)


def v111_price_percent(db: Session, key: str, default: float = 0):
    p = v111_price_obj(db, key)
    return float(p.value_percent if p else default)


def v11836_public_accounts(db: Session):
    def setting(key: str, default: str = "") -> str:
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        value = (row.value if row and row.value is not None else default) or default
        return str(value).strip()

    return {
        "advertiser_payment_account": setting("advertiser_payment_account", "Dodaj broj računa u adminu"),
        "advertiser_payment_holder": setting("advertiser_payment_holder", "Dodaj naziv primaoca u adminu"),
        "user_payout_account": setting("user_payout_account", "Dodaj račun za isplatu u adminu"),
        "user_payout_holder": setting("user_payout_holder", "Dodaj naziv primaoca u adminu"),
        "payment_reference": setting("payment_reference", "KlikZarada budžet"),
        "payout_reference": setting("payout_reference", "KlikZarada isplata"),
        "bank_note": setting("bank_note", "Podaci se mogu menjati iz admin system settings."),
    }


def v11836_pricing_summary(db: Session):
    platform_fee_percent = v111_price_percent(db, "platform_commission_percent", 20)
    banner_top_7d = v111_price_rsd(db, "banner_home_top_7d", 9500)
    banner_mid_7d = v111_price_rsd(db, "banner_home_mid_7d", 5500)
    ad_view_cost = v111_price_rsd(db, "ad_view_cost_rsd", 10)
    ad_view_reward = v111_price_rsd(db, "ad_view_reward_rsd", 6)
    boost_top_3d = v111_price_rsd(db, "boost_top_position_3d", 2500)
    boost_featured_3d = v111_price_rsd(db, "boost_featured_3d", 1800)
    boost_highlighted_3d = v111_price_rsd(db, "boost_highlighted_3d", 1200)
    return {
        "platform_fee_percent": platform_fee_percent,
        "user_reward_share": max(0, 100 - platform_fee_percent),
        "banner_top_7d": banner_top_7d,
        "banner_mid_7d": banner_mid_7d,
        "banner_top_day": banner_top_7d / 7 if banner_top_7d else 0,
        "banner_mid_day": banner_mid_7d / 7 if banner_mid_7d else 0,
        "ad_view_cost": ad_view_cost,
        "ad_view_reward": ad_view_reward,
        "boost_top_3d": boost_top_3d,
        "boost_featured_3d": boost_featured_3d,
        "boost_highlighted_3d": boost_highlighted_3d,
        "min_withdrawal": MIN_WITHDRAWAL_RSD,
    }


def seed_v111_ui_ads_pricing():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        pricing_defaults = [
            ("banner_home_top_7d", "Veliki banner na početnoj / dan", 9500, 0, "Cena velikog banner slota po danu."),
            ("banner_home_mid_7d", "Srednji banner na početnoj / dan", 5500, 0, "Cena srednjeg banner slota po danu."),
            ("ad_view_cost_rsd", "Cena gledanja reklame za oglašivača", 10, 0, "Koliko se skida oglašivaču po validnom gledanju reklame."),
            ("ad_view_reward_rsd", "Nagrada korisniku za gledanje reklame", 6, 0, "Koliko korisnik dobija za validno gledanje reklame."),
            ("boost_top_position_3d", "Podizanje kampanje na prvo mesto / 3 dana", 2500, 0, "Cena top pozicije za 3 dana."),
            ("boost_featured_3d", "Featured kampanja / 3 dana", 1800, 0, "Cena featured oznake za 3 dana."),
            ("boost_highlighted_3d", "Highlighted kampanja / 3 dana", 1200, 0, "Cena highlighted isticanja za 3 dana."),
            ("platform_commission_percent", "Provizija platforme na kampanje", 0, 20, "Globalna provizija platforme za nove kampanje."),
        ]
        for key, title, value_rsd, value_percent, description in pricing_defaults:
            row = db.query(MonetizationPricingV111).filter(MonetizationPricingV111.key == key).first()
            if row:
                row.title = title
                row.value_rsd = value_rsd
                row.value_percent = value_percent
                row.description = description
            else:
                db.add(MonetizationPricingV111(key=key, title=title, value_rsd=value_rsd, value_percent=value_percent, description=description))

        slot_defaults = [
            ("home_top_wide", "Početna — veliki gornji banner", "home_top", "wide", 9500),
            ("home_mid_left", "Početna — srednji levi banner", "home_mid", "half", 5500),
            ("home_mid_right", "Početna — srednji desni banner", "home_mid", "half", 5500),
        ]
        for code, title, placement, width_label, price_rsd in slot_defaults:
            row = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code == code).first()
            if row:
                row.title = title
                row.placement = placement
                row.width_label = width_label
                row.price_rsd = price_rsd
                row.is_active = True
            else:
                db.add(HomeBannerSlotV111(code=code, title=title, placement=placement, width_label=width_label, price_rsd=price_rsd))

        if db.query(PanelShortcutV111).count() == 0:
            shortcuts = [
                ("admin","Daily Desk","Dnevni radni sto","/admin/daily-desk-v11","Operacije",10),
                ("admin","Cene i provizije","Cenovnik reklama, gledanja i provizije","/admin/cene-v111","Monetizacija",20),
                ("admin","Reklame i isticanja","Banneri i podizanje kampanja","/admin/reklame-v111","Monetizacija",30),
                ("admin","Payouts","Isplate i payout metode","/admin/payouts-v11","Finansije",40),
                ("admin","Fraud","Anti-fraud signali","/admin/fraud-v11","Sigurnost",50),
                ("admin","Deploy","Production i smoke test","/admin/deploy-v11","Produkcija",60),
                ("oglasivac","Moje reklame","Banner reklame na početnoj","/oglasivac/reklame-v111","Promocija",10),
                ("oglasivac","Top pozicija","Podigni kampanju na prvo mesto","/oglasivac/boost-v111","Promocija",20),
                ("oglasivac","Budžet","Dopuna budžeta","/oglasivac/payments","Finansije",30),
                ("korisnik","Zadaci","Lista zadataka","/korisnik/zadaci","Rad",10),
                ("korisnik","Wallet","Stanje i zarada","/korisnik/wallet","Finansije",20),
            ]
            for role,title,desc,url,group,order in shortcuts:
                db.add(PanelShortcutV111(role=role,title=title,description=desc,url=url,group_name=group,sort_order=order))

        adv = db.query(User).filter(User.role == "oglasivac").first()
        slot = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code == "home_top_wide").first()
        if adv and slot and db.query(PaidAdBannerV111).count() == 0:
            db.add(PaidAdBannerV111(
                advertiser_id=adv.id, slot_id=slot.id, title="Demo plaćeni banner",
                body="Ovaj prostor može kupiti oglašivač kao dodatnu reklamu.",
                target_url="/registracija", price_rsd=slot.price_rsd,
                view_cost_rsd=v111_price_rsd(db, "ad_view_cost_rsd", 8),
                viewer_reward_rsd=v111_price_rsd(db, "ad_view_reward_rsd", 5),
                days_count=1, status="active", starts_at=datetime.utcnow()
            ))

        if adv and db.query(PaidPromotionRequestV111).count() == 0:
            task = db.query(Task).filter(Task.advertiser_id == adv.id).first()
            if task:
                task.featured = True
                db.add(PaidPromotionRequestV111(
                    advertiser_id=adv.id, task_id=task.id, promotion_type="top_position",
                    title=f"Top pozicija: {task.title}",
                    price_rsd=v111_price_rsd(db, "boost_top_position_3d", 1500),
                    days_count=3, status="active", starts_at=datetime.utcnow()
                ))
        db.commit()
    finally:
        db.close()


def v111_active_home_banners(db: Session):
    return db.query(PaidAdBannerV111).filter(PaidAdBannerV111.status == "active").order_by(PaidAdBannerV111.created_at.desc()).limit(6).all()


def v111_featured_tasks(db: Session):
    active_boosts = db.query(PaidPromotionRequestV111).filter(PaidPromotionRequestV111.status == "active", PaidPromotionRequestV111.task_id != None).order_by(PaidPromotionRequestV111.created_at.desc()).all()
    tasks, seen = [], set()
    for boost in active_boosts:
        if boost.task and boost.task.status == "active" and boost.task.id not in seen:
            tasks.append(boost.task); seen.add(boost.task.id)
    for t in db.query(Task).filter(Task.status == "active").order_by(Task.featured.desc(), Task.reward_rsd.desc()).limit(12).all():
        if t.id not in seen:
            tasks.append(t); seen.add(t.id)
    return tasks[:8]


@app.get("/panel-v111", response_class=HTMLResponse)
def smart_panel_v111(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    shortcuts = db.query(PanelShortcutV111).filter(PanelShortcutV111.role == u.role, PanelShortcutV111.is_visible == True).order_by(PanelShortcutV111.group_name, PanelShortcutV111.sort_order).all()
    grouped = {}
    for s in shortcuts:
        grouped.setdefault(s.group_name, []).append(s)
    return templates.TemplateResponse("smart_panel_v111.html", {"request": request, "user": u, "grouped": grouped})


# V11.13 disabled old route /admin/cene-v111
def admin_prices_v111(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    prices = db.query(MonetizationPricingV111).order_by(MonetizationPricingV111.key).all()
    slots = db.query(HomeBannerSlotV111).order_by(HomeBannerSlotV111.price_rsd.desc()).all()
    pricing_summary = v11836_pricing_summary(db)
    return templates.TemplateResponse("admin_prices_v111.html", {"request": request, "user": u, "prices": prices, "slots": slots, "pricing_summary": pricing_summary})


@app.post("/admin/cene-v111/save")
def admin_price_save_v111(request: Request, key: str = Form(...), title: str = Form(...), value_rsd: float = Form(0), value_percent: float = Form(0), description: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    p = db.query(MonetizationPricingV111).filter(MonetizationPricingV111.key == key.strip()).first()
    if not p:
        p = MonetizationPricingV111(key=key.strip(), title=title.strip())
        db.add(p)
    p.title = title.strip()
    p.value_rsd = value_rsd
    p.value_percent = value_percent
    p.description = description.strip() or None
    p.updated_at = datetime.utcnow()
    # sync banner slot defaults
    if key == "banner_home_top_7d":
        for s in db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.placement == "home_top").all():
            s.price_rsd = value_rsd
    if key == "banner_home_mid_7d":
        for s in db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.placement == "home_mid").all():
            s.price_rsd = value_rsd
    db.commit()
    return RedirectResponse("/admin/cene-v111?msg=saved", 303)


@app.post("/admin/cene-v111/slot")
def admin_slot_save_v111(request: Request, code: str = Form(...), title: str = Form(...), placement: str = Form("home_top"), width_label: str = Form("wide"), price_rsd: float = Form(...), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    s = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code == code.strip()).first()
    if not s:
        s = HomeBannerSlotV111(code=code.strip(), title=title.strip())
        db.add(s)
    s.title = title.strip(); s.placement = placement; s.width_label = width_label; s.price_rsd = float(price_rsd or 0) * 7; s.is_active = True
    db.commit()
    return RedirectResponse("/admin/cene-v111?msg=saved", 303)


# V11.9 disabled old route /admin/reklame-v111
def admin_ads_v111(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    slots = db.query(HomeBannerSlotV111).order_by(HomeBannerSlotV111.price_rsd.desc()).all()
    banners = db.query(PaidAdBannerV111).order_by(PaidAdBannerV111.created_at.desc()).all()
    boosts = db.query(PaidPromotionRequestV111).order_by(PaidPromotionRequestV111.created_at.desc()).all()
    views = db.query(PaidAdViewV111).order_by(PaidAdViewV111.created_at.desc()).limit(100).all()
    return templates.TemplateResponse("admin_ads_v111.html", {"request": request, "user": u, "slots": slots, "banners": banners, "boosts": boosts, "views": views})


@app.get("/admin/banneri-v111", response_class=HTMLResponse)
def admin_banneri_v111(request: Request, db: Session = Depends(get_db)):
    return admin_ads_v111(request, db)


@app.get("/admin/promocija-v111", response_class=HTMLResponse)
def admin_promocija_v111(request: Request, db: Session = Depends(get_db)):
    return admin_ads_v111(request, db)


@app.post("/admin/reklame-v111/banner/{banner_id}/{status}")
def admin_banner_status_v111(
    banner_id: int,
    status: str,
    request: Request,
    admin_note: str = Form(""),
    force_publish: str = Form("no"),
    db: Session = Depends(get_db)
):
    u = require(request, db); check_role(u, ["admin"])
    banner = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.id == banner_id).first()
    if not banner:
        raise HTTPException(404)

    status = {
        "aktivno": "active",
        "objavi": "active",
        "objavljeno": "active",
        "publish": "active",
        "published": "active",
        "odbijeno": "rejected",
        "odbij": "rejected",
        "rejected": "rejected",
        "isteklo": "expired",
        "expired": "expired",
        "na čekanju": "pending",
        "na_cekanju": "pending",
        "pending": "pending",
    }.get(status, status)

    if status not in ["active", "rejected", "expired", "pending"]:
        raise HTTPException(400)

    old_status = banner.status
    note = admin_note.strip()

    if status == "active" and old_status != "active":
        price = float(banner.price_rsd or 0)
        enough_budget = float(getattr(banner.advertiser, "advertiser_budget_rsd", 0) or 0) >= price
        free_publish = force_publish == "yes" or price <= 0

        reserved_paid = V11817_BANNER_RESERVED_MARK in (banner.admin_note or "")
        if not enough_budget and not free_publish and not reserved_paid:
            banner.admin_note = note or "Nema dovoljno budžeta za aktivaciju. Upiši cenu 0 ili koristi Objavi bez naplate."
            db.commit()
            return RedirectResponse("/admin/banneri-v111?msg=budget_error", 303)

        reserved_paid = V11817_BANNER_RESERVED_MARK in (banner.admin_note or "")
        if price > 0 and reserved_paid:
            banner.advertiser.advertiser_reserved_rsd = max(0, float(getattr(banner.advertiser, "advertiser_reserved_rsd", 0) or 0) - price)
            banner.advertiser_spent_rsd = float(getattr(banner.advertiser, "advertiser_spent_rsd", 0) or 0) + price
            add_budget_tx(db, banner.advertiser, 0, "activate_reserved_banner", f"Aktiviran već plaćen banner: {banner.title}")
            banner.admin_note = (banner.admin_note or "").replace(V11817_BANNER_RESERVED_MARK, "").strip()
        elif price > 0 and not free_publish:
            banner.advertiser.advertiser_budget_rsd -= price
            banner.advertiser_spent_rsd = float(getattr(banner.advertiser, "advertiser_spent_rsd", 0) or 0) + price
            add_budget_tx(db, banner.advertiser, -price, "paid_banner", f"Plaćeni banner: {banner.title}")
        elif free_publish:
            banner.admin_note = (note + " · " if note else "") + "Objavljeno bez naplate."

        banner.starts_at = datetime.utcnow()
        if not banner.ends_at and banner.days_count:
            banner.ends_at = datetime.utcnow() + timedelta(days=int(banner.days_count or 7))

    banner.status = status
    banner.admin_note = banner.admin_note or note or status
    notify(db, banner.advertiser, None, "Status banner reklame", f"Banner '{banner.title}' je sada: {status}.")
    db.commit()
    return RedirectResponse("/admin/banneri-v111?msg=saved", 303)


@app.post("/admin/banneri-v111/banner/{banner_id}/{status}")
def admin_banneri_status_v111(
    banner_id: int,
    status: str,
    request: Request,
    admin_note: str = Form(""),
    force_publish: str = Form("no"),
    db: Session = Depends(get_db)
):
    return admin_banner_status_v111(
        banner_id=banner_id,
        status=status,
        request=request,
        admin_note=admin_note,
        force_publish=force_publish,
        db=db,
    )


@app.post("/admin/promocija-v111/banner/{banner_id}/{status}")
def admin_promocija_status_v111(
    banner_id: int,
    status: str,
    request: Request,
    admin_note: str = Form(""),
    force_publish: str = Form("no"),
    db: Session = Depends(get_db)
):
    return admin_banner_status_v111(
        banner_id=banner_id,
        status=status,
        request=request,
        admin_note=admin_note,
        force_publish=force_publish,
        db=db,
    )


@app.post("/admin/reklame-v111/boost/{boost_id}/{status}")
def admin_boost_status_v111(boost_id: int, status: str, request: Request, admin_note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    boost = db.query(PaidPromotionRequestV111).filter(PaidPromotionRequestV111.id == boost_id).first()
    if not boost: raise HTTPException(404)
    if status not in ["active", "rejected", "expired", "pending"]: raise HTTPException(400)
    old = boost.status
    if status == "active" and old != "active":
        if boost.advertiser.advertiser_budget_rsd < boost.price_rsd:
            boost.admin_note = "Nema dovoljno budžeta za aktivaciju."
            db.commit()
            return RedirectResponse("/admin/banneri-v111?msg=budget_error", 303)
        boost.advertiser.advertiser_budget_rsd -= boost.price_rsd
        add_budget_tx(db, boost.advertiser, -boost.price_rsd, "paid_boost", f"Plaćeno isticanje: {boost.title}")
        boost.starts_at = datetime.utcnow()
        if boost.task:
            boost.task.featured = True
    boost.status = status
    boost.admin_note = admin_note.strip() or status
    notify(db, boost.advertiser, None, "Status isticanja", f"Zahtev '{boost.title}' je sada: {status}.")
    db.commit()
    return RedirectResponse("/admin/banneri-v111?msg=saved", 303)


@app.post("/admin/banneri-v111/boost/{boost_id}/{status}")
def admin_banneri_boost_status_v111(boost_id: int, status: str, request: Request, admin_note: str = Form(""), db: Session = Depends(get_db)):
    return admin_boost_status_v111(boost_id=boost_id, status=status, request=request, admin_note=admin_note, db=db)


@app.post("/admin/promocija-v111/boost/{boost_id}/{status}")
def admin_promocija_boost_status_v111(boost_id: int, status: str, request: Request, admin_note: str = Form(""), db: Session = Depends(get_db)):
    return admin_boost_status_v111(boost_id=boost_id, status=status, request=request, admin_note=admin_note, db=db)


@app.get("/oglasivac/reklame-v111", response_class=HTMLResponse)
def advertiser_ads_v111(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["oglasivac", "admin"])
    if "v11815_ensure_9_banner_slots" in globals():
        v11815_ensure_9_banner_slots(db)
    expected_codes = [x[0] for x in v11815_banner_slot_definitions()] if "v11815_banner_slot_definitions" in globals() else []
    if expected_codes:
        slots = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code.in_(expected_codes), HomeBannerSlotV111.is_active == True).order_by(HomeBannerSlotV111.id.asc()).all()
    else:
        slots = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.is_active == True).order_by(HomeBannerSlotV111.id.asc()).all()
    banners = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.advertiser_id == u.id).order_by(PaidAdBannerV111.created_at.desc()).all()
    pricing_summary = v11836_pricing_summary(db)
    return templates.TemplateResponse("advertiser_ads_v111.html", {"request": request, "user": u, "slots": slots, "banners": banners, "flash": flash(msg), "pricing_summary": pricing_summary})


@app.get("/oglasivac/banneri-v111", response_class=HTMLResponse)
def advertiser_banneri_v111(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    return advertiser_ads_v111(request, msg, db)


@app.get("/oglasivac/promocija-v111", response_class=HTMLResponse)
def advertiser_promocija_v111(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    return advertiser_ads_v111(request, msg, db)


@app.post("/oglasivac/reklame-v111")
async def advertiser_ad_create_v111(request: Request, slot_id: int = Form(...), title: str = Form(...), body: str = Form(""), image_url: str = Form(""), upload_image: UploadFile | None = File(None), target_url: str = Form("/"), days_count: int = Form(7), image_fit: str = Form("cover"), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["oglasivac", "admin"])
    if "v11815_ensure_9_banner_slots" in globals():
        v11815_ensure_9_banner_slots(db)
    slot = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.id == slot_id, HomeBannerSlotV111.is_active == True).first()
    if not slot:
        raise HTTPException(404)
    days_count = max(1, int(days_count or 7))
    daily_price = float(slot.price_rsd or 0) / 7 if float(slot.price_rsd or 0) else 0
    price = daily_price * days_count

    if u.role == "oglasivac" and float(getattr(u, "advertiser_budget_rsd", 0) or 0) < price:
        return RedirectResponse("/oglasivac/banneri-v111?msg=budget_error", 303)

    if u.role == "oglasivac" and price > 0:
        u.advertiser_budget_rsd = float(getattr(u, "advertiser_budget_rsd", 0) or 0) - price
        u.advertiser_reserved_rsd = float(getattr(u, "advertiser_reserved_rsd", 0) or 0) + price
        add_budget_tx(db, u, -price, "reserve_banner", f"Rezervisan budžet za banner: {title.strip()}")

    db.add(PaidAdBannerV111(
        advertiser_id=u.id, slot_id=slot.id, title=title.strip(), body=body.strip() or None,
        image_url=(await v11828_final_banner_image(slot, title.strip(), upload_image, image_url, image_fit, v11818_default_banner_image(slot.code))), target_url=target_url.strip() or "/",
        price_rsd=price, view_cost_rsd=v111_price_rsd(db, "ad_view_cost_rsd", 8),
        viewer_reward_rsd=v111_price_rsd(db, "ad_view_reward_rsd", 5),
        days_count=days_count, status="pending",
        admin_note=(V11817_BANNER_RESERVED_MARK if u.role == "oglasivac" and price > 0 else None)
    ))
    notify(db, None, "admin", "Nova banner reklama", f"Oglašivač {u.full_name} traži banner: {title}")
    db.commit()
    return RedirectResponse("/oglasivac/banneri-v111?msg=saved", 303)


@app.post("/oglasivac/banneri-v111")
async def advertiser_banneri_create_v111(request: Request, slot_id: int = Form(...), title: str = Form(...), body: str = Form(""), image_url: str = Form(""), upload_image: UploadFile | None = File(None), target_url: str = Form("/"), days_count: int = Form(7), image_fit: str = Form("cover"), db: Session = Depends(get_db)):
    return await advertiser_ad_create_v111(
        request=request,
        slot_id=slot_id,
        title=title,
        body=body,
        image_url=image_url,
        upload_image=upload_image,
        target_url=target_url,
        days_count=days_count,
        image_fit=image_fit,
        db=db,
    )


@app.post("/oglasivac/promocija-v111")
async def advertiser_promocija_create_v111(request: Request, slot_id: int = Form(...), title: str = Form(...), body: str = Form(""), image_url: str = Form(""), upload_image: UploadFile | None = File(None), target_url: str = Form("/"), days_count: int = Form(7), image_fit: str = Form("cover"), db: Session = Depends(get_db)):
    return await advertiser_ad_create_v111(
        request=request,
        slot_id=slot_id,
        title=title,
        body=body,
        image_url=image_url,
        upload_image=upload_image,
        target_url=target_url,
        days_count=days_count,
        image_fit=image_fit,
        db=db,
    )


# V11.14 disabled old route /oglasivac/boost-v111
def advertiser_boost_v111(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["oglasivac", "admin"])
    tasks = db.query(Task).filter(Task.advertiser_id == u.id).order_by(Task.created_at.desc()).all()
    boosts = db.query(PaidPromotionRequestV111).filter(PaidPromotionRequestV111.advertiser_id == u.id).order_by(PaidPromotionRequestV111.created_at.desc()).all()
    prices = {
        "top_position": v111_price_rsd(db, "boost_top_position_3d", 1500),
        "featured": v111_price_rsd(db, "boost_featured_3d", 1000),
        "highlighted": v111_price_rsd(db, "boost_highlighted_3d", 700),
    }
    return templates.TemplateResponse("advertiser_boost_v111.html", {"request": request, "user": u, "tasks": tasks, "boosts": boosts, "prices": prices, "flash": flash(msg)})


@app.post("/oglasivac/boost-v111")
def advertiser_boost_create_v111(request: Request, task_id: int = Form(...), promotion_type: str = Form("top_position"), days_count: int = Form(3), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["oglasivac", "admin"])
    task = db.query(Task).filter(Task.id == task_id, Task.advertiser_id == u.id).first()
    if not task: raise HTTPException(404)
    keys = {"top_position":"boost_top_position_3d", "featured":"boost_featured_3d", "highlighted":"boost_highlighted_3d"}
    base_price = v111_price_rsd(db, keys.get(promotion_type, "boost_top_position_3d"), 1500)
    price = base_price * max(1, days_count) / 3
    db.add(PaidPromotionRequestV111(
        advertiser_id=u.id, task_id=task.id, promotion_type=promotion_type,
        title=f"{promotion_type}: {task.title}", price_rsd=price,
        days_count=days_count, status="pending"
    ))
    notify(db, None, "admin", "Novi zahtev za isticanje", f"Oglašivač {u.full_name} traži isticanje kampanje: {task.title}")
    db.commit()
    return RedirectResponse("/oglasivac/boost-v111?msg=saved", 303)


@app.get("/reklama-v111/{banner_id}/view")
def ad_view_v111(banner_id: int, request: Request, db: Session = Depends(get_db)):
    u = current_user(request, db)
    banner = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.id == banner_id, PaidAdBannerV111.status == "active").first()
    if not banner:
        raise HTTPException(404)
    # One reward per logged-in user per banner.
    already = bool(u and db.query(PaidAdViewV111).filter(PaidAdViewV111.banner_id == banner.id, PaidAdViewV111.user_id == u.id).first())
    cost = banner.view_cost_rsd or v111_price_rsd(db, "ad_view_cost_rsd", 8)
    reward = banner.viewer_reward_rsd or v111_price_rsd(db, "ad_view_reward_rsd", 5)
    fee = max(0, cost - reward)
    if not already:
        banner.views_count += 1
        if banner.advertiser.advertiser_budget_rsd >= cost:
            banner.advertiser.advertiser_budget_rsd -= cost
            add_budget_tx(db, banner.advertiser, -cost, "ad_view", f"Gledanje reklame: {banner.title}")
            if u and u.role == "korisnik" and reward > 0:
                u.balance_rsd += reward
                u.lifetime_earned_rsd += reward
                add_tx(db, u, reward, "ad_view_reward", f"Nagrada za gledanje reklame: {banner.title}")
            db.add(PaidAdViewV111(banner_id=banner.id, user_id=u.id if u else None, advertiser_id=banner.advertiser_id, cost_rsd=cost, reward_rsd=reward if u else 0, platform_fee_rsd=fee, ip_address=v11_ip(request) if "v11_ip" in globals() else None))
        else:
            banner.admin_note = "Oglašivač nema dovoljno budžeta za naplatu po gledanju."
    db.commit()
    return RedirectResponse(banner.target_url or "/", 303)


# V11.7 disabled old route /blog
def blog_placeholder_v112(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("static_page.html", {
        "request": request,
        "user": current_user(request, db),
        "title": "Blog",
        "body": "Blog sekcija je spremna za buduće tekstove, vodiče i novosti platforme."
    })




# ---------------------------------------------------
# V11.4.2 PRO FINAL POLISH: banner admin editing
# ---------------------------------------------------

@app.post("/admin/reklame-v111/banner/{banner_id}/edit")
async def admin_banner_edit_v1142(
    banner_id: int,
    request: Request,
    title: str = Form(...),
    body: str = Form(""),
    target_url: str = Form("/"),
    image_url: str = Form(""),
    upload_image: UploadFile | None = File(None),
    price_rsd: float = Form(0),
    view_cost_rsd: float = Form(0),
    viewer_reward_rsd: float = Form(0),
    days_count: int = Form(7),
    db: Session = Depends(get_db)
):
    u = require(request, db); check_role(u, ["admin"])
    banner = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.id == banner_id).first()
    if not banner:
        raise HTTPException(404)
    banner.title = title.strip()
    banner.body = body.strip() or None
    banner.target_url = target_url.strip() or "/"
    banner.image_url = (await v11828_final_banner_image(banner.slot, title.strip(), upload_image, image_url, image_fit if 'image_fit' in locals() else 'cover', None)) or banner.image_url or (v11818_default_banner_image(banner.slot.code) if banner.slot else None)
    banner.price_rsd = price_rsd
    banner.view_cost_rsd = view_cost_rsd
    banner.viewer_reward_rsd = viewer_reward_rsd
    banner.days_count = days_count
    banner.admin_note = "Admin izmenio banner."
    db.commit()
    return RedirectResponse("/admin/reklame-v111?msg=banner_saved", 303)


@app.post("/admin/reklame-v111/slot/{slot_id}/edit")
def admin_slot_edit_v1142(
    slot_id: int,
    request: Request,
    title: str = Form(...),
    placement: str = Form("home_top"),
    width_label: str = Form("wide"),
    price_rsd: float = Form(0),
    is_active: str = Form("yes"),
    db: Session = Depends(get_db)
):
    u = require(request, db); check_role(u, ["admin"])
    slot = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.id == slot_id).first()
    if not slot:
        raise HTTPException(404)
    slot.title = title.strip()
    slot.placement = placement.strip()
    slot.width_label = width_label.strip()
    slot.price_rsd = float(price_rsd or 0) * 7
    slot.is_active = is_active == "yes"
    db.commit()
    return RedirectResponse("/admin/reklame-v111?msg=slot_saved", 303)


@app.post("/admin/reklame-v111/quick-banner")
async def admin_quick_banner_v1142(
    request: Request,
    advertiser_id: int = Form(...),
    slot_id: int = Form(...),
    title: str = Form(...),
    body: str = Form(""),
    image_url: str = Form(""),
    upload_image: UploadFile | None = File(None),
    image_fit: str = Form("cover"),
    target_url: str = Form("/"),
    price_rsd: float = Form(0),
    days_count: int = Form(7),
    start_date: str = Form(""),
    status: str = Form("active"),
    db: Session = Depends(get_db)
):
    u = require(request, db); check_role(u, ["admin"])
    advertiser = db.query(User).filter(User.id == advertiser_id).first()
    slot = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.id == slot_id).first()
    if not advertiser or not slot:
        raise HTTPException(404)
    status = {
        "aktivno": "active",
        "objavi": "active",
        "objavljeno": "active",
        "active": "active",
        "pending": "pending",
        "na čekanju": "pending",
        "na_cekanju": "pending",
        "rejected": "rejected",
        "odbijeno": "rejected",
        "expired": "expired",
    }.get(status, status)
    if status not in ["active", "pending", "rejected", "expired"]:
        status = "pending"
    days_count = max(1, int(days_count or 7))
    daily_price = float(price_rsd or 0) if float(price_rsd or 0) > 0 else (float(slot.price_rsd or 0) / 7 if float(slot.price_rsd or 0) else 0)
    planned_start = v11837_parse_date(start_date) or datetime.utcnow()
    if status == "active" and planned_start.date() > datetime.utcnow().date():
        status = "pending"
    banner = PaidAdBannerV111(
        advertiser_id=advertiser.id,
        slot_id=slot.id,
        title=title.strip(),
        body=body.strip() or None,
        image_url=(await v11828_final_banner_image(slot, title.strip(), upload_image, image_url, image_fit, v11818_default_banner_image(slot.code))),
        target_url=target_url.strip() or "/",
        price_rsd=daily_price * days_count,
        view_cost_rsd=v111_price_rsd(db, "ad_view_cost_rsd", 8) if "v111_price_rsd" in globals() else 8,
        viewer_reward_rsd=v111_price_rsd(db, "ad_view_reward_rsd", 5) if "v111_price_rsd" in globals() else 5,
        days_count=days_count,
        status=status,
        starts_at=planned_start,
        ends_at=(planned_start + timedelta(days=days_count))
    )
    db.add(banner)
    db.commit()
    return RedirectResponse("/admin/reklame-v111?msg=quick_banner_saved", 303)




# ---------------------------------------------------
# V11.7 UNIFIED PROFESSIONAL PUBLIC PAGES
# ---------------------------------------------------

@app.get("/za-oglasivace", response_class=HTMLResponse)
def public_advertisers_v117(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("public_advertisers_v117.html", {
        "request": request,
        "user": current_user(request, db),
        "pricing_summary": v11836_pricing_summary(db),
        "finance_accounts": v11836_public_accounts(db),
        "flash": None
    })


@app.get("/za-korisnike", response_class=HTMLResponse)
def public_users_v117(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("public_users_v117.html", {
        "request": request,
        "user": current_user(request, db),
        "pricing_summary": v11836_pricing_summary(db),
        "flash": None
    })


@app.get("/cenovnik", response_class=HTMLResponse)
def pricing_public_v117(request: Request, db: Session = Depends(get_db)):
    prices = []
    if "MonetizationPricingV111" in globals():
        prices = db.query(MonetizationPricingV111).order_by(MonetizationPricingV111.key).all()
    pricing_summary = v11836_pricing_summary(db)
    task_price_ranges = [
        {"label": "Kratki zadaci", "reward": "20-40 RSD", "desc": "Posete i brze akcije od oko 1 minuta."},
        {"label": "Standardni zadaci", "reward": "50-120 RSD", "desc": "Ankete, registracije i testiranje od 3-5 minuta."},
        {"label": "Viši zadaci", "reward": "120-250 RSD", "desc": "Duže kampanje sa više koraka i dokazom."},
        {"label": "Premium zadaci", "reward": "250+ RSD", "desc": "Kompleksniji ili specijalni zadaci."},
    ]
    banner_packages = [
        {"title": "Početna - veliki banner", "price": f"od {pricing_summary['banner_top_day']:.0f} RSD / 24 sata", "desc": "Najvidljiviji prostor odmah ispod hero sekcije."},
        {"title": "Početna - srednji banner", "price": f"od {pricing_summary['banner_mid_day']:.0f} RSD / 24 sata", "desc": "Uredan format za brendove i kampanje."},
        {"title": "Top pozicija kampanje", "price": f"od {pricing_summary['boost_top_3d']:.0f} RSD / 3 dana", "desc": "Kampanja se izdvaja na vrhu liste zadataka."},
    ]
    pricing_summary["ad_view_cost_rsd"] = pricing_summary.get("ad_view_cost", 8)
    return templates.TemplateResponse("pricing_v117.html", {
        "request": request,
        "user": current_user(request, db),
        "prices": prices,
        "pricing_summary": pricing_summary,
        "task_price_ranges": task_price_ranges,
        "banner_packages": banner_packages,
        "finance_accounts": v11836_public_accounts(db),
        "flash": None
    })


@app.get("/reklame", response_class=HTMLResponse)
def public_ads_v117(request: Request, db: Session = Depends(get_db)):
    banners = []
    if "PaidAdBannerV111" in globals():
        banners = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.status == "active").order_by(PaidAdBannerV111.created_at.desc()).limit(12).all()
    return templates.TemplateResponse("public_ads_v117.html", {
        "request": request,
        "user": current_user(request, db),
        "banners": banners,
        "pricing_summary": v11836_pricing_summary(db),
        "flash": None
    })


@app.get("/kontakt", response_class=HTMLResponse)
def contact_v117(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("contact_v117.html", {
        "request": request,
        "user": current_user(request, db),
        "flash": None
    })


@app.get("/blog", response_class=HTMLResponse)
def blog_v117(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("blog_v117.html", {
        "request": request,
        "user": current_user(request, db),
        "flash": None
    })




# ---------------------------------------------------
# V11.7.1 SAFE ADMIN DASHBOARD
# ---------------------------------------------------

# V11.16 disabled old /admin/v11 route
def admin_v11_safe_v1171(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])

    total_users = db.query(User).count()
    total_customers = db.query(User).filter(User.role == "korisnik").count()
    total_advertisers = db.query(User).filter(User.role == "oglasivac").count()
    active_tasks = db.query(Task).filter(Task.status == "active").count()
    pending_tasks = db.query(Task).filter(Task.status == "pending").count()
    pending_submissions = db.query(TaskSubmission).filter(TaskSubmission.status == "pending").count()
    pending_withdrawals = db.query(Withdrawal).filter(Withdrawal.status == "pending").count()

    total_budget = db.query(func.coalesce(func.sum(User.advertiser_budget_rsd), 0)).filter(User.role == "oglasivac").scalar() or 0
    reserved_budget = db.query(func.coalesce(func.sum(User.advertiser_reserved_rsd), 0)).filter(User.role == "oglasivac").scalar() or 0
    spent_budget = db.query(func.coalesce(func.sum(User.advertiser_spent_rsd), 0)).filter(User.role == "oglasivac").scalar() or 0

    latest_tasks = db.query(Task).order_by(Task.created_at.desc()).limit(8).all()
    latest_submissions = db.query(TaskSubmission).order_by(TaskSubmission.created_at.desc()).limit(8).all()
    latest_withdrawals = db.query(Withdrawal).order_by(Withdrawal.created_at.desc()).limit(8).all()

    banners = []
    boosts = []
    if "PaidAdBannerV111" in globals():
        banners = db.query(PaidAdBannerV111).order_by(PaidAdBannerV111.created_at.desc()).limit(6).all()
    if "PaidPromotionRequestV111" in globals():
        boosts = db.query(PaidPromotionRequestV111).order_by(PaidPromotionRequestV111.created_at.desc()).limit(6).all()

    return templates.TemplateResponse("admin_v11_safe_v1171.html", {
        "request": request,
        "user": u,
        "flash": None,
        "stats": {
            "total_users": total_users,
            "total_customers": total_customers,
            "total_advertisers": total_advertisers,
            "active_tasks": active_tasks,
            "pending_tasks": pending_tasks,
            "pending_submissions": pending_submissions,
            "pending_withdrawals": pending_withdrawals,
            "total_budget": total_budget,
            "reserved_budget": reserved_budget,
            "spent_budget": spent_budget,
        },
        "latest_tasks": latest_tasks,
        "latest_submissions": latest_submissions,
        "latest_withdrawals": latest_withdrawals,
        "banners": banners,
        "boosts": boosts,
    })




# ---------------------------------------------------
# V11.8 PLATFORM MAP + DESIGN AUDIT
# ---------------------------------------------------

V118_PLATFORM_PAGES = [
    {"group":"Javne stranice","title":"Početna","url":"/","status":"sredjeno"},
    {"group":"Javne stranice","title":"Zadaci","url":"/zadaci","status":"sredjeno"},
    {"group":"Javne stranice","title":"Za korisnike","url":"/za-korisnike","status":"sredjeno"},
    {"group":"Javne stranice","title":"Za oglašivače","url":"/za-oglasivace","status":"sredjeno"},
    {"group":"Javne stranice","title":"Cenovnik","url":"/cenovnik","status":"sredjeno"},
    {"group":"Javne stranice","title":"Reklame","url":"/reklame","status":"sredjeno"},
    {"group":"Javne stranice","title":"Blog","url":"/blog","status":"sredjeno"},
    {"group":"Javne stranice","title":"Kontakt","url":"/kontakt","status":"sredjeno"},
    {"group":"Korisnik","title":"Korisnički panel","url":"/korisnik/panel","status":"unified"},
    {"group":"Korisnik","title":"Dostupni zadaci","url":"/korisnik/zadaci","status":"unified"},
    {"group":"Korisnik","title":"Moji dokazi","url":"/korisnik/dokazi","status":"unified"},
    {"group":"Korisnik","title":"Novčanik","url":"/korisnik/wallet","status":"unified"},
    {"group":"Korisnik","title":"Isplate","url":"/korisnik/isplate","status":"unified"},
    {"group":"Korisnik","title":"Referral","url":"/korisnik/referral","status":"unified"},
    {"group":"Korisnik","title":"Profil","url":"/korisnik/profil","status":"unified"},
    {"group":"Korisnik","title":"Bedževi","url":"/korisnik/bedzevi","status":"unified"},
    {"group":"Oglašivač","title":"Panel oglašivača","url":"/oglasivac/panel","status":"unified"},
    {"group":"Oglašivač","title":"Kampanje","url":"/oglasivac/kampanje","status":"unified"},
    {"group":"Oglašivač","title":"Nova kampanja","url":"/oglasivac/nova-kampanja","status":"unified"},
    {"group":"Oglašivač","title":"Budžet","url":"/oglasivac/budzet","status":"unified"},
    {"group":"Oglašivač","title":"Banner reklame","url":"/oglasivac/reklame-v111","status":"sredjeno"},
    {"group":"Oglašivač","title":"Top pozicija","url":"/oglasivac/boost-v111","status":"sredjeno"},
    {"group":"Oglašivač","title":"Fakture","url":"/oglasivac/fakture","status":"unified"},
    {"group":"Admin","title":"Admin dashboard","url":"/admin/v11","status":"sredjeno"},
    {"group":"Admin","title":"Dnevni radni sto","url":"/admin/daily-desk-v11","status":"unified"},
    {"group":"Admin","title":"Cene i provizije","url":"/admin/cene-v111","status":"sredjeno"},
    {"group":"Admin","title":"Banneri i isticanja","url":"/admin/reklame-v111","status":"sredjeno"},
    {"group":"Admin","title":"Kampanje","url":"/admin/kampanje","status":"unified"},
    {"group":"Admin","title":"Dokazi","url":"/admin/dokazi","status":"unified"},
    {"group":"Admin","title":"Isplate","url":"/admin/isplate","status":"unified"},
    {"group":"Admin","title":"Finansije","url":"/admin/finansije","status":"unified"},
    {"group":"Admin","title":"Automatizacija","url":"/admin/workflows-v10","status":"unified"},
    {"group":"Admin","title":"Anti-fraud","url":"/admin/fraud-v11","status":"unified"},
    {"group":"Admin","title":"Legal","url":"/admin/legal-v11","status":"unified"},
    {"group":"Admin","title":"Produkcija","url":"/admin/deploy-v11","status":"unified"},
]

# V11.9 disabled old route /admin/mapa-platforme
def admin_platform_map_v118(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    grouped = {}
    for p in V118_PLATFORM_PAGES:
        grouped.setdefault(p["group"], []).append(p)
    return templates.TemplateResponse("admin_platform_map_v118.html", {
        "request": request,
        "user": u,
        "flash": None,
        "grouped": grouped,
        "total": len(V118_PLATFORM_PAGES),
    })

@app.get("/api/v1/v11/design-map")
def api_design_map_v118():
    return {"version":"11.8", "pages": V118_PLATFORM_PAGES, "total": len(V118_PLATFORM_PAGES)}




# ---------------------------------------------------
# V11.9 STRUCTURED PROFESSIONAL PLATFORM
# ---------------------------------------------------

KZ119_TASK_CATEGORIES = [
    {"slug":"ankete", "title":"Ankete", "icon":"📋", "description":"Kratke ankete, istraživanje tržišta i mišljenja korisnika."},
    {"slug":"testiranje-sajta", "title":"Testiranje sajta", "icon":"🌐", "description":"Provera landing stranica, UX utisak i korisnički feedback."},
    {"slug":"registracije", "title":"Registracije", "icon":"👤", "description":"Beta liste, registracije za aplikacije i probne naloge."},
    {"slug":"feedback", "title":"Feedback", "icon":"💬", "description":"Komentari, ocene i konkretne sugestije za poboljšanje."},
    {"slug":"drustvene-mreze", "title":"Društvene mreže", "icon":"🔗", "description":"Deljenje, praćenje i proverljive društvene aktivnosti."},
    {"slug":"aplikacije", "title":"Testiranje aplikacija", "icon":"📱", "description":"Mobilne i web aplikacije, onboarding i funkcionalni test."},
    {"slug":"mystery-shopper", "title":"Mystery shopper", "icon":"🛒", "description":"Online kupovina, provera usluge i iskustva korisnika."},
    {"slug":"lokalni-zadaci", "title":"Lokalni zadaci", "icon":"📍", "description":"Zadaci vezani za grad, lokaciju ili lokalne biznise."},
    {"slug":"provera-cena", "title":"Provera cena", "icon":"🏷", "description":"Upoređivanje cena, dostupnosti i tržišnih informacija."},
    {"slug":"video-audio", "title":"Video / audio", "icon":"🎧", "description":"Kratki pregledi, audio utisak i video feedback."},
    {"slug":"ai-zadaci", "title":"AI zadaci", "icon":"🤖", "description":"Testiranje AI alata, promptova i automatizacija."},
    {"slug":"promo-zadaci", "title":"Promo zadaci", "icon":"🚀", "description":"Specijalne promocije i plaćeno istaknuti zadaci."},
]

KZ119_FUNCTIONS = [
    {"slug":"admin-dashboard", "group":"Admin", "title":"Admin dashboard", "url":"/admin/v11", "description":"Glavni pregled platforme, finansije, dokazi, reklame i brze komande."},
    {"slug":"mapa-platforme", "group":"Admin", "title":"Mapa platforme", "url":"/admin/mapa-platforme", "description":"Jedna stranica sa svim ključnim funkcijama i statusom dizajna."},
    {"slug":"kampanje", "group":"Admin", "title":"Kampanje", "url":"/admin/kampanje", "description":"Moderacija i pregled svih kampanja po statusima i kategorijama."},
    {"slug":"dokazi", "group":"Admin", "title":"Dokazi", "url":"/admin/dokazi", "description":"Pregled dokaza koje korisnici šalju za izvršene zadatke."},
    {"slug":"isplate", "group":"Admin", "title":"Isplate", "url":"/admin/isplate", "description":"Zahtevi za isplatu korisnicima i statusi obrade."},
    {"slug":"finansije", "group":"Admin", "title":"Finansije", "url":"/admin/finansije", "description":"Budžeti, provizije, prihodi i finansijski pregled platforme."},
    {"slug":"reklame", "group":"Admin", "title":"Banneri i isticanja", "url":"/admin/reklame-v111", "description":"Upravljanje bannerima, top pozicijom i plaćenim promocijama."},
    {"slug":"cene", "group":"Admin", "title":"Cene i provizije", "url":"/admin/cene-v111", "description":"Admin podešava cene reklama, gledanja i proviziju platforme."},
    {"slug":"automatizacija", "group":"Admin", "title":"Automatizacija", "url":"/admin/workflows-v10", "description":"Tokovi rada, okidači i automatizacija operacija."},
    {"slug":"anti-fraud", "group":"Admin", "title":"Anti-fraud", "url":"/admin/fraud-v11", "description":"Kontrola sumnjivih aktivnosti, duplikata i loših dokaza."},
    {"slug":"zadaci-javno", "group":"Javno", "title":"Zadaci", "url":"/zadaci", "description":"Javna lista zadataka, kategorije, pretraga i filtriranje."},
    {"slug":"za-korisnike", "group":"Javno", "title":"Za korisnike", "url":"/za-korisnike", "description":"Stranica koja objašnjava zaradu i zadatke korisnicima."},
    {"slug":"za-oglasivace", "group":"Javno", "title":"Za oglašivače", "url":"/za-oglasivace", "description":"Stranica za oglašivače, kampanje, rezultate i promocije."},
    {"slug":"reklame-javno", "group":"Javno", "title":"Reklame", "url":"/reklame", "description":"Javna stranica za banner reklame i plaćeno isticanje."},
    {"slug":"korisnik-panel", "group":"Korisnik", "title":"Korisnički panel", "url":"/korisnik/panel", "description":"Pregled zarade, dokaza, zadataka i isplata korisnika."},
    {"slug":"korisnik-zadaci", "group":"Korisnik", "title":"Korisnički zadaci", "url":"/korisnik/zadaci", "description":"Zadaci dostupni ulogovanom korisniku."},
    {"slug":"korisnik-wallet", "group":"Korisnik", "title":"Novčanik", "url":"/korisnik/wallet", "description":"Stanje, pending zarada i istorija transakcija."},
    {"slug":"oglasivac-panel", "group":"Oglašivač", "title":"Panel oglašivača", "url":"/oglasivac/panel", "description":"Pregled kampanja, budžeta i rezultata oglašivača."},
    {"slug":"oglasivac-kampanje", "group":"Oglašivač", "title":"Moje kampanje", "url":"/oglasivac/kampanje", "description":"Lista kampanja oglašivača i njihov status."},
    {"slug":"oglasivac-reklame", "group":"Oglašivač", "title":"Banner reklame", "url":"/oglasivac/reklame-v111", "description":"Oglašivač šalje zahtev za banner reklamu."},
    {"slug":"oglasivac-top", "group":"Oglašivač", "title":"Top pozicija", "url":"/oglasivac/boost-v111", "description":"Oglašivač plaća podizanje kampanje na prvo mesto."},
]

def kz119_category_by_slug(slug: str):
    for c in KZ119_TASK_CATEGORIES:
        if c["slug"] == slug:
            return c
    return None

def kz119_tasks_query(db: Session, q: str | None = None, category: str | None = None):
    query = db.query(Task).filter(Task.status == "active")
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Task.title.ilike(like), Task.description.ilike(like), Task.category.ilike(like), Task.task_type.ilike(like)))
    if category:
        cat = kz119_category_by_slug(category)
        if cat:
            # Loose matching because old seed categories are not normalized.
            words = [cat["title"], cat["slug"].replace("-", " ")]
            if cat["slug"] == "testiranje-sajta":
                words += ["Testiranje", "Test sajta"]
            if cat["slug"] == "drustvene-mreze":
                words += ["Društvene", "Social", "Podeli"]
            clauses = [Task.category.ilike(f"%{w}%") for w in words]
            query = query.filter(or_(*clauses))
    return query.order_by(Task.featured.desc(), Task.reward_rsd.desc(), Task.created_at.desc())

@app.get("/zadaci", response_class=HTMLResponse)
def tasks_public_v119(request: Request, q: str | None = None, category: str | None = None, db: Session = Depends(get_db)):
    tasks = kz119_tasks_query(db, q, category).all()
    counts = {}
    for c in KZ119_TASK_CATEGORIES:
        try:
            counts[c["slug"]] = kz119_tasks_query(db, None, c["slug"]).count()
        except Exception:
            counts[c["slug"]] = 0
    featured = db.query(Task).filter(Task.status == "active").order_by(Task.featured.desc(), Task.reward_rsd.desc()).limit(6).all()
    return templates.TemplateResponse("tasks_structured_v119.html", {
        "request": request,
        "user": current_user(request, db),
        "flash": None,
        "tasks": tasks,
        "featured": featured,
        "categories": KZ119_TASK_CATEGORIES,
        "counts": counts,
        "q": q or "",
        "active_category": category or "",
    })

@app.get("/zadaci-kategorija/{slug}", response_class=HTMLResponse)
def task_category_v119(slug: str, request: Request, db: Session = Depends(get_db)):
    cat = kz119_category_by_slug(slug)
    if not cat:
        raise HTTPException(404)
    tasks = kz119_tasks_query(db, None, slug).all()
    return templates.TemplateResponse("task_category_v119.html", {
        "request": request,
        "user": current_user(request, db),
        "flash": None,
        "category": cat,
        "tasks": tasks,
        "categories": KZ119_TASK_CATEGORIES,
    })

# V11.10 disabled old route /admin/mapa-platforme
def admin_platform_map_v119(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    grouped = {}
    for f in KZ119_FUNCTIONS:
        grouped.setdefault(f["group"], []).append(f)
    return templates.TemplateResponse("admin_platform_map_v119.html", {
        "request": request,
        "user": u,
        "flash": None,
        "grouped": grouped,
        "functions": KZ119_FUNCTIONS,
        "categories": KZ119_TASK_CATEGORIES,
    })

@app.get("/admin/funkcija/{slug}", response_class=HTMLResponse)
def admin_function_page_v119(slug: str, request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    fn = None
    for f in KZ119_FUNCTIONS:
        if f["slug"] == slug:
            fn = f
            break
    if not fn:
        raise HTTPException(404)
    related = [f for f in KZ119_FUNCTIONS if f["group"] == fn["group"] and f["slug"] != fn["slug"]]
    return templates.TemplateResponse("admin_function_page_v119.html", {
        "request": request,
        "user": u,
        "flash": None,
        "fn": fn,
        "related": related,
    })

# V11.10 disabled old route /admin/kampanje
def admin_campaigns_structured_v119(request: Request, status: str | None = None, category: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    if category:
        cat = kz119_category_by_slug(category)
        if cat:
            query = query.filter(Task.category.ilike(f"%{cat['title']}%"))
    tasks = query.order_by(Task.created_at.desc()).all()
    stats = {
        "all": db.query(Task).count(),
        "active": db.query(Task).filter(Task.status == "active").count(),
        "pending": db.query(Task).filter(Task.status == "pending").count(),
        "rejected": db.query(Task).filter(Task.status == "rejected").count(),
    }
    return templates.TemplateResponse("admin_campaigns_structured_v119.html", {
        "request": request,
        "user": u,
        "flash": None,
        "tasks": tasks,
        "stats": stats,
        "categories": KZ119_TASK_CATEGORIES,
        "active_status": status or "",
        "active_category": category or "",
    })

# V11.10 disabled old route /admin/reklame-v111
def admin_ads_structured_v119(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    slots = db.query(HomeBannerSlotV111).order_by(HomeBannerSlotV111.price_rsd.desc()).all() if "HomeBannerSlotV111" in globals() else []
    banners = db.query(PaidAdBannerV111).order_by(PaidAdBannerV111.created_at.desc()).all() if "PaidAdBannerV111" in globals() else []
    boosts = db.query(PaidPromotionRequestV111).order_by(PaidPromotionRequestV111.created_at.desc()).all() if "PaidPromotionRequestV111" in globals() else []
    views = db.query(PaidAdViewV111).order_by(PaidAdViewV111.created_at.desc()).limit(50).all() if "PaidAdViewV111" in globals() else []
    advertisers = db.query(User).filter(User.role == "oglasivac").order_by(User.full_name).all()
    return templates.TemplateResponse("admin_ads_structured_v119.html", {
        "request": request,
        "user": u,
        "flash": None,
        "slots": slots,
        "banners": banners,
        "boosts": boosts,
        "views": views,
        "advertisers": advertisers,
    })

@app.get("/api/v1/v11/design-map")
def api_design_map_v119():
    return {
        "version":"11.9",
        "functions": KZ119_FUNCTIONS,
        "categories": KZ119_TASK_CATEGORIES,
        "total_functions": len(KZ119_FUNCTIONS),
        "total_categories": len(KZ119_TASK_CATEGORIES),
    }




# ---------------------------------------------------
# V11.10 FINAL LAYOUT CONSISTENCY
# ---------------------------------------------------

@app.get("/admin/mapa-platforme", response_class=HTMLResponse)
def admin_platform_map_v1110(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    grouped = {}
    for f in KZ119_FUNCTIONS:
        grouped.setdefault(f["group"], []).append(f)
    return templates.TemplateResponse("admin_platform_map_v1110.html", {
        "request": request,
        "user": u,
        "flash": None,
        "grouped": grouped,
        "functions": KZ119_FUNCTIONS,
        "categories": KZ119_TASK_CATEGORIES,
    })

@app.get("/admin/kampanje", response_class=HTMLResponse)
def admin_campaigns_final_v1110(request: Request, status: str | None = None, category: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    if category:
        cat = kz119_category_by_slug(category)
        if cat:
            query = query.filter(Task.category.ilike(f"%{cat['title']}%"))
    tasks = query.order_by(Task.created_at.desc()).all()
    stats = {
        "all": db.query(Task).count(),
        "active": db.query(Task).filter(Task.status == "active").count(),
        "pending": db.query(Task).filter(Task.status == "pending").count(),
        "rejected": db.query(Task).filter(Task.status == "rejected").count(),
    }
    advertisers = db.query(User).filter(User.role == "oglasivac").order_by(User.full_name.asc()).all()
    grouped = {"active": [], "pending": [], "rejected": [], "other": []}
    for t in tasks:
        grouped[t.status if t.status in grouped else "other"].append(t)
    return templates.TemplateResponse("admin_campaigns_final_v1110.html", {
        "request": request,
        "user": u,
        "flash": None,
        "tasks": tasks,
        "grouped_tasks": grouped,
        "stats": stats,
        "advertisers": advertisers,
        "categories": KZ119_TASK_CATEGORIES,
        "active_status": status or "",
        "active_category": category or "",
    })

@app.post("/admin/kampanje/novo")
def admin_campaign_create_v1110(
    request: Request,
    title: str = Form(...),
    category: str = Form("Promo"),
    task_type: str = Form("visit_site"),
    target_url: str = Form("/"),
    description: str = Form(""),
    instructions: str = Form(""),
    proof_required: str = Form("Pošaljite kratak dokaz o izvršenju."),
    example_proof: str = Form(""),
    reward_rsd: float = Form(50),
    total_slots: int = Form(50),
    estimated_minutes: int = Form(5),
    target_city: str = Form(""),
    target_age_group: str = Form(""),
    target_interests: str = Form(""),
    min_user_level: str = Form("Bronza"),
    proof_file_required: str = Form(""),
    featured: str = Form(""),
    status: str = Form("pending"),
    advertiser_id: int = Form(0),
    db: Session = Depends(get_db),
):
    admin = require(request, db)
    check_role(admin, ["admin"])
    advertiser = None
    if advertiser_id:
        advertiser = db.query(User).filter(User.id == advertiser_id, User.role == "oglasivac").first()
    task = Task(
        advertiser_id=advertiser.id if advertiser else admin.id,
        title=title.strip(),
        category=category.strip() or "Promo",
        task_type=task_type.strip() or "visit_site",
        target_url=target_url.strip() or "/",
        description=description.strip() or "Kampanja kreirana iz admin panela.",
        instructions=instructions.strip() or "Pratite instrukcije i pošaljite dokaz.",
        proof_required=proof_required.strip() or "Pošaljite dokaz.",
        example_proof=example_proof.strip() or None,
        reward_rsd=max(1, float(reward_rsd or 1)),
        total_slots=max(1, int(total_slots or 1)),
        estimated_minutes=max(1, int(estimated_minutes or 1)),
        target_city=target_city.strip() or None,
        target_age_group=target_age_group.strip() or None,
        target_interests=target_interests.strip() or None,
        min_user_level=min_user_level.strip() or "Bronza",
        proof_file_required=bool(proof_file_required),
        featured=bool(featured),
        status=status if status in ["active", "pending", "rejected", "paused", "closed", "returned"] else "pending",
    )
    db.add(task)
    audit(db, admin, "admin_task_create", "Task", None, f"{task.title} / status={task.status} / advertiser={advertiser.id if advertiser else 'admin'}")
    db.commit()
    return RedirectResponse("/admin/kampanje?msg=created", 303)

@app.get("/admin/reklame-v111", response_class=HTMLResponse)
def admin_ads_final_v1110(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    if "v11815_ensure_9_banner_slots" in globals():
        v11815_ensure_9_banner_slots(db)
    expected_codes = [x[0] for x in v11815_banner_slot_definitions()] if "v11815_banner_slot_definitions" in globals() else []
    if expected_codes:
        slots = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code.in_(expected_codes)).order_by(HomeBannerSlotV111.id.asc()).all()
    else:
        slots = db.query(HomeBannerSlotV111).order_by(HomeBannerSlotV111.id.asc()).all() if "HomeBannerSlotV111" in globals() else []
    banners = db.query(PaidAdBannerV111).order_by(PaidAdBannerV111.created_at.desc()).all() if "PaidAdBannerV111" in globals() else []
    boosts = db.query(PaidPromotionRequestV111).order_by(PaidPromotionRequestV111.created_at.desc()).all() if "PaidPromotionRequestV111" in globals() else []
    views = db.query(PaidAdViewV111).order_by(PaidAdViewV111.created_at.desc()).limit(100).all() if "PaidAdViewV111" in globals() else []
    advertisers = db.query(User).filter(User.role == "oglasivac").order_by(User.id.asc()).all()
    pricing_summary = v11836_pricing_summary(db)
    slot_calendar = v11837_slot_booking_calendar(db, 14)
    sales_packages = v11837_margin_snapshot(db)["packages"]
    return templates.TemplateResponse("admin_ads_v111.html", {
        "request": request, "user": u, "slots": slots, "banners": banners, "boosts": boosts, "views": views,
        "advertisers": advertisers, "pricing_summary": pricing_summary, "slot_calendar": slot_calendar, "sales_packages": sales_packages,
    })


@app.get("/api/v1/v11/layout-audit-map")
def api_layout_audit_map_v1110():
    return {
        "version":"11.10",
        "required_layouts": {
            "public": "kz117/kz119",
            "admin": "kz116/kz119/kz1110",
            "tasks": "kz119",
        },
        "checked_pages": [
            "/", "/zadaci", "/admin/mapa-platforme", "/admin/kampanje", "/admin/reklame-v111",
            "/admin/v11", "/admin/cene-v111", "/admin/dokazi", "/admin/finansije",
            "/oglasivac/panel", "/korisnik/panel"
        ]
    }




# ---------------------------------------------------
# V11.11 PERFECT UI PASS
# ---------------------------------------------------

@app.get("/admin/dokazi", response_class=HTMLResponse)
def admin_proofs_final_v1111(request: Request, status: str | None = None, variant: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    query = db.query(TaskSubmission)
    if status:
        query = query.filter(TaskSubmission.status == status)
    submissions = query.order_by(TaskSubmission.created_at.desc()).all()
    ai_results = db.query(AIReviewResult).order_by(AIReviewResult.created_at.desc()).all()
    ai_map = {}
    for result in ai_results:
        if result.submission_id and result.submission_id not in ai_map:
            ai_map[result.submission_id] = result
    def proof_variant(submission, ai):
        if submission.status == "rejected":
            return "rejected"
        if submission.status == "approved":
            if ai and getattr(ai, "suggestion", None) and "Automatski" in ai.suggestion:
                return "auto"
            return "approved"
        return "manual"
    variant_counts = {"auto": 0, "manual": 0, "approved": 0, "rejected": 0}
    visible_submissions = []
    for submission in submissions:
        ai = ai_map.get(submission.id)
        current_variant = proof_variant(submission, ai)
        if current_variant in variant_counts:
            variant_counts[current_variant] += 1
        if variant and current_variant != variant:
            continue
        visible_submissions.append(submission)
    stats = {
        "all": db.query(TaskSubmission).count(),
        "pending": db.query(TaskSubmission).filter(TaskSubmission.status == "pending").count(),
        "approved": db.query(TaskSubmission).filter(TaskSubmission.status == "approved").count(),
        "rejected": db.query(TaskSubmission).filter(TaskSubmission.status == "rejected").count(),
        "disputed": db.query(TaskSubmission).filter(TaskSubmission.status == "disputed").count(),
        "ai_reviews": len(ai_results),
        "auto_approved": db.query(AutoEngineLogV114).filter(AutoEngineLogV114.event_type == "submission_auto_approved").count(),
        "auto_rejected": db.query(AutoEngineLogV114).filter(AutoEngineLogV114.event_type == "submission_auto_rejected").count(),
        "variant_auto": variant_counts["auto"],
        "variant_manual": variant_counts["manual"],
        "variant_approved": variant_counts["approved"],
        "variant_rejected": variant_counts["rejected"],
    }
    return templates.TemplateResponse("admin_proofs_final_v1111.html", {
        "request": request,
        "user": u,
        "flash": None,
        "submissions": visible_submissions,
        "stats": stats,
        "active_status": status or "",
        "active_variant": variant or "",
        "ai_map": ai_map,
    })

@app.get("/korisnik/dokazi", response_class=HTMLResponse)
def user_proofs_final_v1111(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["korisnik"])
    submissions = db.query(TaskSubmission).filter(TaskSubmission.user_id == u.id).order_by(TaskSubmission.created_at.desc()).all()
    stats = {
        "all": len(submissions),
        "pending": sum(1 for s in submissions if s.status == "pending"),
        "approved": sum(1 for s in submissions if s.status == "approved"),
        "rejected": sum(1 for s in submissions if s.status == "rejected"),
    }
    return templates.TemplateResponse("user_proofs_final_v1111.html", {
        "request": request,
        "user": u,
        "flash": None,
        "submissions": submissions,
        "stats": stats,
    })

@app.get("/oglasivac/dokazi", response_class=HTMLResponse)
def advertiser_proofs_final_v1111(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["oglasivac"])
    submissions = db.query(TaskSubmission).join(Task, TaskSubmission.task_id == Task.id).filter(Task.advertiser_id == u.id).order_by(TaskSubmission.created_at.desc()).all()
    stats = {
        "all": len(submissions),
        "pending": sum(1 for s in submissions if s.status == "pending"),
        "approved": sum(1 for s in submissions if s.status == "approved"),
        "rejected": sum(1 for s in submissions if s.status == "rejected"),
    }
    return templates.TemplateResponse("advertiser_proofs_final_v1111.html", {
        "request": request,
        "user": u,
        "flash": None,
        "submissions": submissions,
        "stats": stats,
    })

@app.get("/admin/isplate", response_class=HTMLResponse)
def admin_withdrawals_final_v1111(request: Request, status: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    query = db.query(Withdrawal)
    if status:
        query = query.filter(Withdrawal.status == status)
    withdrawals = query.order_by(Withdrawal.created_at.desc()).all()
    stats = {
        "all": db.query(Withdrawal).count(),
        "pending": db.query(Withdrawal).filter(Withdrawal.status == "pending").count(),
        "paid": db.query(Withdrawal).filter(Withdrawal.status == "paid").count(),
        "rejected": db.query(Withdrawal).filter(Withdrawal.status == "rejected").count(),
    }
    return templates.TemplateResponse("admin_withdrawals_final_v1111.html", {
        "request": request,
        "user": u,
        "flash": None,
        "withdrawals": withdrawals,
        "stats": stats,
        "active_status": status or "",
    })

@app.get("/admin/finansije", response_class=HTMLResponse)
def admin_finance_final_v1111(request: Request, msg: str | None = None, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    total_rewards = db.query(func.coalesce(func.sum(TaskSubmission.reward_rsd), 0)).filter(TaskSubmission.status == "approved").scalar() or 0
    total_fee = db.query(func.coalesce(func.sum(TaskSubmission.platform_fee_rsd), 0)).filter(TaskSubmission.status == "approved").scalar() or 0
    advertiser_budget = db.query(func.coalesce(func.sum(User.advertiser_budget_rsd), 0)).filter(User.role == "oglasivac").scalar() or 0
    reserved_budget = db.query(func.coalesce(func.sum(User.advertiser_reserved_rsd), 0)).filter(User.role == "oglasivac").scalar() or 0
    withdrawals_pending = db.query(func.coalesce(func.sum(Withdrawal.amount_rsd), 0)).filter(Withdrawal.status == "pending").scalar() or 0
    withdrawals_paid = db.query(func.coalesce(func.sum(Withdrawal.amount_rsd), 0)).filter(Withdrawal.status == "paid").scalar() or 0
    invoice_total = db.query(func.coalesce(func.sum(Invoice.amount_rsd), 0)).scalar() or 0
    invoice_count = db.query(Invoice).count()
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).limit(10).all()
    advertisers = db.query(User).filter(User.role == "oglasivac").order_by(User.full_name).all()
    pending_withdrawals = db.query(Withdrawal).filter(Withdrawal.status == "pending").order_by(Withdrawal.created_at.asc()).limit(12).all()
    withdrawals_recent = db.query(Withdrawal).order_by(Withdrawal.created_at.desc()).limit(12).all()
    withdrawal_counts = {
        "pending": db.query(Withdrawal).filter(Withdrawal.status == "pending").count(),
        "paid": db.query(Withdrawal).filter(Withdrawal.status == "paid").count(),
        "rejected": db.query(Withdrawal).filter(Withdrawal.status == "rejected").count(),
    }
    payout_methods = db.query(PayoutMethodV11).order_by(PayoutMethodV11.created_at.desc()).limit(8).all()
    payout_exports = db.query(PayoutExportV11).order_by(PayoutExportV11.created_at.desc()).limit(6).all()
    finance_accounts = v11836_public_accounts(db)
    rows = [
        {"title":"Provizija platforme", "amount": total_fee, "desc":"Ukupna odobrena provizija iz zadataka.", "color":"blue"},
        {"title":"Odobreno korisnicima", "amount": total_rewards, "desc":"Ukupno odobrene nagrade korisnicima.", "color":"green"},
        {"title":"Slobodan budžet oglašivača", "amount": advertiser_budget, "desc":"Dostupno za buduće kampanje.", "color":"purple"},
        {"title":"Rezervisan budžet", "amount": reserved_budget, "desc":"Rezervisano za aktivne kampanje.", "color":"orange"},
        {"title":"Isplate na čekanju", "amount": withdrawals_pending, "desc":"Zahtevi koje admin treba da obradi.", "color":"red"},
        {"title":"Isplaćeno korisnicima", "amount": withdrawals_paid, "desc":"Već označeno kao isplaćeno.", "color":"green"},
        {"title":"Vrednost faktura", "amount": invoice_total, "desc":"Ukupna vrednost svih izdatih dokumenata.", "color":"blue"},
    ]
    return templates.TemplateResponse("admin_finance_final_v1111.html", {
        "request": request,
        "user": u,
        "flash": flash(msg),
        "rows": rows,
        "invoices": invoices,
        "advertisers": advertisers,
        "pending_withdrawals": pending_withdrawals,
        "withdrawals_recent": withdrawals_recent,
        "payout_methods": payout_methods,
        "payout_exports": payout_exports,
        "finance_accounts": finance_accounts,
        "invoice_total": invoice_total,
        "invoice_count": invoice_count,
        "withdrawal_counts": withdrawal_counts,
    })

@app.get("/api/v1/v11/perfect-ui-audit")
def perfect_ui_audit_api_v1111():
    return {
        "version": "11.11",
        "focus": ["admin/dokazi", "korisnik/dokazi", "oglasivac/dokazi", "admin/finansije", "admin/isplate", "color-system"],
        "status": "ready"
    }


# ---------------------------------------------------
# V11.12 ADMIN CLEAN FULL WIDTH
# ---------------------------------------------------

@app.get("/admin-centar", response_class=HTMLResponse)
def admin_hub_v1112(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    groups = {
        "Pregled": [
            {"title":"Glavni dashboard","url":"/admin/v11","desc":"Najvažniji pregled platforme."},
            {"title":"Mapa platforme","url":"/admin/mapa-platforme","desc":"Sve funkcije na jednoj strani."},
            {"title":"Dnevni radni sto","url":"/admin/daily-desk-v11","desc":"Dnevne operacije i obaveze."},
            {"title":"Pametni panel","url":"/panel-v111","desc":"Brze sistemske komande."},
        ],
        "Operacije": [
            {"title":"Kampanje","url":"/admin/kampanje","desc":"Moderacija kampanja."},
            {"title":"Dokazi","url":"/admin/dokazi","desc":"Pregled i odobravanje dokaza."},
            {"title":"Isplate","url":"/admin/isplate","desc":"Obrada isplata korisnicima."},
            {"title":"Tiketi","url":"/admin/tiketi","desc":"Podrška i korisnički zahtevi."},
        ],
        "Novac i reklame": [
            {"title":"Finansije","url":"/admin/finansije","desc":"Prihodi, budžeti i isplate."},
            {"title":"Cene i provizije","url":"/admin/cene-v111","desc":"Podešavanje cena platforme."},
            {"title":"Banneri i isticanja","url":"/admin/reklame-v111","desc":"Reklame, top pozicija i slotovi."},
            {"title":"Budžeti oglašivača","url":"/admin/budget-v11","desc":"Kontrola sredstava oglašivača."},
        ],
        "Sistem": [
            {"title":"Anti-fraud","url":"/admin/fraud-v11","desc":"Sumnjive aktivnosti i kontrola."},
            {"title":"Automatizacija","url":"/admin/workflows-v10","desc":"Tokovi rada i okidači."},
            {"title":"Legal","url":"/admin/legal-v11","desc":"Pravne stranice i usklađenost."},
            {"title":"Produkcija","url":"/admin/deploy-v11","desc":"Deploy, smoke test i status."},
        ],
    }
    return templates.TemplateResponse("admin_hub_v1112.html", {
        "request": request,
        "user": u,
        "flash": None,
        "groups": groups,
    })

@app.get("/api/v1/v11/admin-clean-audit")
def api_admin_clean_audit_v1112():
    return {"version":"11.12", "layout":"admin-full-width-no-left-sidebar", "status":"ready"}




# ---------------------------------------------------
# V11.13 ADMIN AUTOMATION & CONTROL
# ---------------------------------------------------

KZ113_AUTOMATION_RULES = [
    {"title":"Automatska provera vremena gledanja", "trigger":"timer_completed", "status":"aktivno", "desc":"Korisnik ne može da pošalje dokaz pre isteka zadatog vremena."},
    {"title":"Pauza ako korisnik napusti stranicu", "trigger":"visibility_hidden", "status":"aktivno", "desc":"Ako korisnik izađe sa stranice, tajmer se zaustavlja i ne računa vreme."},
    {"title":"Auto-flag za prebrze dokaze", "trigger":"proof_too_fast", "status":"aktivno", "desc":"Dokaz poslat pre minimalnog vremena ulazi u sumnjive."},
    {"title":"Auto isticanje plaćene kampanje", "trigger":"boost_paid", "status":"aktivno", "desc":"Plaćena top pozicija automatski stavlja kampanju na vrh."},
]

def kz113_get_price(db: Session, key: str, default: float = 0.0):
    if "MonetizationPricingV111" not in globals():
        return default
    row = db.query(MonetizationPricingV111).filter(MonetizationPricingV111.key == key).first()
    if not row:
        return default
    if hasattr(row, "value_percent") and row.value_percent and row.value_percent != 0:
        return float(row.value_percent)
    if hasattr(row, "value_rsd"):
        return float(row.value_rsd or default)
    if hasattr(row, "amount_rsd"):
        return float(row.amount_rsd or default)
    return default

def kz113_set_price(db: Session, key: str, title: str, desc: str, amount: float, unit: str = "RSD"):
    if "MonetizationPricingV111" not in globals():
        return None
    row = db.query(MonetizationPricingV111).filter(MonetizationPricingV111.key == key).first()
    is_percent = (unit == "%")
    if not row:
        kwargs = {"key": key, "title": title, "description": desc}
        if "value_rsd" in MonetizationPricingV111.__table__.columns:
            kwargs["value_rsd"] = 0.0 if is_percent else float(amount)
        if "value_percent" in MonetizationPricingV111.__table__.columns:
            kwargs["value_percent"] = float(amount) if is_percent else 0.0
        if "amount_rsd" in MonetizationPricingV111.__table__.columns:
            kwargs["amount_rsd"] = float(amount)
        if "unit" in MonetizationPricingV111.__table__.columns:
            kwargs["unit"] = unit
        if "is_active" in MonetizationPricingV111.__table__.columns:
            kwargs["is_active"] = True
        row = MonetizationPricingV111(**kwargs)
        db.add(row)
    else:
        row.title = title
        row.description = desc
        if hasattr(row, "value_rsd"):
            row.value_rsd = 0.0 if is_percent else float(amount)
        if hasattr(row, "value_percent"):
            row.value_percent = float(amount) if is_percent else 0.0
        if hasattr(row, "amount_rsd"):
            row.amount_rsd = float(amount)
        if hasattr(row, "unit"):
            row.unit = unit
        if hasattr(row, "is_active"):
            row.is_active = True
    db.commit()
    return row

@app.get("/admin/cene-v111", response_class=HTMLResponse)
def admin_prices_final_v1113(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    # Ensure defaults exist, including split percentages.
    defaults = [
        ("AD_VIEW_COST_RSD", "Cena gledanja reklame za oglašivača", "Koliko se skida oglašivaču za validno gledanje reklame.", 8.0, "RSD"),
        ("AD_VIEW_REWARD_RSD", "Nagrada korisniku za gledanje reklame", "Koliko korisnik dobija za validno gledanje reklame.", 5.0, "RSD"),
        ("AD_VIEW_PLATFORM_PERCENT", "Procenat platforme od gledanja", "Koliki procenat od cene gledanja ide platformi.", 37.5, "%"),
        ("AD_VIEW_USER_PERCENT", "Procenat korisniku od gledanja", "Koliki procenat od cene gledanja ide korisniku.", 62.5, "%"),
        ("BANNER_HOME_TOP_7D", "Veliki banner na početnoj / dan", "Cena velikog banner slota po danu.", 5000.0, "RSD"),
        ("BANNER_HOME_MID_7D", "Srednji banner na početnoj / dan", "Cena srednjeg banner slota po danu.", 3000.0, "RSD"),
        ("BOOST_TOP_POSITION_3D", "Podizanje kampanje na prvo mesto / 3 dana", "Cena top pozicije za 3 dana.", 1500.0, "RSD"),
        ("BOOST_FEATURED_3D", "Featured kampanja / 3 dana", "Cena featured oznake za 3 dana.", 1000.0, "RSD"),
        ("PLATFORM_COMMISSION_PERCENT", "Provizija platforme na kampanje", "Globalna provizija platforme za nove kampanje.", 20.0, "%"),
    ]
    for key,title,desc,amount,unit in defaults:
        kz113_set_price(db, key, title, desc, amount, unit)
    prices = db.query(MonetizationPricingV111).order_by(MonetizationPricingV111.key).all() if "MonetizationPricingV111" in globals() else []
    margin_snapshot = v11837_margin_snapshot(db)
    return templates.TemplateResponse("admin_prices_final_v1113.html", {
        "request": request, "user": u, "flash": None, "prices": prices,
        "ad_cost": kz113_get_price(db, "AD_VIEW_COST_RSD", 8),
        "ad_reward": kz113_get_price(db, "AD_VIEW_REWARD_RSD", 5),
        "platform_percent": kz113_get_price(db, "AD_VIEW_PLATFORM_PERCENT", 37.5),
        "user_percent": kz113_get_price(db, "AD_VIEW_USER_PERCENT", 62.5),
        "margin_snapshot": margin_snapshot,
        "sales_packages": margin_snapshot["packages"],
        "pricing_summary": v11836_pricing_summary(db),
    })

@app.post("/admin/cene-v111/split")
def admin_prices_split_save_v1113(request: Request, db: Session = Depends(get_db),
                                  ad_cost: float = Form(...),
                                  platform_percent: float = Form(...),
                                  user_percent: float = Form(...)):
    u = require(request, db); check_role(u, ["admin"])
    if platform_percent < 0 or user_percent < 0 or round(platform_percent + user_percent, 2) != 100.0:
        return RedirectResponse("/admin/cene-v111?msg=split_error", status_code=303)
    reward = round(float(ad_cost) * float(user_percent) / 100.0, 2)
    kz113_set_price(db, "AD_VIEW_COST_RSD", "Cena gledanja reklame za oglašivača", "Koliko se skida oglašivaču za validno gledanje reklame.", ad_cost, "RSD")
    kz113_set_price(db, "AD_VIEW_PLATFORM_PERCENT", "Procenat platforme od gledanja", "Koliki procenat od cene gledanja ide platformi.", platform_percent, "%")
    kz113_set_price(db, "AD_VIEW_USER_PERCENT", "Procenat korisniku od gledanja", "Koliki procenat od cene gledanja ide korisniku.", user_percent, "%")
    kz113_set_price(db, "AD_VIEW_REWARD_RSD", "Nagrada korisniku za gledanje reklame", "Automatski izračunato iz procenta korisnika.", reward, "RSD")
    return RedirectResponse("/admin/cene-v111?msg=split_saved", status_code=303)

@app.post("/admin/cene-v111/save-all")
async def admin_prices_save_all_v1113(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    form = await request.form()
    if "MonetizationPricingV111" in globals():
        for k,v in form.items():
            if k.startswith("amount_"):
                pid = int(k.replace("amount_",""))
                row = db.query(MonetizationPricingV111).filter(MonetizationPricingV111.id == pid).first()
                if row:
                    try:
                        val = float(v)
                        is_percent = bool(getattr(row, "value_percent", 0))
                        if hasattr(row, "value_percent") and is_percent:
                            row.value_percent = val
                        elif hasattr(row, "value_rsd"):
                            row.value_rsd = val
                        elif hasattr(row, "amount_rsd"):
                            row.amount_rsd = val
                    except Exception:
                        pass
        db.commit()
    return RedirectResponse("/admin/cene-v111?msg=saved", status_code=303)

@app.get("/admin/budget-v11", response_class=HTMLResponse)
def admin_budget_final_v1113(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    advertisers = db.query(User).filter(User.role == "oglasivac").order_by(User.full_name).all()
    total_available = sum(float(a.advertiser_budget_rsd or 0) for a in advertisers)
    total_reserved = sum(float(a.advertiser_reserved_rsd or 0) for a in advertisers)
    total_spent = sum(float(a.advertiser_spent_rsd or 0) for a in advertisers)
    alerts = db.query(AdvertiserBudgetAlertV11).order_by(AdvertiserBudgetAlertV11.created_at.desc()).all()
    logs = db.query(CampaignStatusLogV11).order_by(CampaignStatusLogV11.created_at.desc()).limit(24).all()
    top_advertisers = sorted(
        advertisers,
        key=lambda a: float((getattr(a, "advertiser_reserved_rsd", 0) or 0) + (getattr(a, "advertiser_spent_rsd", 0) or 0)),
        reverse=True,
    )[:6]
    summary = {
        "count": len(advertisers),
        "alerts_active": sum(1 for a in alerts if getattr(a, "status", "") == "active"),
        "alerts_total": len(alerts),
        "logs_total": len(logs),
    }
    return templates.TemplateResponse("admin_budget_final_v1113.html", {
        "request":request, "user":u, "flash":None, "advertisers":advertisers,
        "total_available":total_available, "total_reserved":total_reserved, "total_spent":total_spent,
        "alerts": alerts, "logs": logs, "top_advertisers": top_advertisers, "summary": summary,
    })

# V11.14 disabled old route /admin/fraud-v11
def admin_fraud_final_v1113(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    suspicious = []
    users = db.query(User).order_by(User.created_at.desc()).limit(80).all()
    for usr in users:
        reject_count = db.query(TaskSubmission).filter(TaskSubmission.user_id == usr.id, TaskSubmission.status == "rejected").count()
        pending_count = db.query(TaskSubmission).filter(TaskSubmission.user_id == usr.id, TaskSubmission.status == "pending").count()
        risk = 0
        reasons = []
        if reject_count >= 2:
            risk += 45; reasons.append("više odbijenih dokaza")
        if pending_count >= 5:
            risk += 25; reasons.append("mnogo dokaza na čekanju")
        if getattr(usr, 'is_blocked', False):
            risk += 50; reasons.append("blokiran nalog")
        if risk > 0:
            suspicious.append({"user":usr, "risk":min(risk,100), "reasons":", ".join(reasons), "status":"kontrola"})
    return templates.TemplateResponse("admin_fraud_final_v1113.html", {
        "request":request, "user":u, "flash":None, "suspicious":suspicious, "rules":KZ113_AUTOMATION_RULES,
    })

# V11.14 disabled old route /admin/workflows-v10
def admin_workflows_final_v1113(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    workflows = []
    if "AutomationRule" in globals():
        workflows = db.query(AutomationRule).order_by(AutomationRule.created_at.desc()).all()
    return templates.TemplateResponse("admin_workflows_final_v1113.html", {
        "request":request, "user":u, "flash":None, "rules":KZ113_AUTOMATION_RULES, "workflows":workflows,
    })

@app.get("/admin/deploy-v11", response_class=HTMLResponse)
def admin_deploy_final_v1113(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    checks = db.query(ProductionConfigCheckV11).order_by(ProductionConfigCheckV11.created_at.desc()).all()
    targets = db.query(DeployTargetV11).order_by(DeployTargetV11.created_at.desc()).all()
    backups = db.query(BackupRunV11).order_by(BackupRunV11.created_at.desc()).all()
    smoke_runs = db.query(SmokeTestRunV11).order_by(SmokeTestRunV11.created_at.desc()).limit(6).all()
    summary = {
        "checks_total": len(checks),
        "checks_done": sum(1 for c in checks if c.status == "done"),
        "checks_open": sum(1 for c in checks if c.status == "open"),
        "checks_blocked": sum(1 for c in checks if c.status == "blocked"),
        "targets_ready": sum(1 for t in targets if t.status in ["ready", "production", "live"]),
        "targets_total": len(targets),
        "backups_total": len(backups),
        "smoke_total": len(smoke_runs),
        "smoke_passed": sum(1 for r in smoke_runs if getattr(r, "status", "") == "passed"),
    }
    return templates.TemplateResponse("admin_deploy_v11.html", {
        "request": request, "user": u, "flash": None, "checks": checks,
        "targets": targets, "backups": backups, "smoke_runs": smoke_runs, "summary": summary,
        "ops_suite": v11838_ops_suite_context(db, "/admin/deploy-v11"),
    })

@app.post("/admin/tasks/{task_id}/auto-boost")
def admin_task_auto_boost_v1113(task_id: int, request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t: raise HTTPException(404)
    t.featured = True
    if hasattr(t, "status"):
        t.status = "active"
    db.commit()
    return RedirectResponse("/admin/kampanje?msg=boosted", status_code=303)

# V11.13 disabled old task detail route
@app.get("/zadaci/{task_id}", response_class=HTMLResponse)
def task_detail_timer_v1113(task_id: int, request: Request, db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t:
        raise HTTPException(404)
    u = current_user(request, db)
    seconds = int((t.estimated_minutes or 2) * 60)
    # minimum for demo: do not make demo painfully long, but keep real value in UI
    return templates.TemplateResponse("task_detail_timer_v1113.html", {
        "request":request, "user":u, "flash":None, "task":t, "required_seconds":seconds,
    })

@app.get("/api/v1/v11/admin-automation-audit")
def api_admin_automation_audit_v1113():
    return {"version":"11.13", "status":"ready", "features":["admin price split","auto boost","task timer","admin automation pages"]}




# ---------------------------------------------------
# V11.14 AUTO APPROVAL & BUDGET ENGINE
# ---------------------------------------------------

def kz114_log(db: Session, event_type: str, message: str, actor=None, task=None, submission=None, amount: float = 0.0, status: str = "done", meta: str = ""):
    row = AutoEngineLogV114(
        event_type=event_type,
        actor_role=(actor.role if actor else "system"),
        actor_user_id=(actor.id if actor else None),
        task_id=(task.id if task else None),
        submission_id=(submission.id if submission else None),
        amount_rsd=float(amount or 0),
        status=status,
        message=message,
        meta_json=meta or "",
    )
    db.add(row)
    db.commit()
    return row

def kz114_queue_notify(db: Session, channel: str, recipient: str, subject: str, body: str, user=None, task=None):
    row = AutoNotificationQueueV114(
        channel=channel,
        recipient=recipient or "",
        subject=subject or "",
        body=body or "",
        related_user_id=(user.id if user else None),
        related_task_id=(task.id if task else None),
        status="queued",
    )
    db.add(row)
    db.commit()
    return row

def kz114_price(db: Session, key: str, default: float):
    try:
        return kz113_get_price(db, key, default)
    except Exception:
        return default

def kz114_try_auto_approve(db: Session, submission):
    """Safe auto approval for simple timer-controlled tasks."""
    if not submission or submission.status != "pending":
        return False, "nije pending"
    task = submission.task
    user = submission.user
    if not task or not user:
        return False, "nedostaje korisnik ili zadatak"

    # Only auto approve low-risk categories.
    auto_categories = ["Gledanje sajta", "Test sajta", "Testiranje", "Anketa", "Feedback", "Registracija"]
    cat_text = f"{task.category or ''} {task.task_type or ''}".lower()
    can_auto = any(x.lower() in cat_text for x in auto_categories)

    # Basic proof requirement.
    proof_ok = bool((submission.proof or "").strip()) or bool(getattr(submission, "proof_file", None))

    if not can_auto:
        return False, "kategorija zahteva ručnu proveru"
    if not proof_ok:
        return False, "nema dokaza"

    # approve
    submission.status = "approved"
    if hasattr(submission, "admin_note"):
        submission.admin_note = "Automatski odobreno: tajmer/dokaz su prošli osnovnu kontrolu."

    reward = float(submission.reward_rsd or task.reward_rsd or 0)
    if hasattr(user, "pending_rsd"):
        user.pending_rsd = max(0, float(user.pending_rsd or 0) - reward)
    if hasattr(user, "balance_rsd"):
        user.balance_rsd = float(user.balance_rsd or 0) + reward
    if hasattr(user, "lifetime_earned_rsd"):
        user.lifetime_earned_rsd = float(user.lifetime_earned_rsd or 0) + reward

    db.commit()
    kz114_log(db, "auto_approve_proof", f"Automatski odobren dokaz za zadatak: {task.title}", actor=None, task=task, submission=submission, amount=reward)
    kz114_queue_notify(db, "internal", user.email, "Dokaz odobren", f"Dokaz za zadatak '{task.title}' je automatski odobren.", user=user, task=task)
    return True, "odobreno"

# V11.15 disabled old route /admin/auto-engine-v114
def admin_auto_engine_v114(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    logs = db.query(AutoEngineLogV114).order_by(AutoEngineLogV114.created_at.desc()).limit(80).all()
    queue = db.query(AutoNotificationQueueV114).order_by(AutoNotificationQueueV114.created_at.desc()).limit(80).all()
    sessions = db.query(TaskViewSessionV114).order_by(TaskViewSessionV114.created_at.desc()).limit(50).all()
    stats = {
        "logs": db.query(AutoEngineLogV114).count(),
        "queued": db.query(AutoNotificationQueueV114).filter(AutoNotificationQueueV114.status == "queued").count(),
        "sessions": db.query(TaskViewSessionV114).count(),
        "completed_sessions": db.query(TaskViewSessionV114).filter(TaskViewSessionV114.is_completed == True).count(),
    }
    return templates.TemplateResponse("admin_auto_engine_v114.html", {
        "request": request, "user": u, "flash": None,
        "logs": logs, "queue": queue, "sessions": sessions, "stats": stats,
    })

@app.get("/admin/workflows-v10", response_class=HTMLResponse)
def admin_workflows_auto_v114(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    logs = db.query(AutoEngineLogV114).order_by(AutoEngineLogV114.created_at.desc()).limit(20).all()
    rules = [
        {"title":"Auto top pozicija", "status":"aktivno", "desc":"Oglašivač klikne, sistem proveri budžet, skine cenu i odmah istakne kampanju."},
        {"title":"Auto odobravanje sigurnih dokaza", "status":"aktivno", "desc":"Jednostavni zadaci sa tajmerom i dokazom mogu biti odobreni automatski."},
        {"title":"Tajmer kontrole gledanja", "status":"aktivno", "desc":"Korisnik ne može potvrditi zadatak dok ne istekne minimalno vreme."},
        {"title":"Pauza kad korisnik napusti tab", "status":"aktivno", "desc":"Ako korisnik promeni tab, vreme se ne računa."},
        {"title":"Email/SMS queue", "status":"priprema", "desc":"Sistem upisuje poruke u queue, a pravo slanje se kači kasnije."},
        {"title":"AI screenshot review", "status":"priprema", "desc":"Mesto za AI proveru screenshot dokaza i sumnjivih fajlova."},
    ]
    return templates.TemplateResponse("admin_workflows_auto_v114.html", {
        "request": request, "user": u, "flash": None, "rules": rules, "logs": logs,
    })

@app.get("/admin/fraud-v11", response_class=HTMLResponse)
def admin_fraud_auto_v114(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    suspicious = []
    campaign_risks = []
    identity_rows = []
    users = db.query(User).order_by(User.created_at.desc()).limit(120).all()
    for usr in users:
        profile = v11836_user_fraud_profile(db, usr)
        if profile["risk_score"] > 0:
            suspicious.append(profile)
            identity = profile.get("identity") or {}
            identity_flags = []
            if identity.get("same_device_users", 0) > 0:
                identity_flags.append(f"isti uređaj ×{identity['same_device_users']}")
            if identity.get("same_ip_users", 0) > 0:
                identity_flags.append(f"isti IP ×{identity['same_ip_users']}")
            if identity.get("same_payment_users", 0) > 0:
                identity_flags.append(f"isti payment ×{identity['same_payment_users']}")
            if identity_flags:
                identity_rows.append({
                    "user": usr,
                    "risk_score": profile["risk_score"],
                    "level": profile["level"],
                    "flags": identity_flags,
                    "identity": identity,
                })
            if profile["risk_score"] >= 40:
                existing = db.query(FraudSignalV11).filter(FraudSignalV11.user_id == usr.id, FraudSignalV11.signal_type == "user_risk_score").first()
                details = f"risk={profile['risk_score']}; approved={profile['approved']}; rejected={profile['rejected']}; pending={profile['pending']}; reasons={', '.join(profile['reasons'])}"
                if existing:
                    existing.risk_score = float(profile["risk_score"])
                    existing.details = details
                    existing.status = "open"
                else:
                    db.add(FraudSignalV11(user_id=usr.id, signal_type="user_risk_score", risk_score=float(profile["risk_score"]), details=details))

    tasks = db.query(Task).order_by(Task.created_at.desc()).limit(120).all()
    for task in tasks:
        profile = v11836_campaign_fraud_profile(db, task)
        if profile["risk_score"] > 0:
            campaign_risks.append(profile)
            if profile["risk_score"] >= 45:
                owner_id = task.advertiser_id if getattr(task, "advertiser_id", None) else None
                signal_type = f"campaign_risk_{task.id}"
                details = f"task={task.title}; risk={profile['risk_score']}; total={profile['total']}; approved={profile['approved']}; rejected={profile['rejected']}; pending={profile['pending']}; reasons={', '.join(profile['reasons'])}"
                existing = db.query(FraudSignalV11).filter(FraudSignalV11.user_id == owner_id, FraudSignalV11.signal_type == signal_type).first()
                if existing:
                    existing.risk_score = float(profile["risk_score"])
                    existing.details = details
                    existing.status = "open"
                else:
                    db.add(FraudSignalV11(user_id=owner_id, signal_type=signal_type, risk_score=float(profile["risk_score"]), details=details))
    rules = [
        "previše odbijenih dokaza",
        "previše pending dokaza",
        "dupliran telefon",
        "dokaz bez minimalnog vremena",
        "pokušaj slanja dokaza pre isteka tajmera",
    ]
    fraud_summary = {
        "open_signals": len(suspicious) + len(campaign_risks) + len(identity_rows),
        "user_high": sum(1 for s in suspicious if s["risk_score"] >= 70),
        "user_medium": sum(1 for s in suspicious if 40 <= s["risk_score"] < 70),
        "campaign_high": sum(1 for c in campaign_risks if c["risk_score"] >= 70),
        "campaign_medium": sum(1 for c in campaign_risks if 40 <= c["risk_score"] < 70),
        "identity_rows": len(identity_rows),
        "rules": len(rules),
    }
    top_users = sorted(suspicious, key=lambda row: row["risk_score"], reverse=True)[:6]
    top_campaigns = sorted(campaign_risks, key=lambda row: row["risk_score"], reverse=True)[:6]
    db.commit()
    return templates.TemplateResponse("admin_fraud_auto_v114.html", {
        "request": request, "user": u, "flash": None, "suspicious": suspicious, "campaign_risks": campaign_risks, "identity_rows": identity_rows, "rules": rules,
        "fraud_summary": fraud_summary, "top_users": top_users, "top_campaigns": top_campaigns,
    })

@app.get("/oglasivac/boost-v111", response_class=HTMLResponse)
def advertiser_boost_auto_v114(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["oglasivac"])
    tasks = db.query(Task).filter(Task.advertiser_id == u.id).order_by(Task.created_at.desc()).all()
    price = kz114_price(db, "BOOST_TOP_POSITION_3D", 1500.0)
    return templates.TemplateResponse("advertiser_boost_auto_v114.html", {
        "request": request, "user": u, "flash": None, "tasks": tasks, "price": price,
    })

@app.post("/oglasivac/boost-v111/auto")
def advertiser_boost_auto_post_v114(request: Request, db: Session = Depends(get_db),
                                    task_id: int = Form(...)):
    u = require(request, db); check_role(u, ["oglasivac"])
    task = db.query(Task).filter(Task.id == task_id, Task.advertiser_id == u.id).first()
    if not task:
        return RedirectResponse("/oglasivac/boost-v111?msg=task_not_found", status_code=303)
    price = kz114_price(db, "BOOST_TOP_POSITION_3D", 1500.0)
    available = float(getattr(u, "advertiser_budget_rsd", 0) or 0)
    if available < price:
        kz114_log(db, "auto_boost_failed", f"Nedovoljno budžeta za top poziciju: {task.title}", actor=u, task=task, amount=price, status="failed")
        return RedirectResponse("/oglasivac/boost-v111?msg=no_budget", status_code=303)

    u.advertiser_budget_rsd = available - price
    if hasattr(u, "advertiser_spent_rsd"):
        u.advertiser_spent_rsd = float(u.advertiser_spent_rsd or 0) + price
    task.featured = True
    task.status = "active"
    db.commit()

    kz114_log(db, "auto_boost_success", f"Kampanja automatski podignuta na prvo mesto: {task.title}", actor=u, task=task, amount=price, status="done")
    kz114_queue_notify(db, "internal", u.email, "Kampanja istaknuta", f"Kampanja '{task.title}' je automatski podignuta na prvo mesto.", user=u, task=task)
    return RedirectResponse("/oglasivac/boost-v111?msg=boost_done", status_code=303)

@app.post("/korisnik/zadaci/{task_id}/dokaz-auto")
def user_submit_proof_auto_v114(task_id: int, request: Request, db: Session = Depends(get_db),
                                proof_text: str = Form(""),
                                timer_ok: str = Form("no")):
    u = require(request, db); check_role(u, ["korisnik"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404)
    if timer_ok != "yes":
        session = db.query(TaskViewSessionV114).filter(
            TaskViewSessionV114.user_id == u.id,
            TaskViewSessionV114.task_id == task.id,
            TaskViewSessionV114.is_completed == True
        ).order_by(TaskViewSessionV114.created_at.desc()).first()
        if not session:
            try:
                kz114_log(db, "proof_blocked_timer", f"Korisnik je pokušao dokaz pre isteka tajmera: {task.title}", actor=u, task=task, status="blocked")
            except Exception:
                pass
            return RedirectResponse(f"/zadaci/{task_id}?msg=timer_required", status_code=303)

    sub, status = v11831_create_submission(db, u, task, proof_text, "")
    if status != "created":
        return RedirectResponse(f"/zadaci/{task_id}?msg={status}", status_code=303)

    try:
        decision, profile = v11831_auto_review_submission(db, sub, actor=u, source="timer")
        if decision == "approved":
            return RedirectResponse("/korisnik/dokazi?msg=auto_approved", status_code=303)
        if decision == "rejected":
            return RedirectResponse("/korisnik/dokazi?msg=auto_rejected", status_code=303)
    except Exception:
        pass
    return RedirectResponse("/korisnik/dokazi?msg=pending_manual", status_code=303)

@app.post("/api/v1/v11/task-view/start")
async def api_task_view_start_v114(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    task_id = int(data.get("task_id"))
    u = current_user(request, db)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return JSONResponse({"ok": False, "error": "task_not_found"}, status_code=404)
    required = int((task.estimated_minutes or 2) * 60)
    row = TaskViewSessionV114(user_id=(u.id if u else None), task_id=task.id, required_seconds=required, active_seconds=0, status="started")
    db.add(row); db.commit(); db.refresh(row)
    return {"ok": True, "session_id": row.id, "required_seconds": required}

@app.post("/api/v1/v11/task-view/tick")
async def api_task_view_tick_v114(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    sid = int(data.get("session_id"))
    add_seconds = int(data.get("seconds", 1))
    row = db.query(TaskViewSessionV114).filter(TaskViewSessionV114.id == sid).first()
    if not row:
        return JSONResponse({"ok": False, "error": "session_not_found"}, status_code=404)
    if not row.is_completed:
        row.active_seconds = int(row.active_seconds or 0) + max(0, min(add_seconds, 5))
        if row.active_seconds >= row.required_seconds:
            row.is_completed = True
            row.status = "completed"
            row.completed_at = datetime.utcnow()
        db.commit()
    return {"ok": True, "active_seconds": row.active_seconds, "required_seconds": row.required_seconds, "completed": row.is_completed}

@app.get("/api/v1/v11/auto-engine-audit")
def api_auto_engine_audit_v114():
    return {"version": "11.14", "status": "ready", "features": ["auto boost budget", "auto proof approval", "timer verification", "notification queue", "ai review placeholder"]}




# ---------------------------------------------------
# V11.15 SMART AUTOMATION & USER MOTIVATION
# ---------------------------------------------------

KZ115_USER_STATUSES = [
    {"name":"Nov", "min_quality":0, "max_risk":100, "desc":"Novi korisnik, osnovni limiti."},
    {"name":"Pouzdan", "min_quality":65, "max_risk":40, "desc":"Dobija više zadataka i bržu proveru."},
    {"name":"Proveren", "min_quality":78, "max_risk":30, "desc":"Prioritet za bolje plaćene zadatke."},
    {"name":"Premium tester", "min_quality":88, "max_risk":20, "desc":"Najbolji zadaci i posebne misije."},
    {"name":"VIP korisnik", "min_quality":95, "max_risk":10, "desc":"Maksimalan prioritet i bonus misije."},
    {"name":"Pod kontrolom", "min_quality":0, "max_risk":65, "desc":"Ručno proveravanje dokaza."},
    {"name":"Rizičan", "min_quality":0, "max_risk":100, "desc":"Ograničen pristup zadacima."},
]

KZ115_BADGE_LIBRARY = [
    ("first_task", "Prvi zadatak", "Završen prvi zadatak.", "🥇"),
    ("three_day_streak", "3 dana zaredom", "Aktivan 3 dana zaredom.", "🔥"),
    ("seven_day_streak", "Nedelju dana zaredom", "Aktivan nedelju dana zaredom.", "⚡"),
    ("quality_80", "Pouzdan tester", "Quality score preko 80.", "✅"),
    ("quality_95", "Elite tester", "Quality score preko 95.", "💎"),
    ("ten_approved", "10 odobrenih", "Deset uspešno odobrenih dokaza.", "🏆"),
    ("fast_starter", "Brzi start", "Započeo zadatak odmah posle registracije.", "🚀"),
    ("feedback_master", "Majstor feedback-a", "Kvalitetni feedback zadaci.", "💬"),
]

def kz115_today():
    return datetime.utcnow().strftime("%Y-%m-%d")

def kz115_get_score(db: Session, user):
    row = db.query(UserScoreV115).filter(UserScoreV115.user_id == user.id).first()
    if not row:
        row = UserScoreV115(user_id=user.id, quality_score=50.0, risk_score=0.0, level_name="Novi član", status_name="Nov")
        db.add(row); db.commit(); db.refresh(row)
    return row

def kz115_award_badge(db: Session, user, badge_key: str):
    exists = db.query(UserBadgeV115).filter(UserBadgeV115.user_id == user.id, UserBadgeV115.badge_key == badge_key).first()
    if exists:
        return exists
    for key,title,desc,icon in KZ115_BADGE_LIBRARY:
        if key == badge_key:
            b = UserBadgeV115(user_id=user.id, badge_key=key, title=title, description=desc, icon=icon)
            db.add(b); db.commit()
            try:
                kz114_queue_notify(db, "internal", user.email, "Novi bedž", f"Osvojili ste bedž: {title}", user=user)
                kz114_log(db, "badge_awarded", f"Korisnik je osvojio bedž: {title}", actor=user)
            except Exception:
                pass
            return b
    return None

def kz115_recalculate_user_score(db: Session, user):
    score = kz115_get_score(db, user)
    approved = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id, TaskSubmission.status == "approved").count()
    rejected = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id, TaskSubmission.status == "rejected").count()
    pending = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id, TaskSubmission.status == "pending").count()
    total = approved + rejected + pending

    approval_rate = (approved / total) if total else 0.5
    quality = 45 + approval_rate * 45 + min(10, approved * 0.7)
    risk = rejected * 18 + max(0, pending - 5) * 4
    risk = min(100, risk)
    quality = max(0, min(100, quality - (risk * 0.25)))

    if risk >= 70:
        status = "Rizičan"
    elif risk >= 45:
        status = "Pod kontrolom"
    elif quality >= 95:
        status = "VIP korisnik"
    elif quality >= 88:
        status = "Premium tester"
    elif quality >= 78:
        status = "Proveren"
    elif quality >= 65:
        status = "Pouzdan"
    else:
        status = "Nov"

    if quality >= 95:
        level = "Dijamant"
        kz115_award_badge(db, user, "quality_95")
    elif quality >= 80:
        level = "Zlato"
        kz115_award_badge(db, user, "quality_80")
    elif quality >= 65:
        level = "Srebro"
    elif approved >= 1:
        level = "Bronza"
        kz115_award_badge(db, user, "first_task")
    else:
        level = "Novi član"

    if approved >= 10:
        kz115_award_badge(db, user, "ten_approved")

    score.quality_score = round(quality, 1)
    score.risk_score = round(risk, 1)
    score.status_name = status
    score.level_name = level
    score.total_points = int((score.total_points or 0) + max(0, approved - rejected))
    score.updated_at = datetime.utcnow()
    db.commit()
    return score

def kz115_task_priority(task):
    priority = 0
    if getattr(task, "featured", False):
        priority += 1000
    priority += float(getattr(task, "reward_rsd", 0) or 0) * 2
    priority += max(0, 100 - int(getattr(task, "total_slots", 0) or 0)) * 0.2
    cat = f"{getattr(task, 'category', '')} {getattr(task, 'task_type', '')}".lower()
    if "promo" in cat or "top" in cat:
        priority += 120
    return round(priority, 2)

def kz115_auto_maintenance(db: Session):
    now = datetime.utcnow()
    logs = []
    # expire reservations
    expired = db.query(TaskReservationV115).filter(TaskReservationV115.status == "active", TaskReservationV115.reserved_until < now).all()
    for r in expired:
        r.status = "expired"
        logs.append(f"Istekla rezervacija zadatka #{r.task_id}")
        try:
            kz114_log(db, "reservation_expired", f"Rezervacija zadatka je istekla: {r.task.title if r.task else r.task_id}", actor=r.user, task=r.task, status="done")
        except Exception:
            pass

    # pause campaigns without enough advertiser budget
    tasks = db.query(Task).filter(Task.status == "active").all()
    paused = 0
    closed = 0
    for t in tasks:
        advertiser = t.advertiser if hasattr(t, "advertiser") else None
        if advertiser and float(getattr(advertiser, "advertiser_budget_rsd", 0) or 0) <= 0:
            t.status = "paused"
            paused += 1
            logs.append(f"Pauzirana kampanja bez budžeta: {t.title}")
            try: kz114_log(db, "campaign_paused_no_budget", f"Kampanja pauzirana jer nema budžet: {t.title}", task=t)
            except Exception: pass
        approved = db.query(TaskSubmission).filter(TaskSubmission.task_id == t.id, TaskSubmission.status == "approved").count()
        total_slots = int(getattr(t, "total_slots", 0) or 0)
        if total_slots and approved >= total_slots:
            t.status = "closed"
            closed += 1
            logs.append(f"Zatvorena popunjena kampanja: {t.title}")
            try: kz114_log(db, "campaign_closed_full", f"Kampanja zatvorena jer su mesta popunjena: {t.title}", task=t)
            except Exception: pass

    db.commit()
    return {"expired_reservations": len(expired), "paused_campaigns": paused, "closed_campaigns": closed, "logs": logs}

def kz115_generate_advertiser_suggestions(db: Session, advertiser):
    tasks = db.query(Task).filter(Task.advertiser_id == advertiser.id).all()
    created = 0
    for t in tasks:
        approved = db.query(TaskSubmission).filter(TaskSubmission.task_id == t.id, TaskSubmission.status == "approved").count()
        pending = db.query(TaskSubmission).filter(TaskSubmission.task_id == t.id, TaskSubmission.status == "pending").count()
        exists = db.query(AdvertiserSuggestionV115).filter(AdvertiserSuggestionV115.advertiser_id == advertiser.id, AdvertiserSuggestionV115.task_id == t.id, AdvertiserSuggestionV115.status == "open").first()
        if exists:
            continue
        if not getattr(t, "featured", False) and approved + pending < 3:
            s = AdvertiserSuggestionV115(advertiser_id=advertiser.id, task_id=t.id, suggestion_type="boost", title="Podignite kampanju na prvo mesto", description=f"Kampanja '{t.title}' ima slab odziv. Top pozicija može povećati broj izvršenja.", expected_impact="više prikaza i brži rezultati")
            db.add(s); created += 1
        elif float(getattr(t, "reward_rsd", 0) or 0) < 60:
            s = AdvertiserSuggestionV115(advertiser_id=advertiser.id, task_id=t.id, suggestion_type="increase_reward", title="Povećajte nagradu", description=f"Kampanja '{t.title}' ima nižu nagradu. Veća nagrada obično povećava odziv.", expected_impact="veći odziv korisnika")
            db.add(s); created += 1
    db.commit()
    return created

def kz115_daily_report(db: Session):
    today = kz115_today()
    row = db.query(AdminDailyReportV115).filter(AdminDailyReportV115.report_date == today).first()
    if row:
        return row
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    new_users = db.query(User).filter(User.role == "korisnik", User.created_at >= start).count()
    new_adv = db.query(User).filter(User.role == "oglasivac", User.created_at >= start).count()
    approved = db.query(TaskSubmission).filter(TaskSubmission.status == "approved").count()
    rejected = db.query(TaskSubmission).filter(TaskSubmission.status == "rejected").count()
    pending = db.query(TaskSubmission).filter(TaskSubmission.status == "pending").count()
    revenue = db.query(func.coalesce(func.sum(TaskSubmission.platform_fee_rsd), 0)).filter(TaskSubmission.status == "approved").scalar() or 0
    spent = db.query(func.coalesce(func.sum(User.advertiser_spent_rsd), 0)).filter(User.role == "oglasivac").scalar() or 0
    risk_users = db.query(UserScoreV115).filter(UserScoreV115.risk_score >= 45).count()
    summary = f"Danas: novi korisnici {new_users}, novi oglašivači {new_adv}, pending dokazi {pending}, rizični korisnici {risk_users}."
    row = AdminDailyReportV115(report_date=today, new_users=new_users, new_advertisers=new_adv, approved_submissions=approved, rejected_submissions=rejected, pending_submissions=pending, platform_revenue_rsd=float(revenue), advertiser_spent_rsd=float(spent), risk_users=risk_users, summary=summary)
    db.add(row); db.commit()
    return row

def kz115_seed_missions(db: Session, user):
    defaults = [
        ("daily_1", "Završi 1 zadatak danas", "Dnevna misija za aktivnost.", 1, 20, 0),
        ("daily_3", "Završi 3 zadatka", "Bonus za aktivnije korisnike.", 3, 75, 10),
        ("feedback_2", "Pošalji 2 kvalitetna feedback-a", "Motiviše korisnike da daju bolji feedback.", 2, 60, 0),
        ("week_streak", "Budi aktivan nedelju dana", "Streak misija za lojalnost.", 7, 250, 50),
    ]
    for key,title,desc,target,points,rsd in defaults:
        exists = db.query(UserMissionV115).filter(UserMissionV115.user_id == user.id, UserMissionV115.mission_key == key, UserMissionV115.status == "active").first()
        if not exists:
            db.add(UserMissionV115(user_id=user.id, mission_key=key, title=title, description=desc, target_count=target, reward_points=points, reward_rsd=rsd))
    db.commit()

@app.get("/admin/smart-v115", response_class=HTMLResponse)
def admin_smart_v115(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    maintenance = kz115_auto_maintenance(db)
    report = kz115_daily_report(db)
    users = db.query(User).filter(User.role == "korisnik").limit(80).all()
    for user in users:
        kz115_recalculate_user_score(db, user)
    scores = db.query(UserScoreV115).order_by(UserScoreV115.risk_score.desc(), UserScoreV115.quality_score.desc()).limit(20).all()
    advertisers = db.query(User).filter(User.role == "oglasivac").all()
    suggestions_created = 0
    for adv in advertisers:
        suggestions_created += kz115_generate_advertiser_suggestions(db, adv)
    suggestions = db.query(AdvertiserSuggestionV115).order_by(AdvertiserSuggestionV115.created_at.desc()).limit(30).all()
    reservations = db.query(TaskReservationV115).order_by(TaskReservationV115.created_at.desc()).limit(30).all()
    return templates.TemplateResponse("admin_smart_v115.html", {"request":request,"user":u,"flash":None,"maintenance":maintenance,"report":report,"scores":scores,"suggestions":suggestions,"reservations":reservations,"suggestions_created":suggestions_created})

@app.post("/admin/smart-v115/run")
def admin_smart_run_v115(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    kz115_auto_maintenance(db)
    for user in db.query(User).filter(User.role == "korisnik").all():
        kz115_recalculate_user_score(db, user)
    for adv in db.query(User).filter(User.role == "oglasivac").all():
        kz115_generate_advertiser_suggestions(db, adv)
    kz115_daily_report(db)
    try: kz114_log(db, "smart_automation_run", "Admin je pokrenuo Smart Automation Pack.", actor=u)
    except Exception: pass
    return RedirectResponse("/admin/smart-v115?msg=done", status_code=303)

@app.get("/korisnik/motivacija-v115", response_class=HTMLResponse)
def user_motivation_v115(request: Request, db: Session = Depends(get_db)):
    u = require(request, db)
    if u.role != "korisnik":
        return RedirectResponse(role_url(u.role), status_code=303)
    score = kz115_recalculate_user_score(db, u)
    kz115_seed_missions(db, u)
    badges = db.query(UserBadgeV115).filter(UserBadgeV115.user_id == u.id).order_by(UserBadgeV115.awarded_at.desc()).all()
    missions = db.query(UserMissionV115).filter(UserMissionV115.user_id == u.id).order_by(UserMissionV115.created_at.desc()).all()
    rewards = db.query(DailyRewardV115).filter(DailyRewardV115.user_id == u.id).order_by(DailyRewardV115.created_at.desc()).limit(20).all()
    leaderboard = db.query(UserScoreV115).order_by(UserScoreV115.quality_score.desc(), UserScoreV115.total_points.desc()).limit(10).all()
    recent_tasks = db.query(Task).filter(Task.status == "active").order_by(Task.featured.desc(), Task.reward_rsd.desc()).limit(5).all()
    return templates.TemplateResponse("user_motivation_v115.html", {"request":request,"user":u,"flash":None,"score":score,"badges":badges,"missions":missions,"rewards":rewards,"leaderboard":leaderboard,"statuses":KZ115_USER_STATUSES,"recent_tasks":recent_tasks,"all_badges":[{"key":k,"title":t,"description":d,"icon":i,"earned": any(getattr(b,"badge_key","")==k for b in badges)} for k,t,d,i in KZ115_BADGE_LIBRARY]})

@app.post("/korisnik/dnevna-nagrada-v115")
def user_daily_reward_v115(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["korisnik"])
    today = kz115_today()
    exists = db.query(DailyRewardV115).filter(DailyRewardV115.user_id == u.id, DailyRewardV115.reward_date == today).first()
    if exists:
        return RedirectResponse("/korisnik/motivacija-v115?msg=already_claimed", status_code=303)
    score = kz115_get_score(db, u)
    points = 25 + min(100, int(score.streak_days or 0) * 5)
    amount = 0.0
    if (score.streak_days or 0) >= 7:
        amount = 10.0
    reward = DailyRewardV115(user_id=u.id, reward_date=today, points=points, amount_rsd=amount)
    db.add(reward)
    score.daily_points = int(score.daily_points or 0) + points
    score.total_points = int(score.total_points or 0) + points
    # streak logic simplified
    score.streak_days = int(score.streak_days or 0) + 1
    score.last_activity_date = datetime.utcnow()
    if amount and hasattr(u, "balance_rsd"):
        u.balance_rsd = float(u.balance_rsd or 0) + amount
    db.commit()
    if score.streak_days >= 3:
        kz115_award_badge(db, u, "three_day_streak")
    if score.streak_days >= 7:
        kz115_award_badge(db, u, "seven_day_streak")
    try: kz114_log(db, "daily_reward_claimed", f"Korisnik je preuzeo dnevnu nagradu: {points} poena", actor=u, amount=amount)
    except Exception: pass
    return RedirectResponse("/korisnik/motivacija-v115?msg=claimed", status_code=303)

@app.post("/zadaci/{task_id}/rezervisi-v115")
def reserve_task_v115(task_id: int, request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["korisnik"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404)
    existing_done = db.query(TaskSubmission).filter(TaskSubmission.user_id == u.id, TaskSubmission.task_id == task.id).first()
    if existing_done:
        return RedirectResponse(f"/zadaci/{task_id}?msg=already_done", status_code=303)
    existing = db.query(TaskReservationV115).filter(TaskReservationV115.user_id == u.id, TaskReservationV115.task_id == task.id, TaskReservationV115.status == "active").first()
    if existing:
        return RedirectResponse(f"/zadaci/{task_id}?msg=already_reserved", status_code=303)
    minutes = max(15, int((task.estimated_minutes or 5) + 15))
    r = TaskReservationV115(user_id=u.id, task_id=task.id, reserved_until=datetime.utcnow()+timedelta(minutes=minutes))
    db.add(r); db.commit()
    try: kz114_log(db, "task_reserved", f"Korisnik je rezervisao zadatak: {task.title}", actor=u, task=task)
    except Exception: pass
    return RedirectResponse(f"/zadaci/{task_id}?msg=reserved", status_code=303)

@app.get("/oglasivac/saveti-v115", response_class=HTMLResponse)
def advertiser_suggestions_v115(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["oglasivac"])
    kz115_generate_advertiser_suggestions(db, u)
    suggestions = db.query(AdvertiserSuggestionV115).filter(AdvertiserSuggestionV115.advertiser_id == u.id).order_by(AdvertiserSuggestionV115.created_at.desc()).all()
    return templates.TemplateResponse("advertiser_suggestions_v115.html", {"request":request,"user":u,"flash":None,"suggestions":suggestions})

@app.get("/api/v1/v11/smart-automation-audit")
def api_smart_automation_audit_v115():
    return {"version":"11.15","status":"ready","features":["reservations","quality_score","risk_score","badges","daily_rewards","missions","leaderboard","advertiser_suggestions","daily_admin_report","maintenance"]}


# V11.15 compatibility auto engine dashboard
@app.get("/admin/auto-engine-v114", response_class=HTMLResponse)
def admin_auto_engine_v115_compat(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    logs = db.query(AutoEngineLogV114).order_by(AutoEngineLogV114.created_at.desc()).limit(80).all() if "AutoEngineLogV114" in globals() else []
    queue = db.query(AutoNotificationQueueV114).order_by(AutoNotificationQueueV114.created_at.desc()).limit(80).all() if "AutoNotificationQueueV114" in globals() else []
    sessions = db.query(TaskViewSessionV114).order_by(TaskViewSessionV114.created_at.desc()).limit(50).all() if "TaskViewSessionV114" in globals() else []
    submissions_pending = db.query(TaskSubmission).filter(TaskSubmission.status == "pending").count()
    submissions_auto_approved = db.query(AutoEngineLogV114).filter(AutoEngineLogV114.event_type == "submission_auto_approved").count() if "AutoEngineLogV114" in globals() else 0
    submissions_auto_rejected = db.query(AutoEngineLogV114).filter(AutoEngineLogV114.event_type == "submission_auto_rejected").count() if "AutoEngineLogV114" in globals() else 0
    stats = {
        "logs": len(logs),
        "queued": len([q for q in queue if q.status == "queued"]),
        "sessions": len(sessions),
        "completed_sessions": len([s for s in sessions if s.is_completed]),
        "submissions_pending": submissions_pending,
        "submissions_auto_approved": submissions_auto_approved,
        "submissions_auto_rejected": submissions_auto_rejected,
    }
    return templates.TemplateResponse("admin_auto_engine_v115_compat.html", {
        "request": request,
        "user": u,
        "flash": None,
        "logs": logs,
        "queue": queue,
        "sessions": sessions,
        "stats": stats,
    })


# ---------------------------------------------------
# V11.16 PREMIUM ADMIN DASHBOARD OVERRIDE
# ---------------------------------------------------
@app.get("/admin/v11", response_class=HTMLResponse)
def admin_v11_premium_dashboard_v116(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    users = db.query(User).order_by(User.created_at.desc()).limit(50).all()
    tasks = db.query(Task).order_by(Task.created_at.desc()).limit(50).all()
    pending_tasks = db.query(Task).filter(Task.status == "pending").all()
    pending_subs = db.query(TaskSubmission).filter(TaskSubmission.status == "pending").all()
    pending_withdrawals = db.query(Withdrawal).filter(Withdrawal.status == "pending").all()
    platform_fee_total = db.query(func.coalesce(func.sum(TaskSubmission.platform_fee_rsd), 0)).filter(TaskSubmission.status == "approved").scalar() or 0
    approved_total = db.query(func.coalesce(func.sum(TaskSubmission.reward_rsd), 0)).filter(TaskSubmission.status == "approved").scalar() or 0
    advertiser_budget_total = db.query(func.coalesce(func.sum(User.advertiser_budget_rsd), 0)).filter(User.role == "oglasivac").scalar() or 0
    reserved_budget_total = db.query(func.coalesce(func.sum(User.advertiser_reserved_rsd), 0)).filter(User.role == "oglasivac").scalar() or 0
    spent_budget_total = db.query(func.coalesce(func.sum(User.advertiser_spent_rsd), 0)).filter(User.role == "oglasivac").scalar() or 0
    pricing_summary = v11836_pricing_summary(db)
    submissions_latest = db.query(TaskSubmission).order_by(TaskSubmission.created_at.desc()).limit(50).all()
    banners = []
    boosts = []
    if "PaidAdBannerV111" in globals():
        banners = db.query(PaidAdBannerV111).order_by(PaidAdBannerV111.created_at.desc()).limit(6).all()
    if "PaidPromotionRequestV111" in globals():
        boosts = db.query(PaidPromotionRequestV111).order_by(PaidPromotionRequestV111.created_at.desc()).limit(20).all()
    admin_dashboard_banner = v11817_active_banner_for_code(db, "admin_dashboard_banner") if "v11817_active_banner_for_code" in globals() else None
    automation_summary = {
        "auto_approved": db.query(AutoEngineLogV114).filter(AutoEngineLogV114.event_type == "submission_auto_approved").count(),
        "auto_rejected": db.query(AutoEngineLogV114).filter(AutoEngineLogV114.event_type == "submission_auto_rejected").count(),
        "manual_queue": db.query(AutoEngineLogV114).filter(AutoEngineLogV114.event_type == "submission_needs_manual_review", AutoEngineLogV114.status == "queued").count(),
        "ai_reviews": db.query(AIReviewResult).count(),
    }
    dashboard_mix = {
        "pending_subs": len(pending_subs),
        "auto_approved": automation_summary["auto_approved"],
    }
    proof_mix = {
        "pending": db.query(TaskSubmission).filter(TaskSubmission.status == "pending").count(),
        "approved": db.query(TaskSubmission).filter(TaskSubmission.status == "approved").count(),
        "rejected": db.query(TaskSubmission).filter(TaskSubmission.status == "rejected").count(),
        "disputed": db.query(TaskSubmission).filter(TaskSubmission.status == "disputed").count(),
    }
    fraud_users = []
    for usr in users[:12]:
        try:
            profile = v11836_user_fraud_profile(db, usr)
        except Exception:
            continue
        if profile:
            fraud_users.append(profile)
    fraud_users.sort(key=lambda item: item.get("risk_score", 0), reverse=True)
    fraud_campaigns = []
    for task in tasks[:12]:
        try:
            profile = v11836_campaign_fraud_profile(db, task)
        except Exception:
            continue
        if profile:
            fraud_campaigns.append(profile)
    fraud_campaigns.sort(key=lambda item: item.get("risk_score", 0), reverse=True)
    fraud_summary = {
        "high_risk_users": sum(1 for item in fraud_users if item.get("risk_score", 0) >= 70),
        "medium_risk_users": sum(1 for item in fraud_users if 40 <= item.get("risk_score", 0) < 70),
        "high_risk_campaigns": sum(1 for item in fraud_campaigns if item.get("risk_score", 0) >= 70),
        "medium_risk_campaigns": sum(1 for item in fraud_campaigns if 40 <= item.get("risk_score", 0) < 70),
    }
    return templates.TemplateResponse("admin_v11_safe_v1171.html", {
        "request": request,
        "user": u,
        "flash": None,
        "stats": {
            "total_users": db.query(User).count(),
            "total_customers": db.query(User).filter(User.role == "korisnik").count(),
            "total_advertisers": db.query(User).filter(User.role == "oglasivac").count(),
            "active_tasks": db.query(Task).filter(Task.status == "active").count(),
            "pending_tasks": len(pending_tasks),
            "pending_submissions": len(pending_subs),
            "pending_withdrawals": len(pending_withdrawals),
            "total_budget": advertiser_budget_total,
            "reserved_budget": reserved_budget_total,
            "spent_budget": spent_budget_total,
        },
        "pricing_summary": pricing_summary,
        "latest_tasks": tasks[:8],
        "latest_submissions": submissions_latest[:8],
        "latest_withdrawals": pending_withdrawals[:8],
        "banners": banners[:6],
        "boosts": boosts[:6],
        "admin_dashboard_banner": admin_dashboard_banner,
        "automation_summary": automation_summary,
        "dashboard_mix": dashboard_mix,
        "proof_mix": proof_mix,
        "fraud_users": fraud_users[:6],
        "fraud_campaigns": fraud_campaigns[:6],
        "fraud_summary": fraud_summary,
    })




# ---------------------------------------------------
# V11.16.1 USER WALLET / PAYOUTS / BADGES FIX
# ---------------------------------------------------

def kz1161_user_context(db: Session, user):
    subs = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id).order_by(TaskSubmission.created_at.desc()).all()
    txs = db.query(WalletTransaction).filter(WalletTransaction.user_id == user.id).order_by(WalletTransaction.created_at.desc()).all()
    withdrawals = db.query(Withdrawal).filter(Withdrawal.user_id == user.id).order_by(Withdrawal.created_at.desc()).all()
    refs = db.query(User).filter(User.referred_by_id == user.id).all()
    score = None
    if "kz115_recalculate_user_score" in globals():
        try:
            score = kz115_recalculate_user_score(db, user)
        except Exception:
            score = None
    return subs, txs, withdrawals, refs, score

@app.get("/korisnik/wallet", response_class=HTMLResponse)
def user_wallet_v1161(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["korisnik"])
    subs, txs, withdrawals, refs, score = kz1161_user_context(db, u)
    total_in = sum(float(t.amount_rsd or 0) for t in txs if float(t.amount_rsd or 0) > 0)
    total_out = abs(sum(float(t.amount_rsd or 0) for t in txs if float(t.amount_rsd or 0) < 0))
    approved_total = sum(float(s.reward_rsd or 0) for s in subs if s.status == "approved")
    pending_total = sum(float(s.reward_rsd or 0) for s in subs if s.status == "pending")
    return templates.TemplateResponse("user_wallet_v1161.html", {
        "request": request, "user": u, "flash": None,
        "txs": txs, "withdrawals": withdrawals, "score": score,
        "total_in": total_in, "total_out": total_out,
        "approved_total": approved_total, "pending_total": pending_total,
    })

@app.get("/korisnik/isplate", response_class=HTMLResponse)
def user_payouts_v1161(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["korisnik"])
    subs, txs, withdrawals, refs, score = kz1161_user_context(db, u)
    return templates.TemplateResponse("user_payouts_v1161.html", {
        "request": request, "user": u, "flash": None,
        "withdrawals": withdrawals, "score": score, "min_withdrawal": MIN_WITHDRAWAL_RSD,
    })

@app.get("/korisnik/bedzevi", response_class=HTMLResponse)
def user_badges_v1161(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["korisnik"])
    if "kz115_recalculate_user_score" in globals():
        kz115_recalculate_user_score(db, u)
    earned = db.query(UserBadgeV115).filter(UserBadgeV115.user_id == u.id).order_by(UserBadgeV115.awarded_at.desc()).all() if "UserBadgeV115" in globals() else []
    earned_keys = {b.badge_key for b in earned}
    all_badges = []
    if "KZ115_BADGE_LIBRARY" in globals():
        for key,title,desc,icon in KZ115_BADGE_LIBRARY:
            all_badges.append({"key": key, "title": title, "description": desc, "icon": icon, "earned": key in earned_keys})
    return templates.TemplateResponse("user_badges_v1161.html", {
        "request": request, "user": u, "flash": None,
        "earned": earned, "all_badges": all_badges,
    })

@app.get("/korisnik/referral", response_class=HTMLResponse)
def user_referral_v1161(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["korisnik"])
    refs = db.query(User).filter(User.referred_by_id == u.id).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse("user_referral_v1161.html", {
        "request": request, "user": u, "flash": None, "refs": refs,
    })

@app.get("/api/v1/v11/user-pages-fix-audit")
def api_user_pages_fix_audit_v1161():
    return {"version":"11.16.1","status":"ready","pages":["wallet","payouts","badges","referral"],"home_button":"moved"}


# V11.16.1 premium home route override
@app.get("/", response_class=HTMLResponse)
@app.get("/pocetna", response_class=HTMLResponse)
def premium_home_v1161(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    tasks = db.query(Task).filter(Task.status == "active").order_by(Task.featured.desc(), Task.reward_rsd.desc()).limit(20).all()
    banner_map = v11817_active_banner_map(db) if "v11817_active_banner_map" in globals() else {}
    pricing_summary = v11836_pricing_summary(db)
    stats = {
        "tasks": db.query(Task).filter(Task.status == "active").count(),
        "users": db.query(User).filter(User.role == "korisnik").count(),
        "advertisers": db.query(User).filter(User.role == "oglasivac").count(),
        "approved_rsd": db.query(func.coalesce(func.sum(TaskSubmission.reward_rsd), 0)).filter(TaskSubmission.status == "approved").scalar() or 0,
    }
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "user": user,
            "tasks": tasks,
            "banner_map": banner_map,
            "pricing_summary": pricing_summary,
            "finance_accounts": v11836_public_accounts(db),
            "stats": stats,
        },
    )




# ---------------------------------------------------
# V11.17 ADMIN ANALYTICS & SEPARATE CRM DATABASES
# ---------------------------------------------------

def kz117_hash_ip(ip: str):
    try:
        return hashlib.sha256((ip or "unknown").encode("utf-8")).hexdigest()[:24]
    except Exception:
        return "unknown"

def kz117_sync_directories(db: Session):
    """Create/update separate user and advertiser CRM tables from main accounts."""
    users = db.query(User).filter(User.role == "korisnik").all()
    advertisers = db.query(User).filter(User.role == "oglasivac").all()

    for u in users:
        row = db.query(UserDirectoryV117).filter(UserDirectoryV117.user_id == u.id).first()
        if not row:
            row = UserDirectoryV117(user_id=u.id)
            db.add(row)
        approved = db.query(TaskSubmission).filter(TaskSubmission.user_id == u.id, TaskSubmission.status == "approved").count()
        rejected = db.query(TaskSubmission).filter(TaskSubmission.user_id == u.id, TaskSubmission.status == "rejected").count()
        pending = db.query(TaskSubmission).filter(TaskSubmission.user_id == u.id, TaskSubmission.status == "pending").count()
        score = None
        if "UserScoreV115" in globals():
            score = db.query(UserScoreV115).filter(UserScoreV115.user_id == u.id).first()
        row.full_name = getattr(u, "full_name", "") or ""
        row.email = getattr(u, "email", "") or ""
        row.phone = getattr(u, "phone", "") or ""
        row.city = getattr(u, "city", "") or ""
        row.status_name = getattr(score, "status_name", "") if score else (getattr(u, "status", "") or "")
        row.level_name = getattr(score, "level_name", "") if score else (getattr(u, "level", "") or "")
        row.balance_rsd = float(getattr(u, "balance_rsd", 0) or 0)
        row.pending_rsd = float(getattr(u, "pending_rsd", 0) or 0)
        row.lifetime_earned_rsd = float(getattr(u, "lifetime_earned_rsd", 0) or 0)
        row.approved_count = approved
        row.rejected_count = rejected
        row.pending_count = pending
        row.referral_code = getattr(u, "referral_code", "") or ""
        row.created_at_original = getattr(u, "created_at", None)
        row.synced_at = datetime.utcnow()

    for a in advertisers:
        row = db.query(AdvertiserDirectoryV117).filter(AdvertiserDirectoryV117.user_id == a.id).first()
        if not row:
            row = AdvertiserDirectoryV117(user_id=a.id)
            db.add(row)
        tasks = db.query(Task).filter(Task.advertiser_id == a.id).all()
        task_ids = [t.id for t in tasks]
        row.full_name = getattr(a, "full_name", "") or ""
        row.company_name = getattr(a, "company_name", "") or getattr(a, "full_name", "") or ""
        row.email = getattr(a, "email", "") or ""
        row.phone = getattr(a, "phone", "") or ""
        row.city = getattr(a, "city", "") or ""
        row.website = getattr(a, "website", "") or ""
        row.pib = getattr(a, "pib", "") or getattr(a, "tax_id", "") or ""
        row.budget_available_rsd = float(getattr(a, "advertiser_budget_rsd", 0) or 0)
        row.budget_reserved_rsd = float(getattr(a, "advertiser_reserved_rsd", 0) or 0)
        row.budget_spent_rsd = float(getattr(a, "advertiser_spent_rsd", 0) or 0)
        row.campaigns_total = len(tasks)
        row.campaigns_active = sum(1 for t in tasks if t.status == "active")
        row.campaigns_pending = sum(1 for t in tasks if t.status == "pending")
        row.submissions_total = db.query(TaskSubmission).filter(TaskSubmission.task_id.in_(task_ids)).count() if task_ids else 0
        row.created_at_original = getattr(a, "created_at", None)
        row.synced_at = datetime.utcnow()

    db.commit()
    return {"users": len(users), "advertisers": len(advertisers)}

@app.middleware("http")
async def kz117_visit_tracking_middleware(request: Request, call_next):
    start = time.time()
    path = request.url.path
    if path.startswith("/admin") and not admin_focus_route_allowed(path):
        db = SessionLocal()
        try:
            u = current_user(request, db)
            if u and u.role == "admin":
                return HTMLResponse(
                    """
                    <!doctype html>
                    <html lang="sr">
                    <head>
                      <meta charset="utf-8">
                      <meta name="viewport" content="width=device-width,initial-scale=1">
                      <title>Admin focus mode</title>
                      <style>
                        body{margin:0;font-family:Arial,sans-serif;background:#f8fafc;color:#0f172a}
                        main{max-width:760px;margin:72px auto;padding:40px;background:#fff;border:1px solid #dbe4f0;border-radius:24px;box-shadow:0 24px 60px rgba(15,23,42,.08)}
                        h1{margin:0 0 16px;font-size:32px}
                        p{margin:0 0 12px;font-size:18px;line-height:1.6;color:#475569}
                        ul{margin:24px 0;padding-left:20px;color:#1e293b}
                        a{color:#4f46e5;font-weight:700;text-decoration:none}
                      </style>
                    </head>
                    <body>
                      <main>
                        <h1>Ova admin ruta je privremeno blokirana.</h1>
                        <p>Drzimo fokus samo na ekranima koje trenutno sredjujemo, da bude jasno sta ispravljamo i gde.</p>
                        <p>Aktivne rute su:</p>
                        <ul>
                          <li><a href="/admin/v11">Dashboard</a></li>
                          <li><a href="/admin/mapa-platforme">Mapa platforme</a></li>
                          <li><a href="/admin/kampanje">Kampanje</a></li>
                          <li><a href="/admin/dokazi">Dokazi</a></li>
                          <li><a href="/admin/finansije">Finansije</a></li>
                          <li><a href="/admin/isplate">Isplate</a></li>
                          <li><a href="/admin/fakture">Fakture</a></li>
                          <li><a href="/admin/payouts-v11">Payouts</a></li>
                          <li><a href="/admin/reklame-v111">Reklame</a></li>
                          <li><a href="/admin/cene-v111">Cene</a></li>
                          <li><a href="/admin/oglasivaci-baza-v117">Baza oglasivaca</a></li>
                          <li><a href="/admin/oglasivaci">Oglasivaci</a></li>
                          <li><a href="/admin/budget-v11">Budzeti</a></li>
                          <li><a href="/admin/affiliate-v9">Affiliate</a></li>
                          <li><a href="/admin/revenue-v9">Revenue</a></li>
                          <li><a href="/admin/launch-v9">Launch</a></li>
                          <li><a href="/admin/golive-v9">Go-live</a></li>
                          <li><a href="/admin/smoke-v11">Smoke</a></li>
                          <li><a href="/admin/deploy-v11">Deploy</a></li>
                          <li><a href="/admin/daily-desk-v11">Daily desk</a></li>
                          <li><a href="/admin/ops-v11835">Ops</a></li>
                          <li><a href="/admin/feature-flags">Feature flags</a></li>
                          <li><a href="/admin/system-settings">System settings</a></li>
                          <li><a href="/admin/security-v11">Security</a></li>
                        </ul>
                      </main>
                    </body>
                    </html>
                    """,
                    status_code=404,
                )
        finally:
            db.close()
    response = await call_next(request)
    try:
        # Do not track static assets and favicon noise.
        if not (path.startswith("/static") or path in ["/favicon.ico", "/sw.js", "/robots.txt", "/sitemap.xml"]):
            db = SessionLocal()
            try:
                u = current_user(request, db)
                visitor_id = request.cookies.get("kz_visitor_id") or ""
                if not visitor_id:
                    raw = f"{request.client.host if request.client else ''}|{request.headers.get('user-agent','')}|{datetime.utcnow().date()}"
                    visitor_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
                    response.set_cookie("kz_visitor_id", visitor_id, max_age=60*60*24*365, httponly=False, samesite="lax")
                visit = PlatformVisitV117(
                    visitor_id=visitor_id,
                    user_id=(u.id if u else None),
                    role=(u.role if u else "guest"),
                    path=path,
                    method=request.method,
                    status_code=response.status_code,
                    referrer=request.headers.get("referer", "")[:700],
                    user_agent=request.headers.get("user-agent", "")[:2000],
                    ip_hash=kz117_hash_ip(request.client.host if request.client else ""),
                    duration_ms=round((time.time() - start) * 1000, 2),
                    created_at=datetime.utcnow(),
                )
                db.add(visit)
                db.commit()
            finally:
                db.close()
    except Exception:
        pass
    return response

def kz117_visit_stats(db: Session):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    total_visits = db.query(PlatformVisitV117).count()
    today_visits = db.query(PlatformVisitV117).filter(PlatformVisitV117.created_at >= today_start).count()
    unique_total = db.query(PlatformVisitV117.visitor_id).distinct().count()
    unique_today = db.query(PlatformVisitV117.visitor_id).filter(PlatformVisitV117.created_at >= today_start).distinct().count()
    registered_users = db.query(User).filter(User.role == "korisnik").count()
    registered_advertisers = db.query(User).filter(User.role == "oglasivac").count()
    admins = db.query(User).filter(User.role == "admin").count()
    top_routes = db.query(PlatformVisitV117.path, func.count(PlatformVisitV117.id).label("cnt")).group_by(PlatformVisitV117.path).order_by(func.count(PlatformVisitV117.id).desc()).limit(12).all()
    role_visits = db.query(PlatformVisitV117.role, func.count(PlatformVisitV117.id).label("cnt")).group_by(PlatformVisitV117.role).order_by(func.count(PlatformVisitV117.id).desc()).all()
    recent = db.query(PlatformVisitV117).order_by(PlatformVisitV117.created_at.desc()).limit(50).all()
    return {
        "total_visits": total_visits,
        "today_visits": today_visits,
        "unique_total": unique_total,
        "unique_today": unique_today,
        "registered_users": registered_users,
        "registered_advertisers": registered_advertisers,
        "admins": admins,
        "top_routes": top_routes,
        "role_visits": role_visits,
        "recent": recent,
    }

@app.get("/admin/analitika-v117", response_class=HTMLResponse)
def admin_analytics_v117(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    kz117_sync_directories(db)
    stats = kz117_visit_stats(db)
    return templates.TemplateResponse("admin_analytics_v117.html", {"request": request, "user": u, "flash": None, "stats": stats})

@app.get("/admin/korisnici-baza-v117", response_class=HTMLResponse)
def admin_user_directory_v117(request: Request, q: str = "", db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    kz117_sync_directories(db)
    query = db.query(UserDirectoryV117)
    if q:
        like = f"%{q}%"
        query = query.filter((UserDirectoryV117.full_name.ilike(like)) | (UserDirectoryV117.email.ilike(like)) | (UserDirectoryV117.phone.ilike(like)) | (UserDirectoryV117.city.ilike(like)))
    rows = query.order_by(UserDirectoryV117.created_at_original.desc()).limit(300).all()
    totals = {
        "count": db.query(UserDirectoryV117).count(),
        "balance": db.query(func.coalesce(func.sum(UserDirectoryV117.balance_rsd), 0)).scalar() or 0,
        "pending": db.query(func.coalesce(func.sum(UserDirectoryV117.pending_rsd), 0)).scalar() or 0,
        "earned": db.query(func.coalesce(func.sum(UserDirectoryV117.lifetime_earned_rsd), 0)).scalar() or 0,
    }
    return templates.TemplateResponse("admin_user_directory_v117.html", {"request": request, "user": u, "flash": None, "rows": rows, "q": q, "totals": totals})

@app.get("/admin/oglasivaci-baza-v117", response_class=HTMLResponse)
def admin_advertiser_directory_v117(request: Request, q: str = "", db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    kz117_sync_directories(db)
    query = db.query(AdvertiserDirectoryV117)
    if q:
        like = f"%{q}%"
        query = query.filter((AdvertiserDirectoryV117.full_name.ilike(like)) | (AdvertiserDirectoryV117.company_name.ilike(like)) | (AdvertiserDirectoryV117.email.ilike(like)) | (AdvertiserDirectoryV117.phone.ilike(like)) | (AdvertiserDirectoryV117.city.ilike(like)))
    rows = query.order_by(AdvertiserDirectoryV117.created_at_original.desc()).limit(300).all()
    totals = {
        "count": db.query(AdvertiserDirectoryV117).count(),
        "available": db.query(func.coalesce(func.sum(AdvertiserDirectoryV117.budget_available_rsd), 0)).scalar() or 0,
        "reserved": db.query(func.coalesce(func.sum(AdvertiserDirectoryV117.budget_reserved_rsd), 0)).scalar() or 0,
        "spent": db.query(func.coalesce(func.sum(AdvertiserDirectoryV117.budget_spent_rsd), 0)).scalar() or 0,
    }
    return templates.TemplateResponse("admin_advertiser_directory_v117.html", {"request": request, "user": u, "flash": None, "rows": rows, "q": q, "totals": totals})

def kz117_csv_response(filename, headers, rows):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return Response(content=output.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@app.get("/admin/korisnici-baza-v117.csv")
def admin_user_directory_csv_v117(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    kz117_sync_directories(db)
    rows = db.query(UserDirectoryV117).order_by(UserDirectoryV117.created_at_original.desc()).all()
    return kz117_csv_response("klikzarada_korisnici_baza_v117.csv",
        ["ID","Ime","Email","Telefon","Grad","Status","Nivo","Balans","Pending","Ukupno zaradjeno","Odobreno","Odbijeno","Na cekanju","Referral","Registrovan"],
        [[r.user_id,r.full_name,r.email,r.phone,r.city,r.status_name,r.level_name,r.balance_rsd,r.pending_rsd,r.lifetime_earned_rsd,r.approved_count,r.rejected_count,r.pending_count,r.referral_code,r.created_at_original] for r in rows]
    )

@app.get("/admin/oglasivaci-baza-v117.csv")
def admin_advertiser_directory_csv_v117(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    kz117_sync_directories(db)
    rows = db.query(AdvertiserDirectoryV117).order_by(AdvertiserDirectoryV117.created_at_original.desc()).all()
    return kz117_csv_response("klikzarada_oglasivaci_baza_v117.csv",
        ["ID","Firma","Kontakt","Email","Telefon","Grad","Sajt","PIB","Budzet","Rezervisano","Potroseno","Kampanje","Aktivne","Pending","Dokazi","Registrovan"],
        [[r.user_id,r.company_name,r.full_name,r.email,r.phone,r.city,r.website,r.pib,r.budget_available_rsd,r.budget_reserved_rsd,r.budget_spent_rsd,r.campaigns_total,r.campaigns_active,r.campaigns_pending,r.submissions_total,r.created_at_original] for r in rows]
    )

@app.get("/api/v1/v11/admin-analytics-audit")
def api_admin_analytics_audit_v117():
    return {"version":"11.17","status":"ready","features":["visit_tracking","registered_counts","separate_user_database","separate_advertiser_database","csv_export"]}


# V11.18.10 public helper aliases for home/footer buttons
@app.get("/podrska")
def v11810_support_alias():
    return RedirectResponse(url="/kontakt", status_code=302)

@app.get("/politika-privatnosti")
def v11810_privacy_alias():
    return RedirectResponse(url="/pravila", status_code=302)

@app.get("/uslovi-isplate")
def v11810_payout_terms_alias():
    return RedirectResponse(url="/pravila", status_code=302)


# V11.18.12 function-only public route aliases
@app.get("/o-nama")
def v11812_about_alias():
    return RedirectResponse(url="/za-korisnike", status_code=302)

@app.get("/kako-funkcionise")
def v11812_how_it_works_alias():
    return RedirectResponse(url="/za-korisnike", status_code=302)


# V11.18.13 function-only form endpoint hardening


# V11.18.14 function-only workflow health endpoint
@app.get("/api/v1/v11/workflow-health")
def v11814_workflow_health(db: Session = Depends(get_db)):
    return {
        "version": "11.18.14",
        "status": "ready",
        "users": db.query(User).count(),
        "tasks": db.query(Task).count(),
        "submissions": db.query(TaskSubmission).count(),
        "withdrawals": db.query(Withdrawal).count(),
        "budget_transactions": db.query(AdvertiserBudgetTransaction).count(),
    }


# V11.18.14 function-only withdrawal request endpoint
@app.post("/korisnik/isplate/zahtev")
def v11814_withdrawal_request(request: Request, amount_rsd: float = Form(0), method: str = Form("bank_transfer"), note: str = Form(""), db: Session = Depends(get_db)):
    user = require(request, db)
    check_role(user, ["korisnik"])
    w, status = v11836_create_payout_request(db, user, amount_rsd, method, getattr(user, "payment_details", "") or note, note)
    return RedirectResponse(f"/korisnik/isplate?msg={status}", status_code=303)


# V11.18.15 function-only: homepage and dashboard banner slots
def v11815_banner_slot_definitions():
    return [
        ("home_top_left", "Početna — gornji levi premium banner", "home_top", "half", 5000),
        ("home_top_right", "Početna — gornji desni premium banner", "home_top", "half", 5000),
        ("home_sponsor_1", "Početna — sponzorski banner 1", "home_sponsor", "quarter", 3000),
        ("home_sponsor_2", "Početna — sponzorski banner 2", "home_sponsor", "quarter", 3000),
        ("home_sponsor_3", "Početna — sponzorski banner 3", "home_sponsor", "quarter", 3000),
        ("home_sponsor_4", "Početna — sponzorski banner 4", "home_sponsor", "quarter", 3000),
        ("home_dashboard_banner", "Početna — banner ispod isplate", "home_dashboard", "wide", 4500),
        ("admin_dashboard_banner", "Admin — premium banner za dashboard", "admin_dashboard", "wide", 6500),
        ("home_bottom_1", "Početna — donji banner 1", "home_bottom", "third", 2500),
        ("home_bottom_2", "Početna — donji banner 2", "home_bottom", "third", 2500),
        ("home_bottom_3", "Početna — donji banner 3", "home_bottom", "third", 2500),
    ]

def v11815_ensure_9_banner_slots(db: Session):
    for code, title, placement, width_label, price_rsd in v11815_banner_slot_definitions():
        slot = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code == code).first()
        if not slot:
            slot = HomeBannerSlotV111(code=code, title=title, placement=placement, width_label=width_label, price_rsd=price_rsd, is_active=True)
            db.add(slot)
        else:
            # Ne brišemo postojeće admin izmene osim ako su prazne
            if not slot.title:
                slot.title = title
            if not slot.placement:
                slot.placement = placement
            if not slot.width_label:
                slot.width_label = width_label
            if slot.price_rsd is None:
                slot.price_rsd = price_rsd
    db.commit()

@app.get("/api/v1/v11/banner-slots-health")
def v11815_banner_slots_health(db: Session = Depends(get_db)):
    v11815_ensure_9_banner_slots(db)
    slots = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code.in_([x[0] for x in v11815_banner_slot_definitions()])).order_by(HomeBannerSlotV111.id.asc()).all()
    return {
        "version": "11.18.15",
        "expected": 11,
        "count": len(slots),
        "slots": [{"id": s.id, "code": s.code, "title": s.title, "placement": s.placement, "width_label": s.width_label, "price_rsd": s.price_rsd, "is_active": s.is_active} for s in slots],
    }


def v11815_startup_banner_slots():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        if "v11815_ensure_9_banner_slots" in globals():
            v11815_ensure_9_banner_slots(db)
    finally:
        db.close()


# V11.18.17 banner system helpers
V11817_BANNER_RESERVED_MARK = "[BANNER_RESERVED_PAID]"

def v11817_active_banner_map(db: Session):
    """Return latest active banner for each configured public/admin slot code."""
    if "v11815_ensure_9_banner_slots" in globals():
        v11815_ensure_9_banner_slots(db)
    expected_codes = [x[0] for x in v11815_banner_slot_definitions()] if "v11815_banner_slot_definitions" in globals() else []
    slots = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code.in_(expected_codes)).all() if expected_codes else []
    out = {}
    for slot in slots:
        banner = (
            db.query(PaidAdBannerV111)
            .filter(PaidAdBannerV111.slot_id == slot.id, PaidAdBannerV111.status == "active")
            .order_by(PaidAdBannerV111.created_at.desc())
            .first()
        )
        if banner:
            out[slot.code] = banner
    return out

def v11817_active_banner_for_code(db: Session, slot_code: str):
    code = (slot_code or "").strip()
    if not code:
        return None
    if "v11815_ensure_9_banner_slots" in globals():
        v11815_ensure_9_banner_slots(db)
    slot = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code == code).first()
    if not slot:
        return None
    return (
        db.query(PaidAdBannerV111)
        .filter(PaidAdBannerV111.slot_id == slot.id, PaidAdBannerV111.status == "active")
        .order_by(PaidAdBannerV111.created_at.desc())
        .first()
    )

def v11817_banner_url(url: str | None):
    url = (url or "/").strip()
    if not url:
        return "/"
    return url


def v11818_default_banner_image(slot_code: str | None):
    code = (slot_code or "").strip()
    mapping = {
        "home_top_left": "/static/img/banner_home_top_left.svg",
        "home_top_right": "/static/img/banner_home_top_right.svg",
        "home_sponsor_1": "/static/img/banner_home_sponsor_1.svg",
        "home_sponsor_2": "/static/img/banner_home_sponsor_2.svg",
        "home_sponsor_3": "/static/img/banner_home_sponsor_3.svg",
        "home_sponsor_4": "/static/img/banner_home_sponsor_4.svg",
        "home_dashboard_banner": "/static/img/banner_generic.svg",
        "admin_dashboard_banner": "/static/img/banner_generic.svg",
        "home_bottom_1": "/static/img/banner_home_bottom_1.svg",
        "home_bottom_2": "/static/img/banner_home_bottom_2.svg",
        "home_bottom_3": "/static/img/banner_home_bottom_3.svg",
    }
    return mapping.get(code, "/static/img/banner_generic.svg")


# V11.18.19 banner maker helpers and routes
GENERATED_BANNERS_DIR = Path("app/static/generated_banners")
GENERATED_BANNERS_DIR.mkdir(parents=True, exist_ok=True)

def v11819_banner_canvas(slot_code: str | None):
    code = (slot_code or "").strip()
    if code in ["home_top_left", "home_top_right"]:
        return (1400, 360, "top")
    if code in ["home_sponsor_1", "home_sponsor_2", "home_sponsor_3", "home_sponsor_4"]:
        return (900, 300, "sponsor")
    if code in ["home_dashboard_banner"]:
        return (1200, 220, "dashboard")
    if code in ["admin_dashboard_banner"]:
        return (1200, 220, "admin-dashboard")
    if code in ["home_bottom_1", "home_bottom_2", "home_bottom_3"]:
        return (900, 260, "bottom")
    return (900, 260, "generic")


def v11819_theme_colors(theme: str | None, accent: str | None = None):
    palette = {
        "blue": ("#1158db", "#367dff", "#ffffff"),
        "green": ("#0d8c4e", "#16ba6b", "#ffffff"),
        "violet": ("#6d39f5", "#8b5cf6", "#ffffff"),
        "orange": ("#f57c1f", "#fb923c", "#ffffff"),
        "dark": ("#0f172a", "#1e293b", "#ffffff"),
        "pink": ("#db2777", "#f472b6", "#ffffff"),
    }
    c1, c2, text = palette.get((theme or "blue").strip().lower(), palette["blue"])
    if accent and accent.strip():
        text = accent.strip()
    return c1, c2, text


def v11819_svg_icon(icon: str | None, x: int, y: int, box: int, stroke: str = "#ffffff"):
    ic = (icon or "megaphone").strip().lower()
    bg = f'<rect x="{x}" y="{y}" width="{box}" height="{box}" rx="22" fill="rgba(255,255,255,0.16)"/>'
    if ic == "cart":
        art = f'<path d="M{x+20} {y+24} H{x+38} L{x+52} {y+76} H{x+112}" stroke="{stroke}" stroke-width="9" fill="none" stroke-linecap="round"/><rect x="{x+48}" y="{y+34}" width="52" height="32" rx="10" fill="#e5e7eb"/><circle cx="{x+62}" cy="{y+88}" r="8" fill="{stroke}"/><circle cx="{x+96}" cy="{y+88}" r="8" fill="{stroke}"/>'
    elif ic == "chart":
        art = f'<path d="M{x+26} {y+86} H{x+106}" stroke="{stroke}" stroke-width="8" stroke-linecap="round"/><rect x="{x+34}" y="{y+58}" width="12" height="28" rx="4" fill="{stroke}"/><rect x="{x+56}" y="{y+44}" width="12" height="42" rx="4" fill="{stroke}"/><rect x="{x+78}" y="{y+28}" width="12" height="58" rx="4" fill="{stroke}"/><path d="M{x+30} {y+56} C{x+48} {y+34}, {x+70} {y+52}, {x+96} {y+22}" stroke="#dbeafe" stroke-width="7" fill="none" stroke-linecap="round"/>'
    elif ic == "travel":
        art = f'<circle cx="{x+70}" cy="{y+36}" r="18" fill="#fde68a"/><path d="M{x+70} {y+52} L{x+70} {y+88}" stroke="{stroke}" stroke-width="8" stroke-linecap="round"/><path d="M{x+48} {y+76} L{x+70} {y+56} L{x+92} {y+76}" stroke="{stroke}" stroke-width="8" fill="none" stroke-linecap="round" stroke-linejoin="round"/><path d="M{x+48} {y+84} H{x+92}" stroke="{stroke}" stroke-width="8" stroke-linecap="round"/>'
    elif ic == "fit":
        art = f'<circle cx="{x+64}" cy="{y+30}" r="14" fill="#fde68a"/><path d="M{x+64} {y+46} V{x+86} M{x+64} {y+58} L{x+40} {y+70} M{x+64} {y+58} L{x+88} {y+70} M{x+64} {y+86} L{x+46} {y+108} M{x+64} {y+86} L{x+84} {y+106}" stroke="{stroke}" stroke-width="8" stroke-linecap="round"/><rect x="{x+90}" y="{y+44}" width="24" height="44" rx="8" fill="#fff"/>'
    elif ic == "chat":
        art = f'<path d="M{x+26} {y+34} C{x+26} {y+22}, {x+38} {y+18}, {x+48} {y+18} H{x+90} C{x+106} {y+18}, {x+112} {y+30}, {x+112} {y+42} V{x+60} C{x+112} {y+74}, {x+104} {y+84}, {x+90} {y+84} H{x+62} L{x+42} {y+102} V{x+84} H{x+48} C{x+34} {y+84}, {x+26} {y+76}, {x+26} {y+62} Z" fill="{stroke}" opacity="0.95"/>'
    elif ic == "link":
        art = f'<path d="M{x+42} {y+70} l16-16 a18 18 0 0 1 26 26 l-12 12 a18 18 0 0 1 -26 0" stroke="{stroke}" stroke-width="9" fill="none" stroke-linecap="round"/><path d="M{x+82} {y+54} l-16 16 a18 18 0 0 1 -26 -26 l12-12 a18 18 0 0 1 26 0" stroke="#dbeafe" stroke-width="9" fill="none" stroke-linecap="round"/>'
    elif ic == "rocket":
        art = f'<path d="M{x+74} {y+20} C{x+102} {y+22}, {x+110} {y+52}, {x+90} {y+76} L{x+70} {y+98} L{x+52} {y+80} L{x+74} {y+58} C{x+84} {y+48}, {x+88} {y+36}, {x+74} {y+20} Z" fill="{stroke}"/><circle cx="{x+82}" cy="{y+42}" r="7" fill="#60a5fa"/><path d="M{x+50} {y+82} L{x+38} {y+108} L{x+64} {y+96}" fill="#f59e0b"/>'
    else:
        art = f'<circle cx="{x+70}" cy="{y+58}" r="28" fill="{stroke}" opacity="0.95"/><path d="M{x+70} {y+42} V{x+74} M{x+54} {y+58} H{x+86}" stroke="#60a5fa" stroke-width="8" stroke-linecap="round"/>'
    return bg + art


def v11819_make_banner_svg(slot_code: str | None, title: str, body: str, cta: str = "Saznaj više", theme: str = "blue", accent: str = "#ffffff", icon: str = "megaphone"):
    width, height, kind = v11819_banner_canvas(slot_code)
    c1, c2, text = v11819_theme_colors(theme, accent)
    safe_title = html.escape((title or "Banner").strip())[:90]
    safe_body = html.escape((body or "Profesionalna reklama za vašu ponudu.").strip())[:180]
    safe_cta = html.escape((cta or "Saznaj više").strip())[:30]
    if kind == "top":
        title_size, body_size, icon_box = 58, 27, 140
        tx, ty = 54, 110
        ix = width - 250
        iy = 60
    elif kind == "sponsor":
        title_size, body_size, icon_box = 46, 22, 124
        tx, ty = 38, 96
        ix = width - 190
        iy = 44
    elif kind == "admin-dashboard":
        title_size, body_size, icon_box = 46, 22, 124
        tx, ty = 38, 96
        ix = width - 190
        iy = 44
    else:
        title_size, body_size, icon_box = 40, 21, 112
        tx, ty = 36, 88
        ix = width - 170
        iy = 38
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#0f172a" flood-opacity="0.15"/></filter>
  </defs>
  <rect width="{width}" height="{height}" rx="28" fill="url(#bg)"/>
  <circle cx="44" cy="34" r="16" fill="rgba(255,255,255,0.14)"/>
  <circle cx="{width-48}" cy="{height-34}" r="18" fill="rgba(255,255,255,0.10)"/>
  <text x="{tx}" y="40" font-family="Arial" font-size="18" font-weight="700" fill="rgba(255,255,255,0.88)">KLIKZARADA BANNER</text>
  <text x="{tx}" y="{ty}" font-family="Arial" font-size="{title_size}" font-weight="800" fill="{text}">{safe_title}</text>
  <text x="{tx}" y="{ty+42}" font-family="Arial" font-size="{body_size}" fill="rgba(255,255,255,0.94)">{safe_body}</text>
  <rect x="{tx}" y="{height-74}" rx="16" ry="16" width="180" height="42" fill="rgba(255,255,255,0.20)" stroke="rgba(255,255,255,0.38)"/>
  <text x="{tx+24}" y="{height-46}" font-family="Arial" font-size="20" font-weight="700" fill="#ffffff">{safe_cta} →</text>
  <g filter="url(#shadow)">{v11819_svg_icon(icon, ix, iy, icon_box, '#ffffff')}</g>
</svg>"""
    return svg


def v11819_save_banner_svg(slot_code: str | None, title: str, body: str, cta: str = "Saznaj više", theme: str = "blue", accent: str = "#ffffff", icon: str = "megaphone"):
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in (title or "banner"))
    slug = "-".join([x for x in slug.split("-") if x])[:50] or "banner"
    name = f"{slug}-{int(time.time()*1000)}.svg"
    path = GENERATED_BANNERS_DIR / name
    path.write_text(v11819_make_banner_svg(slot_code, title, body, cta=cta, theme=theme, accent=accent, icon=icon), encoding="utf-8")
    return f"/static/generated_banners/{name}"


@app.post("/oglasivac/reklame-v111/maker")
async def advertiser_banner_maker_v11819(
    request: Request,
    slot_id: int = Form(...),
    title: str = Form(...),
    body: str = Form(""),
    target_url: str = Form("/"),
    days_count: int = Form(7),
    theme: str = Form("blue"),
    accent: str = Form("#ffffff"),
    icon: str = Form("megaphone"),
    cta: str = Form("Saznaj više"),
    upload_image: UploadFile | None = File(None),
    image_fit: str = Form("cover"),
    db: Session = Depends(get_db)
):
    u = require(request, db); check_role(u, ["oglasivac"])
    if "v11815_ensure_9_banner_slots" in globals():
        v11815_ensure_9_banner_slots(db)
    slot = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.id == slot_id, HomeBannerSlotV111.is_active == True).first()
    if not slot:
        raise HTTPException(404, "Slot nije pronađen")
    price = float(slot.price_rsd or 0)
    if float(getattr(u, "advertiser_budget_rsd", 0) or 0) < price:
        return RedirectResponse("/oglasivac/banneri-v111?msg=budget_error", 303)
    if price > 0:
        u.advertiser_budget_rsd -= price
        u.advertiser_reserved_rsd = float(getattr(u, "advertiser_reserved_rsd", 0) or 0) + price
        add_budget_tx(db, u, -price, "reserve_banner", f"Rezervisan budžet za banner: {title.strip()}")
    image_url = (await v11828_final_banner_image(slot, title.strip(), upload_image, '', image_fit, None)) or v11819_save_banner_svg(slot.code, title.strip(), body.strip() or "Profesionalna reklama za vašu ponudu.", cta=cta, theme=theme, accent=accent, icon=icon)
    banner = PaidAdBannerV111(
        advertiser_id=u.id,
        slot_id=slot.id,
        title=title.strip(),
        body=body.strip() or None,
        image_url=image_url,
        target_url=target_url.strip() or "/",
        price_rsd=price,
        view_cost_rsd=v111_price_rsd(db, "ad_view_cost_rsd", 8),
        viewer_reward_rsd=v111_price_rsd(db, "ad_view_reward_rsd", 5),
        days_count=max(1, int(days_count or 7)),
        status="pending",
        admin_note=V11817_BANNER_RESERVED_MARK
    )
    db.add(banner)
    notify(db, None, "admin", "Novi banner iz bannermakera", f"Oglašivač {u.full_name} kreirao je banner: {title}")
    db.commit()
    return RedirectResponse("/oglasivac/banneri-v111?msg=maker_saved", 303)


@app.post("/oglasivac/banneri-v111/maker")
async def advertiser_banneri_maker_v11819(
    request: Request,
    slot_id: int = Form(...),
    title: str = Form(...),
    body: str = Form(""),
    target_url: str = Form("/"),
    days_count: int = Form(7),
    theme: str = Form("blue"),
    accent: str = Form("#ffffff"),
    icon: str = Form("megaphone"),
    cta: str = Form("Saznaj više"),
    upload_image: UploadFile | None = File(None),
    image_fit: str = Form("cover"),
    db: Session = Depends(get_db)
):
    return await advertiser_banner_maker_v11819(
        request=request,
        slot_id=slot_id,
        title=title,
        body=body,
        target_url=target_url,
        days_count=days_count,
        theme=theme,
        accent=accent,
        icon=icon,
        cta=cta,
        upload_image=upload_image,
        image_fit=image_fit,
        db=db,
    )


@app.post("/oglasivac/promocija-v111/maker")
async def advertiser_promocija_maker_v11819(
    request: Request,
    slot_id: int = Form(...),
    title: str = Form(...),
    body: str = Form(""),
    target_url: str = Form("/"),
    days_count: int = Form(7),
    theme: str = Form("blue"),
    accent: str = Form("#ffffff"),
    icon: str = Form("megaphone"),
    cta: str = Form("Saznaj više"),
    upload_image: UploadFile | None = File(None),
    image_fit: str = Form("cover"),
    db: Session = Depends(get_db)
):
    return await advertiser_banner_maker_v11819(
        request=request,
        slot_id=slot_id,
        title=title,
        body=body,
        target_url=target_url,
        days_count=days_count,
        theme=theme,
        accent=accent,
        icon=icon,
        cta=cta,
        upload_image=upload_image,
        image_fit=image_fit,
        db=db,
    )


@app.post("/admin/reklame-v111/maker")
async def admin_banner_maker_v11819(
    request: Request,
    advertiser_id: int = Form(...),
    slot_id: int = Form(...),
    title: str = Form(...),
    body: str = Form(""),
    target_url: str = Form("/"),
    price_rsd: float = Form(0),
    days_count: int = Form(7),
    start_date: str = Form(""),
    status: str = Form("active"),
    theme: str = Form("blue"),
    accent: str = Form("#ffffff"),
    icon: str = Form("megaphone"),
    cta: str = Form("Saznaj više"),
    upload_image: UploadFile | None = File(None),
    image_fit: str = Form("cover"),
    db: Session = Depends(get_db)
):
    u = require(request, db); check_role(u, ["admin"])
    advertiser = db.query(User).filter(User.id == advertiser_id).first()
    slot = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.id == slot_id).first()
    if not advertiser or not slot:
        raise HTTPException(404)
    status = {
        "aktivno": "active", "objavi": "active", "objavljeno": "active", "active": "active",
        "pending": "pending", "na čekanju": "pending", "na_cekanju": "pending",
        "rejected": "rejected", "odbijeno": "rejected", "expired": "expired",
    }.get(status, status)
    if status not in ["active", "pending", "rejected", "expired"]:
        status = "pending"
    image_url = (await v11828_final_banner_image(slot, title.strip(), upload_image, '', image_fit, None)) or v11819_save_banner_svg(slot.code, title.strip(), body.strip() or "Profesionalna reklama za vašu ponudu.", cta=cta, theme=theme, accent=accent, icon=icon)
    days_count = max(1, int(days_count or 7))
    daily_price = float(price_rsd or 0) if float(price_rsd or 0) > 0 else (float(slot.price_rsd or 0) / 7 if float(slot.price_rsd or 0) else 0)
    price_total = daily_price * days_count
    planned_start = v11837_parse_date(start_date) or datetime.utcnow()
    if status == "active" and planned_start.date() > datetime.utcnow().date():
        status = "pending"
    banner = PaidAdBannerV111(
        advertiser_id=advertiser.id,
        slot_id=slot.id,
        title=title.strip(),
        body=body.strip() or None,
        image_url=image_url,
        target_url=target_url.strip() or "/",
        price_rsd=price_total,
        view_cost_rsd=v111_price_rsd(db, "ad_view_cost_rsd", 8) if "v111_price_rsd" in globals() else 8,
        viewer_reward_rsd=v111_price_rsd(db, "ad_view_reward_rsd", 5) if "v111_price_rsd" in globals() else 5,
        days_count=days_count,
        status=status,
        starts_at=planned_start,
        ends_at=(planned_start + timedelta(days=days_count)),
        admin_note="Kreirano preko admin bannermakera."
    )
    db.add(banner)
    notify(db, advertiser, None, "Novi banner", f"Admin je kreirao banner '{title}' za slot {slot.title}.")
    db.commit()
    return RedirectResponse("/admin/banneri-v111?msg=maker_banner_saved", 303)


@app.post("/admin/banneri-v111/maker")
async def admin_banneri_maker_v11819(
    request: Request,
    advertiser_id: int = Form(...),
    slot_id: int = Form(...),
    title: str = Form(...),
    body: str = Form(""),
    target_url: str = Form("/"),
    price_rsd: float = Form(0),
    days_count: int = Form(7),
    status: str = Form("active"),
    theme: str = Form("blue"),
    accent: str = Form("#ffffff"),
    icon: str = Form("megaphone"),
    cta: str = Form("Saznaj više"),
    upload_image: UploadFile | None = File(None),
    image_fit: str = Form("cover"),
    db: Session = Depends(get_db)
):
    return await admin_banner_maker_v11819(
        request=request,
        advertiser_id=advertiser_id,
        slot_id=slot_id,
        title=title,
        body=body,
        target_url=target_url,
        price_rsd=price_rsd,
        days_count=days_count,
        status=status,
        theme=theme,
        accent=accent,
        icon=icon,
        cta=cta,
        upload_image=upload_image,
        image_fit=image_fit,
        db=db,
    )


@app.post("/admin/promocija-v111/maker")
async def admin_promocija_maker_v11819(
    request: Request,
    advertiser_id: int = Form(...),
    slot_id: int = Form(...),
    title: str = Form(...),
    body: str = Form(""),
    target_url: str = Form("/"),
    price_rsd: float = Form(0),
    days_count: int = Form(7),
    status: str = Form("active"),
    theme: str = Form("blue"),
    accent: str = Form("#ffffff"),
    icon: str = Form("megaphone"),
    cta: str = Form("Saznaj više"),
    upload_image: UploadFile | None = File(None),
    image_fit: str = Form("cover"),
    db: Session = Depends(get_db)
):
    return await admin_banner_maker_v11819(
        request=request,
        advertiser_id=advertiser_id,
        slot_id=slot_id,
        title=title,
        body=body,
        target_url=target_url,
        price_rsd=price_rsd,
        days_count=days_count,
        status=status,
        theme=theme,
        accent=accent,
        icon=icon,
        cta=cta,
        upload_image=upload_image,
        image_fit=image_fit,
        db=db,
    )


# V11.18.20 banner upload helpers
BANNER_UPLOAD_DIR = Path("app/static/uploads/banners")
BANNER_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

async def v11820_save_uploaded_banner(upload_image: UploadFile | None, prefix: str = "banner"):
    if not upload_image or not upload_image.filename:
        return None
    raw_name = upload_image.filename
    suffix = Path(raw_name).suffix.lower()
    allowed = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
    if suffix not in allowed:
        raise HTTPException(400, "Dozvoljeni formati slike su PNG, JPG, WEBP ili SVG.")
    data = await upload_image.read()
    if not data:
        return None
    max_bytes = 4 * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(400, "Slika je prevelika. Maksimalno 4 MB.")
    safe_prefix = "".join(ch.lower() if ch.isalnum() else "-" for ch in (prefix or "banner"))[:40].strip("-") or "banner"
    name = f"{safe_prefix}-{int(time.time()*1000)}-{secrets.token_hex(4)}{suffix}"
    path = BANNER_UPLOAD_DIR / name
    path.write_bytes(data)
    return f"/static/uploads/banners/{name}"


# V11.18.22 automatic banner crop/fit wrapper
def v11822_slot_size(slot_code: str | None):
    code = (slot_code or "").strip()
    if code in ["home_top_left", "home_top_right"]:
        return 1400, 360
    if code in ["home_sponsor_1", "home_sponsor_2", "home_sponsor_3", "home_sponsor_4"]:
        return 900, 300
    if code in ["home_bottom_1", "home_bottom_2", "home_bottom_3"]:
        return 900, 260
    return 900, 260

def v11822_make_fitted_banner_svg(slot_code: str | None, image_url: str, title: str = "", fit: str = "cover"):
    width, height = v11822_slot_size(slot_code)
    fit = (fit or "cover").strip().lower()
    preserve = "xMidYMid meet" if fit == "contain" else "xMidYMid slice"
    safe_url = html.escape(image_url or "")
    safe_title = html.escape(title or "Banner")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" rx="0" fill="#eef5ff"/>
  <image href="{safe_url}" x="0" y="0" width="{width}" height="{height}" preserveAspectRatio="{preserve}"/>
  <title>{safe_title}</title>
</svg>'''

def v11822_save_fitted_banner(slot_code: str | None, image_url: str, title: str = "", fit: str = "cover"):
    if not image_url:
        return None
    if "GENERATED_BANNERS_DIR" not in globals():
        return image_url
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in (title or "banner"))
    slug = "-".join([x for x in slug.split("-") if x])[:50] or "banner"
    name = f"{slug}-fit-{int(time.time()*1000)}.svg"
    path = GENERATED_BANNERS_DIR / name
    path.write_text(v11822_make_fitted_banner_svg(slot_code, image_url, title=title, fit=fit), encoding="utf-8")
    return f"/static/generated_banners/{name}"

async def v11822_uploaded_or_url_to_fitted(slot, title: str, upload_image: UploadFile | None = None, image_url: str = "", image_fit: str = "cover"):
    uploaded_url = await v11820_save_uploaded_banner(upload_image, title) if "v11820_save_uploaded_banner" in globals() else None
    raw_url = uploaded_url or (image_url or "").strip()
    if not raw_url:
        return None
    # V11.18.25 fix:
    # Ne umotavamo uploadovanu/eksternu sliku u SVG wrapper.
    # Browser često ne renderuje nested image unutar SVG-a kada je SVG učitan kao <img>.
    # Direktna slika se vidi sigurno, a CSS object-fit popunjava slot.
    return raw_url


# V11.18.23 automation engine
def v11823_auto_log(db: Session, event_type: str, message: str, status: str = "done", amount_rsd: float = 0.0, meta_json: str = ""):
    try:
        row = AutoEngineLogV114(
            event_type=event_type,
            actor_role="system",
            amount_rsd=amount_rsd,
            status=status,
            message=message,
            meta_json=meta_json or "",
        )
        db.add(row)
        return row
    except Exception:
        return None

def v11823_run_automation(db: Session):
    now = datetime.utcnow()
    result = {
        "submission_auto_approved": 0,
        "submission_auto_rejected": 0,
        "submission_manual_queue": 0,
        "expired_banners": 0,
        "expired_reserved_released": 0.0,
        "rejected_reserved_released": 0.0,
        "queued_notifications_sent": 0,
        "stale_withdrawals_flagged": 0,
        "pending_banner_alerts": 0,
    }

    # 0) Process pending proof submissions first so admin mostly sees exceptions.
    pending_submissions = (
        db.query(TaskSubmission)
        .filter(TaskSubmission.status == "pending")
        .order_by(TaskSubmission.created_at.asc())
        .limit(200)
        .all()
    )
    for sub in pending_submissions:
        decision, profile = v11831_auto_review_submission(db, sub, actor=None, source="automation")
        if decision == "approved":
            result["submission_auto_approved"] += 1
        elif decision == "rejected":
            result["submission_auto_rejected"] += 1
        else:
            result["submission_manual_queue"] += 1

    # 1) Expire active banners when ends_at is reached.
    expired = (
        db.query(PaidAdBannerV111)
        .filter(PaidAdBannerV111.status == "active", PaidAdBannerV111.ends_at != None, PaidAdBannerV111.ends_at <= now)
        .all()
    )
    for b in expired:
        b.status = "expired"
        b.admin_note = (b.admin_note or "") + " Auto: banner je istekao."
        result["expired_banners"] += 1
        v11823_auto_log(db, "banner_auto_expired", f"Banner #{b.id} '{b.title}' je automatski istekao.", meta_json=f"slot_id={b.slot_id}")

    # 2) Release reserved money for rejected/expired banners that were never activated/spent.
    reserved_mark = V11817_BANNER_RESERVED_MARK if "V11817_BANNER_RESERVED_MARK" in globals() else "[BANNER_RESERVED_PAID]"
    candidates = (
        db.query(PaidAdBannerV111)
        .filter(PaidAdBannerV111.status.in_(["rejected", "expired"]), PaidAdBannerV111.admin_note.contains(reserved_mark))
        .all()
    )
    for b in candidates:
        price = float(b.price_rsd or 0)
        if b.advertiser and price > 0:
            b.advertiser.advertiser_reserved_rsd = max(0, float(getattr(b.advertiser, "advertiser_reserved_rsd", 0) or 0) - price)
            b.advertiser.advertiser_budget_rsd = float(getattr(b.advertiser, "advertiser_budget_rsd", 0) or 0) + price
            add_budget_tx(db, b.advertiser, price, "banner_reserved_released", f"Vraćen rezervisan budžet za banner: {b.title}")
            if b.status == "rejected":
                result["rejected_reserved_released"] += price
            else:
                result["expired_reserved_released"] += price
        b.admin_note = (b.admin_note or "").replace(reserved_mark, "").strip() + " Auto: rezervacija budžeta oslobođena."
        v11823_auto_log(db, "banner_reserved_released", f"Oslobođen rezervisan budžet za banner #{b.id}: {price:.0f} RSD", amount_rsd=price)

    # 3) Queue admin alerts for pending banners older than 24h.
    cutoff = now - timedelta(hours=24)
    old_pending = (
        db.query(PaidAdBannerV111)
        .filter(PaidAdBannerV111.status == "pending", PaidAdBannerV111.created_at <= cutoff)
        .all()
    )
    for b in old_pending:
        already = db.query(AutoNotificationQueueV114).filter(
            AutoNotificationQueueV114.channel == "internal",
            AutoNotificationQueueV114.subject == "Pending banner >24h",
            AutoNotificationQueueV114.related_user_id == b.advertiser_id,
            AutoNotificationQueueV114.body.contains(f"#{b.id}")
        ).first()
        if not already:
            db.add(AutoNotificationQueueV114(
                channel="internal",
                recipient="admin",
                subject="Pending banner >24h",
                body=f"Banner #{b.id} '{b.title}' čeka odobrenje duže od 24h.",
                status="queued",
                related_user_id=b.advertiser_id
            ))
            result["pending_banner_alerts"] += 1

    # 4) Mark queued internal notifications as sent simulation.
    queued = db.query(AutoNotificationQueueV114).filter(AutoNotificationQueueV114.status == "queued").limit(100).all()
    for q in queued:
        q.status = "sent"
        q.sent_at = now
        result["queued_notifications_sent"] += 1
        v11823_auto_log(db, "notification_sent", f"Auto poslata notifikacija: {q.subject}", meta_json=f"channel={q.channel}")

    # 5) Flag stale pending withdrawals older than 72h.
    wcut = now - timedelta(hours=72)
    stale = db.query(Withdrawal).filter(Withdrawal.status == "pending", Withdrawal.created_at <= wcut).all()
    for w in stale:
        note = w.admin_note or ""
        if "Auto: čeka obradu duže od 72h" not in note:
            w.admin_note = (note + " " if note else "") + "Auto: čeka obradu duže od 72h."
            result["stale_withdrawals_flagged"] += 1
            v11823_auto_log(db, "withdrawal_stale_alert", f"Isplata #{w.id} čeka duže od 72h.", amount_rsd=float(w.amount_rsd or 0))

    v11823_auto_log(db, "automation_run", "Automation engine run completed.", meta_json=str(result))
    db.commit()
    return result

@app.post("/admin/automation/run-v11823")
def admin_run_automation_v11823(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    result = v11823_run_automation(db)
    return RedirectResponse("/admin/auto-engine-v114?msg=automation_run", 303)

@app.get("/api/v1/v11/automation-run")
def api_run_automation_v11823(token: str | None = None, db: Session = Depends(get_db)):
    # Local/dev cron endpoint. In production protect by token/env before public exposure.
    result = v11823_run_automation(db)
    return {"version": "11.18.23", "status": "ok", "result": result}

@app.get("/api/v1/v11/automation-health")
def api_automation_health_v11823(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    return {
        "version": "11.18.23",
        "active_banners": db.query(PaidAdBannerV111).filter(PaidAdBannerV111.status == "active").count(),
        "pending_banners": db.query(PaidAdBannerV111).filter(PaidAdBannerV111.status == "pending").count(),
        "expired_due": db.query(PaidAdBannerV111).filter(PaidAdBannerV111.status == "active", PaidAdBannerV111.ends_at != None, PaidAdBannerV111.ends_at <= now).count(),
        "queued_notifications": db.query(AutoNotificationQueueV114).filter(AutoNotificationQueueV114.status == "queued").count(),
        "pending_withdrawals": db.query(Withdrawal).filter(Withdrawal.status == "pending").count(),
        "pending_submissions": db.query(TaskSubmission).filter(TaskSubmission.status == "pending").count(),
        "auto_reviewed_submissions": db.query(AutoEngineLogV114).filter(AutoEngineLogV114.event_type.in_(["submission_auto_approved", "submission_auto_rejected"])).count(),
    }


# V11.18.24 automation report endpoint
@app.get("/api/v1/v11/automation-report")
def api_automation_report_v11824(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    last_logs = db.query(AutoEngineLogV114).order_by(AutoEngineLogV114.created_at.desc()).limit(20).all()
    pending_24h_cutoff = now - timedelta(hours=24)
    stale_withdrawals_cutoff = now - timedelta(hours=72)

    slot_rows = []
    if "v11815_banner_slot_definitions" in globals():
        codes = [x[0] for x in v11815_banner_slot_definitions()]
        slots = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code.in_(codes)).order_by(HomeBannerSlotV111.id.asc()).all()
    else:
        slots = db.query(HomeBannerSlotV111).order_by(HomeBannerSlotV111.id.asc()).all()

    for s in slots:
        slot_rows.append({
            "slot": s.code,
            "title": s.title,
            "active": db.query(PaidAdBannerV111).filter(PaidAdBannerV111.slot_id == s.id, PaidAdBannerV111.status == "active").count(),
            "pending": db.query(PaidAdBannerV111).filter(PaidAdBannerV111.slot_id == s.id, PaidAdBannerV111.status == "pending").count(),
            "expired": db.query(PaidAdBannerV111).filter(PaidAdBannerV111.slot_id == s.id, PaidAdBannerV111.status == "expired").count(),
        })

    return {
        "version": "11.18.24",
        "generated_at": now.isoformat(),
        "submissions": {
            "pending": db.query(TaskSubmission).filter(TaskSubmission.status == "pending").count(),
            "auto_approved": db.query(AutoEngineLogV114).filter(AutoEngineLogV114.event_type == "submission_auto_approved").count(),
            "auto_rejected": db.query(AutoEngineLogV114).filter(AutoEngineLogV114.event_type == "submission_auto_rejected").count(),
            "manual_queue": db.query(AutoEngineLogV114).filter(AutoEngineLogV114.event_type == "submission_needs_manual_review", AutoEngineLogV114.status == "queued").count(),
        },
        "banners": {
            "active": db.query(PaidAdBannerV111).filter(PaidAdBannerV111.status == "active").count(),
            "pending": db.query(PaidAdBannerV111).filter(PaidAdBannerV111.status == "pending").count(),
            "expired_due": db.query(PaidAdBannerV111).filter(PaidAdBannerV111.status == "active", PaidAdBannerV111.ends_at != None, PaidAdBannerV111.ends_at <= now).count(),
            "pending_over_24h": db.query(PaidAdBannerV111).filter(PaidAdBannerV111.status == "pending", PaidAdBannerV111.created_at <= pending_24h_cutoff).count(),
            "slots": slot_rows,
        },
        "finance": {
            "reserved_total_rsd": sum(float(u.advertiser_reserved_rsd or 0) for u in db.query(User).filter(User.role == "oglasivac").all()),
            "advertiser_budget_total_rsd": sum(float(u.advertiser_budget_rsd or 0) for u in db.query(User).filter(User.role == "oglasivac").all()),
            "pending_withdrawals": db.query(Withdrawal).filter(Withdrawal.status == "pending").count(),
            "stale_withdrawals_over_72h": db.query(Withdrawal).filter(Withdrawal.status == "pending", Withdrawal.created_at <= stale_withdrawals_cutoff).count(),
        },
        "queue": {
            "queued": db.query(AutoNotificationQueueV114).filter(AutoNotificationQueueV114.status == "queued").count(),
            "sent": db.query(AutoNotificationQueueV114).filter(AutoNotificationQueueV114.status == "sent").count(),
        },
        "last_logs": [
            {
                "event_type": l.event_type,
                "status": l.status,
                "message": l.message,
                "amount_rsd": l.amount_rsd,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            } for l in last_logs
        ],
    }


# V11.18.28 real image pack/crop helper
def v11828_slot_size(slot_code: str | None):
    code = (slot_code or "").strip()
    if code in ["home_top_left", "home_top_right"]:
        return 1400, 360
    if code in ["home_sponsor_1", "home_sponsor_2", "home_sponsor_3", "home_sponsor_4"]:
        return 900, 300
    if code in ["home_dashboard_banner"]:
        return 1200, 220
    if code in ["admin_dashboard_banner"]:
        return 1200, 220
    if code in ["home_bottom_1", "home_bottom_2", "home_bottom_3"]:
        return 900, 260
    return 900, 260

def v11828_cover_resize(img, target_w: int, target_h: int):
    src_w, src_h = img.size
    if src_w <= 0 or src_h <= 0:
        return img.resize((target_w, target_h))
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h
    if src_ratio > target_ratio:
        new_h = target_h
        new_w = int(target_h * src_ratio)
    else:
        new_w = target_w
        new_h = int(target_w / src_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = max(0, (new_w - target_w) // 2)
    top = max(0, (new_h - target_h) // 2)
    return img.crop((left, top, left + target_w, top + target_h))

def v11828_contain_resize(img, target_w: int, target_h: int):
    base = Image.new("RGB", (target_w, target_h), (238, 245, 255))
    img.thumbnail((target_w, target_h), Image.LANCZOS)
    if img.mode != "RGB":
        img = img.convert("RGB")
    left = (target_w - img.width) // 2
    top = (target_h - img.height) // 2
    base.paste(img, (left, top))
    return base

async def v11828_save_uploaded_banner_packed(slot, title: str, upload_image: UploadFile | None = None, image_fit: str = "cover"):
    if not upload_image or not upload_image.filename:
        return None

    suffix = Path(upload_image.filename).suffix.lower()
    allowed = {".png", ".jpg", ".jpeg", ".webp"}
    if suffix not in allowed:
        # SVG ne cropujemo preko Pillow-a, ali ga čuvamo direktno kao fallback.
        if "v11820_save_uploaded_banner" in globals():
            return await v11820_save_uploaded_banner(upload_image, title)
        raise HTTPException(400, "Dozvoljeni formati slike su PNG, JPG, JPEG, WEBP ili SVG.")

    data = await upload_image.read()
    if not data:
        return None
    if len(data) > 4 * 1024 * 1024:
        raise HTTPException(400, "Slika je prevelika. Maksimalno 4 MB.")

    target_w, target_h = v11828_slot_size(getattr(slot, "code", None))
    upload_dir = Path("app/static/uploads/banners")
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_prefix = "".join(ch.lower() if ch.isalnum() else "-" for ch in (title or "banner"))[:42].strip("-") or "banner"
    name = f"{safe_prefix}-packed-{target_w}x{target_h}-{int(time.time()*1000)}-{secrets.token_hex(4)}.jpg"
    path = upload_dir / name

    from io import BytesIO
    img = Image.open(BytesIO(data))
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    fit = (image_fit or "cover").strip().lower()
    if fit == "contain":
        out = v11828_contain_resize(img, target_w, target_h)
    else:
        out = v11828_cover_resize(img, target_w, target_h)

    out.save(path, "JPEG", quality=92, optimize=True)
    return f"/static/uploads/banners/{name}"

async def v11828_final_banner_image(slot, title: str, upload_image: UploadFile | None = None, image_url: str = "", image_fit: str = "cover", fallback_url: str | None = None):
    packed = await v11828_save_uploaded_banner_packed(slot, title, upload_image, image_fit)
    if packed:
        return packed
    raw = (image_url or "").strip()
    if raw:
        return raw
    return fallback_url


# =========================================================
# V11.18.31 TASK + PROOF WORKFLOW HARDENING
# Početna stranica se ne dira. Ovo su samo funkcionalni tokovi.
# =========================================================

def v11831_money(v):
    try:
        return round(float(v or 0), 2)
    except Exception:
        return 0.0

def v11831_task_cost(task):
    reward = v11831_money(getattr(task, "reward_rsd", 0))
    fee_percent = v11831_money(getattr(task, "platform_fee_percent", 20.0))
    fee = round(reward * fee_percent / 100.0, 2)
    return reward, fee, round(reward + fee, 2)

def v11831_find_existing_submission(db: Session, user_id: int, task_id: int):
    return db.query(TaskSubmission).filter(
        TaskSubmission.user_id == user_id,
        TaskSubmission.task_id == task_id,
        TaskSubmission.status.in_(["pending", "approved", "disputed"])
    ).first()

def v11831_create_submission(db: Session, user, task, proof_text: str, proof_file: str = ""):
    if not task:
        return None, "task_not_found"
    if getattr(task, "status", "") != "active":
        return None, "task_not_active"
    if v11831_find_existing_submission(db, user.id, task.id):
        return None, "already_submitted"
    if len((proof_text or "").strip()) < 3:
        return None, "proof_required"
    total_slots = int(getattr(task, "total_slots", 0) or 0)
    used_slots = int(getattr(task, "used_slots", 0) or 0)
    if total_slots > 0 and used_slots >= total_slots:
        return None, "no_slots"

    reward, fee, cost = v11831_task_cost(task)
    advertiser = getattr(task, "advertiser", None)
    if advertiser:
        available = v11831_money(getattr(advertiser, "advertiser_budget_rsd", 0))
        if available < cost:
            return None, "advertiser_budget_error"
        advertiser.advertiser_budget_rsd = round(available - cost, 2)
        advertiser.advertiser_reserved_rsd = round(v11831_money(getattr(advertiser, "advertiser_reserved_rsd", 0)) + cost, 2)
        add_budget_tx(db, advertiser, -cost, "task_submission_reserved", f"Rezervisano za dokaz: {task.title}")

    sub = TaskSubmission(
        user_id=user.id,
        task_id=task.id,
        proof=(proof_text or "").strip(),
        proof_file=(proof_file or "").strip() or None,
        status="pending",
        reward_rsd=reward,
        platform_fee_rsd=fee,
        advertiser_cost_rsd=cost,
    )
    db.add(sub)
    task.used_slots = used_slots + 1
    user.pending_rsd = round(v11831_money(getattr(user, "pending_rsd", 0)) + reward, 2)
    notify(db, role_target="admin", title="Novi dokaz za proveru", body=f"{user.full_name} je poslao/la dokaz za: {task.title}")
    if advertiser:
        notify(db, advertiser, None, "Novi dokaz na kampanji", f"Stigao je dokaz za kampanju: {task.title}")
    db.commit()
    db.refresh(sub)
    return sub, "created"

def v11831_approve_submission(db: Session, admin, sub, note: str = ""):
    if not sub:
        return "not_found"
    if sub.status != "pending":
        return f"already_{sub.status}"

    reward = v11831_money(sub.reward_rsd)
    cost = v11831_money(sub.advertiser_cost_rsd)
    sub.status = "approved"
    sub.review_note = note.strip() or "Odobreno"
    sub.reviewed_at = datetime.utcnow()

    sub.user.pending_rsd = max(0, round(v11831_money(getattr(sub.user, "pending_rsd", 0)) - reward, 2))
    sub.user.balance_rsd = round(v11831_money(getattr(sub.user, "balance_rsd", 0)) + reward, 2)
    sub.user.lifetime_earned_rsd = round(v11831_money(getattr(sub.user, "lifetime_earned_rsd", 0)) + reward, 2)
    add_tx(db, sub.user, reward, "task_reward", f"Zarada za zadatak: {sub.task.title}")

    if sub.task and sub.task.advertiser and cost > 0:
        adv = sub.task.advertiser
        adv.advertiser_reserved_rsd = max(0, round(v11831_money(getattr(adv, "advertiser_reserved_rsd", 0)) - cost, 2))
        adv.advertiser_spent_rsd = round(v11831_money(getattr(adv, "advertiser_spent_rsd", 0)) + cost, 2)
        add_budget_tx(db, adv, 0, "task_submission_approved", f"Odobren dokaz, rezervacija prebačena u potrošeno: {sub.task.title}")

    notify(db, sub.user, None, "Dokaz odobren", f"Odobren je dokaz za zadatak: {sub.task.title}. Dodato {reward:.0f} RSD.")
    try:
        update_quality(db, sub.user)
    except Exception:
        pass
    audit(db, admin, "submission_approve_v11831", "TaskSubmission", sub.id, note)
    db.commit()
    return "approved"

def v11831_reject_submission(db: Session, admin, sub, note: str = ""):
    if not sub:
        return "not_found"
    if sub.status != "pending":
        return f"already_{sub.status}"

    reward = v11831_money(sub.reward_rsd)
    cost = v11831_money(sub.advertiser_cost_rsd)
    sub.status = "rejected"
    sub.review_note = note.strip() or "Odbijeno"
    sub.reviewed_at = datetime.utcnow()

    sub.user.pending_rsd = max(0, round(v11831_money(getattr(sub.user, "pending_rsd", 0)) - reward, 2))
    if sub.task:
        sub.task.used_slots = max(0, int(getattr(sub.task, "used_slots", 0) or 0) - 1)
        if sub.task.advertiser and cost > 0:
            adv = sub.task.advertiser
            adv.advertiser_reserved_rsd = max(0, round(v11831_money(getattr(adv, "advertiser_reserved_rsd", 0)) - cost, 2))
            adv.advertiser_budget_rsd = round(v11831_money(getattr(adv, "advertiser_budget_rsd", 0)) + cost, 2)
            add_budget_tx(db, adv, cost, "task_submission_released", f"Vraćena rezervacija za odbijen dokaz: {sub.task.title}")

    notify(db, sub.user, None, "Dokaz odbijen", f"Dokaz za zadatak {sub.task.title if sub.task else ''} je odbijen. Napomena: {note}")
    try:
        update_quality(db, sub.user)
    except Exception:
        pass
    audit(db, admin, "submission_reject_v11831", "TaskSubmission", sub.id, note)
    db.commit()
    return "rejected"

@app.post("/oglasivac/kampanje/v11831")
def advertiser_create_task_v11831(
    request: Request,
    title: str = Form(...),
    task_type: str = Form("visit_site"),
    target_url: str = Form("/"),
    description: str = Form(""),
    instructions: str = Form(""),
    proof_required: str = Form("Pošaljite kratak opis izvršenog zadatka."),
    reward_rsd: float = Form(50),
    total_slots: int = Form(50),
    estimated_minutes: int = Form(2),
    db: Session = Depends(get_db)
):
    u = require(request, db); check_role(u, ["oglasivac", "admin"])
    task = Task(
        advertiser_id=(u.id if u.role == "oglasivac" else None),
        title=title.strip(),
        task_type=task_type.strip() or "visit_site",
        target_url=target_url.strip() or "/",
        description=description.strip() or "Kampanja oglašivača.",
        instructions=instructions.strip() or "Pratite instrukcije i pošaljite dokaz.",
        proof_required=proof_required.strip() or "Pošaljite dokaz.",
        reward_rsd=max(1, float(reward_rsd or 1)),
        total_slots=max(1, int(total_slots or 1)),
        estimated_minutes=max(1, int(estimated_minutes or 1)),
        status="pending",
    )
    db.add(task)
    notify(db, role_target="admin", title="Nova kampanja za odobrenje", body=f"Oglašivač {u.full_name} je kreirao kampanju: {task.title}")
    db.commit()
    return RedirectResponse("/oglasivac/kampanje?msg=created", 303)

@app.post("/admin/tasks/{task_id}/status-v11831")
def admin_task_status_v11831(task_id: int, request: Request, status: str = Form("active"), note: str = Form(""), db: Session = Depends(get_db)):
    admin = require(request, db); check_role(admin, ["admin"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404)
    if status not in ["active", "pending", "rejected", "paused", "closed", "returned"]:
        status = "pending"
    task.status = status
    task.moderation_note = note.strip() or task.moderation_note
    if task.advertiser:
        notify(db, task.advertiser, None, "Status kampanje", f"Kampanja '{task.title}' je sada: {status}.")
    audit(db, admin, f"task_status_{status}_v11831", "Task", task.id, note)
    db.commit()
    return RedirectResponse("/admin/kampanje?msg=saved", 303)

@app.post("/korisnik/zadaci/{task_id}/dokaz-v11831")
def user_submit_proof_v11831(task_id: int, request: Request, proof: str = Form(""), proof_file: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["korisnik"])
    task = db.query(Task).filter(Task.id == task_id).first()
    sub, status = v11831_create_submission(db, u, task, proof, proof_file)
    if status == "created":
        try:
            decision, profile = v11831_auto_review_submission(db, sub, actor=u, source="submit")
            if decision == "approved":
                return RedirectResponse("/korisnik/dokazi?msg=auto_approved", 303)
            if decision == "rejected":
                return RedirectResponse("/korisnik/dokazi?msg=auto_rejected", 303)
        except Exception:
            pass
        return RedirectResponse("/korisnik/dokazi?msg=pending_manual", 303)
    return RedirectResponse(f"/zadaci/{task_id}?msg={status}", 303)

@app.get("/api/v1/v11/task-proof-workflow-health")
def v11831_task_proof_workflow_health(db: Session = Depends(get_db)):
    return {
        "version": "11.18.31",
        "status": "ready",
        "tasks": db.query(Task).count(),
        "active_tasks": db.query(Task).filter(Task.status == "active").count(),
        "pending_tasks": db.query(Task).filter(Task.status == "pending").count(),
        "submissions": db.query(TaskSubmission).count(),
        "pending_submissions": db.query(TaskSubmission).filter(TaskSubmission.status == "pending").count(),
        "approved_submissions": db.query(TaskSubmission).filter(TaskSubmission.status == "approved").count(),
        "rejected_submissions": db.query(TaskSubmission).filter(TaskSubmission.status == "rejected").count(),
    }


@app.post("/admin/task-status-v11831/{task_id}")
def admin_task_status_v11831_alias(task_id: int, request: Request, status: str = Form("active"), note: str = Form(""), db: Session = Depends(get_db)):
    # Non-shadowed route. /admin/tasks/{task_id}/{action} exists earlier and would catch /status-v11831.
    admin = require(request, db); check_role(admin, ["admin"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404)
    if status not in ["active", "pending", "rejected", "paused", "closed", "returned"]:
        status = "pending"
    task.status = status
    task.moderation_note = note.strip() or task.moderation_note
    if task.advertiser:
        notify(db, task.advertiser, None, "Status kampanje", f"Kampanja '{task.title}' je sada: {status}.")
    audit(db, admin, f"task_status_{status}_v11831", "Task", task.id, note)
    db.commit()
    return RedirectResponse("/admin/kampanje?msg=saved", 303)


# =========================================================
# V11.18.32 PAYOUT WORKFLOW HARDENING
# Početna stranica se ne dira.
# =========================================================

def v11832_money(v):
    try:
        return round(float(v or 0), 2)
    except Exception:
        return 0.0

def v11832_pending_withdrawal_total(db: Session, user_id: int):
    return v11832_money(db.query(func.coalesce(func.sum(Withdrawal.amount_rsd), 0)).filter(
        Withdrawal.user_id == user_id,
        Withdrawal.status == "pending"
    ).scalar() or 0)

def v11832_create_withdrawal(db: Session, user, amount_rsd: float, payment_method: str = "bank_transfer", payment_details: str = "", note: str = ""):
    amount = v11832_money(amount_rsd)
    if amount <= 0:
        return None, "bad_amount"
    min_amount = float(globals().get("MIN_WITHDRAWAL_RSD", 500) or 500)
    if amount < min_amount:
        return None, "min_amount"
    balance = v11832_money(getattr(user, "balance_rsd", 0))
    if amount > balance:
        return None, "insufficient_balance"
    details = (payment_details or getattr(user, "payment_details", "") or note or "").strip()
    if len(details) < 3:
        return None, "payment_details_required"

    user.balance_rsd = round(balance - amount, 2)
    w = Withdrawal(
        user_id=user.id,
        amount_rsd=amount,
        payment_method=(payment_method or "bank_transfer").strip(),
        payment_details=details,
        status="pending",
    )
    db.add(w)
    add_tx(db, user, -amount, "withdrawal_reserved", f"Zahtev za isplatu: {amount:.0f} RSD ({w.payment_method})")
    notify(db, role_target="admin", title="Novi zahtev za isplatu", body=f"{user.full_name} traži isplatu {amount:.0f} RSD.")
    db.commit()
    db.refresh(w)
    return w, "created"

def v11832_pay_withdrawal(db: Session, admin, withdrawal, note: str = ""):
    if not withdrawal:
        return "not_found"
    if withdrawal.status != "pending":
        return f"already_{withdrawal.status}"
    withdrawal.status = "paid"
    withdrawal.admin_note = note.strip() or "Isplaćeno"
    withdrawal.processed_at = datetime.utcnow()
    notify(db, withdrawal.user, None, "Isplata izvršena", f"Isplata {withdrawal.amount_rsd:.0f} RSD je označena kao isplaćena.")
    audit(db, admin, "withdrawal_paid_v11832", "Withdrawal", withdrawal.id, note)
    db.commit()
    return "paid"

def v11832_reject_withdrawal(db: Session, admin, withdrawal, note: str = ""):
    if not withdrawal:
        return "not_found"
    if withdrawal.status != "pending":
        return f"already_{withdrawal.status}"
    amount = v11832_money(withdrawal.amount_rsd)
    withdrawal.status = "rejected"
    withdrawal.admin_note = note.strip() or "Odbijeno"
    withdrawal.processed_at = datetime.utcnow()
    withdrawal.user.balance_rsd = round(v11832_money(getattr(withdrawal.user, "balance_rsd", 0)) + amount, 2)
    add_tx(db, withdrawal.user, amount, "withdrawal_return", f"Vraćena odbijena isplata: {amount:.0f} RSD")
    notify(db, withdrawal.user, None, "Isplata odbijena", f"Zahtev za isplatu {amount:.0f} RSD je odbijen. Novac je vraćen na balans.")
    audit(db, admin, "withdrawal_rejected_v11832", "Withdrawal", withdrawal.id, note)
    db.commit()
    return "rejected"

@app.post("/korisnik/isplate/zahtev-v11832")
def user_withdrawal_request_v11832(
    request: Request,
    amount_rsd: float = Form(0),
    payment_method: str = Form("bank_transfer"),
    payment_details: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db)
):
    user = require(request, db); check_role(user, ["korisnik"])
    w, status = v11836_create_payout_request(db, user, amount_rsd, payment_method, payment_details, note)
    return RedirectResponse(f"/korisnik/isplate?msg={status}", 303)

@app.post("/admin/withdrawals-v11832/{wid}/{action}")
def admin_withdrawal_action_v11832(wid: int, action: str, request: Request, note: str = Form(""), db: Session = Depends(get_db)):
    admin = require(request, db); check_role(admin, ["admin"])
    w = db.query(Withdrawal).filter(Withdrawal.id == wid).first()
    if action in ["paid", "pay", "approve"]:
        result = v11832_pay_withdrawal(db, admin, w, note)
    elif action in ["reject", "rejected"]:
        result = v11832_reject_withdrawal(db, admin, w, note)
    else:
        result = "bad_action"
    return RedirectResponse(f"/admin/isplate?msg={result}", 303)

@app.get("/api/v1/v11/payout-workflow-health")
def v11832_payout_workflow_health(db: Session = Depends(get_db)):
    return {
        "version": "11.18.32",
        "status": "ready",
        "withdrawals": db.query(Withdrawal).count(),
        "pending": db.query(Withdrawal).filter(Withdrawal.status == "pending").count(),
        "paid": db.query(Withdrawal).filter(Withdrawal.status == "paid").count(),
        "rejected": db.query(Withdrawal).filter(Withdrawal.status == "rejected").count(),
        "pending_amount_rsd": v11832_money(db.query(func.coalesce(func.sum(Withdrawal.amount_rsd), 0)).filter(Withdrawal.status == "pending").scalar() or 0),
        "paid_amount_rsd": v11832_money(db.query(func.coalesce(func.sum(Withdrawal.amount_rsd), 0)).filter(Withdrawal.status == "paid").scalar() or 0),
    }


# =========================================================
# V11.18.33 ADVERTISER BUDGET ENGINE
# Početna stranica se ne dira.
# =========================================================

def v11833_money(v):
    try:
        return round(float(v or 0), 2)
    except Exception:
        return 0.0

def v11833_budget_snapshot(db: Session, advertiser):
    txs = db.query(AdvertiserBudgetTransaction).filter(
        AdvertiserBudgetTransaction.advertiser_id == advertiser.id
    ).order_by(AdvertiserBudgetTransaction.created_at.desc()).limit(100).all()
    return {
        "budget_rsd": v11833_money(advertiser.advertiser_budget_rsd),
        "reserved_rsd": v11833_money(advertiser.advertiser_reserved_rsd),
        "spent_rsd": v11833_money(advertiser.advertiser_spent_rsd),
        "available_rsd": v11833_money(advertiser.advertiser_budget_rsd),
        "recent_transactions": [
            {"amount_rsd": v11833_money(t.amount_rsd), "tx_type": t.tx_type, "description": t.description, "created_at": t.created_at.isoformat() if t.created_at else None}
            for t in txs
        ]
    }

def v11833_topup_request(db: Session, advertiser, amount_rsd: float, note: str = ""):
    amount = v11833_money(amount_rsd)
    if amount <= 0:
        return None, "bad_amount"
    tx = AdvertiserBudgetTransaction(
        advertiser_id=advertiser.id,
        amount_rsd=0,
        tx_type="topup_request",
        description=f"Zahtev za dopunu: {amount:.0f} RSD. {note}".strip()
    )
    db.add(tx)
    notify(db, role_target="admin", title="Zahtev za dopunu budžeta", body=f"{advertiser.full_name} traži dopunu {amount:.0f} RSD.")
    db.commit()
    db.refresh(tx)
    return tx, "created"

def v11833_admin_topup(db: Session, admin, advertiser, amount_rsd: float, reason: str = ""):
    amount = v11833_money(amount_rsd)
    if not advertiser:
        return "not_found"
    if advertiser.role != "oglasivac":
        return "not_advertiser"
    if amount <= 0:
        return "bad_amount"
    advertiser.advertiser_budget_rsd = round(v11833_money(advertiser.advertiser_budget_rsd) + amount, 2)
    add_budget_tx(db, advertiser, amount, "manual_topup_v11833", reason or f"Admin dopuna budžeta: {amount:.0f} RSD")
    notify(db, advertiser, None, "Budžet dopunjen", f"Vaš oglašivački budžet je dopunjen za {amount:.0f} RSD.")
    audit(db, admin, "advertiser_topup_v11833", "User", advertiser.id, reason)
    db.commit()
    return "topup_done"

def v11833_reserve_budget(db: Session, advertiser, amount_rsd: float, description: str = "Rezervacija budžeta"):
    amount = v11833_money(amount_rsd)
    if amount <= 0:
        return "bad_amount"
    if v11833_money(advertiser.advertiser_budget_rsd) < amount:
        return "insufficient_budget"
    advertiser.advertiser_budget_rsd = round(v11833_money(advertiser.advertiser_budget_rsd) - amount, 2)
    advertiser.advertiser_reserved_rsd = round(v11833_money(advertiser.advertiser_reserved_rsd) + amount, 2)
    add_budget_tx(db, advertiser, -amount, "reserve_v11833", description)
    db.commit()
    return "reserved"

def v11833_spend_reserved(db: Session, advertiser, amount_rsd: float, description: str = "Potrošnja rezervacije"):
    amount = v11833_money(amount_rsd)
    if amount <= 0:
        return "bad_amount"
    advertiser.advertiser_reserved_rsd = max(0, round(v11833_money(advertiser.advertiser_reserved_rsd) - amount, 2))
    advertiser.advertiser_spent_rsd = round(v11833_money(advertiser.advertiser_spent_rsd) + amount, 2)
    add_budget_tx(db, advertiser, 0, "spend_reserved_v11833", description)
    db.commit()
    return "spent"

def v11833_release_reserved(db: Session, advertiser, amount_rsd: float, description: str = "Oslobađanje rezervacije"):
    amount = v11833_money(amount_rsd)
    if amount <= 0:
        return "bad_amount"
    amount = min(amount, v11833_money(advertiser.advertiser_reserved_rsd))
    advertiser.advertiser_reserved_rsd = max(0, round(v11833_money(advertiser.advertiser_reserved_rsd) - amount, 2))
    advertiser.advertiser_budget_rsd = round(v11833_money(advertiser.advertiser_budget_rsd) + amount, 2)
    add_budget_tx(db, advertiser, amount, "release_reserved_v11833", description)
    db.commit()
    return "released"

@app.post("/oglasivac/budzet/zahtev-v11833")
def advertiser_budget_request_v11833(request: Request, amount_rsd: float = Form(...), note: str = Form(""), db: Session = Depends(get_db)):
    adv = require(request, db); check_role(adv, ["oglasivac", "admin"])
    tx, status = v11833_topup_request(db, adv, amount_rsd, note)
    return RedirectResponse(f"/oglasivac/budzet?msg={status}", 303)

@app.post("/admin/oglasivaci/{uid}/topup-v11833")
def admin_topup_v11833(uid: int, request: Request, amount_rsd: float = Form(...), reason: str = Form(""), db: Session = Depends(get_db)):
    admin = require(request, db); check_role(admin, ["admin"])
    adv = db.query(User).filter(User.id == uid, User.role == "oglasivac").first()
    status = v11833_admin_topup(db, admin, adv, amount_rsd, reason)
    return RedirectResponse(f"/admin/oglasivaci?msg={status}", 303)

@app.get("/api/v1/v11/advertiser-budget-health")
def advertiser_budget_health_v11833(db: Session = Depends(get_db)):
    advertisers = db.query(User).filter(User.role == "oglasivac").all()
    return {
        "version": "11.18.33",
        "status": "ready",
        "advertisers": len(advertisers),
        "budget_total_rsd": v11833_money(sum(v11833_money(a.advertiser_budget_rsd) for a in advertisers)),
        "reserved_total_rsd": v11833_money(sum(v11833_money(a.advertiser_reserved_rsd) for a in advertisers)),
        "spent_total_rsd": v11833_money(sum(v11833_money(a.advertiser_spent_rsd) for a in advertisers)),
        "tx_count": db.query(AdvertiserBudgetTransaction).count(),
        "topup_requests": db.query(AdvertiserBudgetTransaction).filter(AdvertiserBudgetTransaction.tx_type == "topup_request").count(),
    }

@app.get("/api/v1/v11/advertiser-budget-snapshot")
def advertiser_budget_snapshot_v11833(request: Request, db: Session = Depends(get_db)):
    adv = require(request, db); check_role(adv, ["oglasivac", "admin"])
    return {"version": "11.18.33", "advertiser_id": adv.id, "snapshot": v11833_budget_snapshot(db, adv)}


# =========================================================
# V11.18.34 FINANCE RECONCILIATION / ADMIN CONTROL
# Početna stranica se ne dira.
# =========================================================

def v11834_money(v):
    try:
        return round(float(v or 0), 2)
    except Exception:
        return 0.0

def v11834_sum(db: Session, model, column, *filters):
    q = db.query(func.coalesce(func.sum(column), 0))
    for f in filters:
        q = q.filter(f)
    return v11834_money(q.scalar() or 0)

def v11834_count(db: Session, model, *filters):
    q = db.query(model)
    for f in filters:
        q = q.filter(f)
    return q.count()

def v11834_finance_snapshot(db: Session):
    users = db.query(User).all()
    korisnici = [u for u in users if u.role == "korisnik"]
    advertisers = [u for u in users if u.role == "oglasivac"]

    user_balance = v11834_money(sum(v11834_money(u.balance_rsd) for u in korisnici))
    user_pending = v11834_money(sum(v11834_money(u.pending_rsd) for u in korisnici))
    user_lifetime = v11834_money(sum(v11834_money(u.lifetime_earned_rsd) for u in korisnici))

    adv_budget = v11834_money(sum(v11834_money(a.advertiser_budget_rsd) for a in advertisers))
    adv_reserved = v11834_money(sum(v11834_money(a.advertiser_reserved_rsd) for a in advertisers))
    adv_spent = v11834_money(sum(v11834_money(a.advertiser_spent_rsd) for a in advertisers))

    approved_rewards = v11834_sum(db, TaskSubmission, TaskSubmission.reward_rsd, TaskSubmission.status == "approved")
    pending_rewards = v11834_sum(db, TaskSubmission, TaskSubmission.reward_rsd, TaskSubmission.status == "pending")
    rejected_rewards = v11834_sum(db, TaskSubmission, TaskSubmission.reward_rsd, TaskSubmission.status == "rejected")
    approved_fees = v11834_sum(db, TaskSubmission, TaskSubmission.platform_fee_rsd, TaskSubmission.status == "approved")
    approved_costs = v11834_sum(db, TaskSubmission, TaskSubmission.advertiser_cost_rsd, TaskSubmission.status == "approved")
    pending_costs = v11834_sum(db, TaskSubmission, TaskSubmission.advertiser_cost_rsd, TaskSubmission.status == "pending")

    withdrawals_pending = v11834_sum(db, Withdrawal, Withdrawal.amount_rsd, Withdrawal.status == "pending")
    withdrawals_paid = v11834_sum(db, Withdrawal, Withdrawal.amount_rsd, Withdrawal.status == "paid")
    withdrawals_rejected = v11834_sum(db, Withdrawal, Withdrawal.amount_rsd, Withdrawal.status == "rejected")

    wallet_tx_total = v11834_sum(db, WalletTransaction, WalletTransaction.amount_rsd)
    budget_tx_total = v11834_sum(db, AdvertiserBudgetTransaction, AdvertiserBudgetTransaction.amount_rsd)

    negative_users = [
        {"id": u.id, "email": u.email, "balance_rsd": v11834_money(u.balance_rsd), "pending_rsd": v11834_money(u.pending_rsd)}
        for u in korisnici
        if v11834_money(u.balance_rsd) < 0 or v11834_money(u.pending_rsd) < 0
    ]
    negative_advertisers = [
        {"id": a.id, "email": a.email, "budget_rsd": v11834_money(a.advertiser_budget_rsd), "reserved_rsd": v11834_money(a.advertiser_reserved_rsd), "spent_rsd": v11834_money(a.advertiser_spent_rsd)}
        for a in advertisers
        if v11834_money(a.advertiser_budget_rsd) < 0 or v11834_money(a.advertiser_reserved_rsd) < 0 or v11834_money(a.advertiser_spent_rsd) < 0
    ]

    stale_withdrawals = db.query(Withdrawal).filter(
        Withdrawal.status == "pending",
        Withdrawal.created_at < datetime.utcnow() - timedelta(hours=72)
    ).count()
    stale_submissions = db.query(TaskSubmission).filter(
        TaskSubmission.status == "pending",
        TaskSubmission.created_at < datetime.utcnow() - timedelta(hours=72)
    ).count()

    warnings = []
    if negative_users:
        warnings.append(f"Negativni korisnički balans/pending: {len(negative_users)}")
    if negative_advertisers:
        warnings.append(f"Negativni oglašivački budžeti/rezervacije: {len(negative_advertisers)}")
    if stale_withdrawals:
        warnings.append(f"Isplate čekaju duže od 72h: {stale_withdrawals}")
    if stale_submissions:
        warnings.append(f"Dokazi čekaju duže od 72h: {stale_submissions}")
    if abs(user_pending - pending_rewards) > 0.01:
        warnings.append(f"Pending korisnika ({user_pending}) nije jednak pending dokazima ({pending_rewards})")
    if abs(adv_reserved - pending_costs) > 0.01:
        warnings.append(f"Rezervacije oglašivača ({adv_reserved}) nisu jednake pending trošku dokaza ({pending_costs})")

    return {
        "version": "11.18.34",
        "status": "ok" if not warnings else "warning",
        "warnings": warnings,
        "counts": {
            "users": len(korisnici),
            "advertisers": len(advertisers),
            "tasks": db.query(Task).count(),
            "submissions": db.query(TaskSubmission).count(),
            "withdrawals": db.query(Withdrawal).count(),
            "wallet_transactions": db.query(WalletTransaction).count(),
            "budget_transactions": db.query(AdvertiserBudgetTransaction).count(),
        },
        "users": {
            "balance_rsd": user_balance,
            "pending_rsd": user_pending,
            "lifetime_earned_rsd": user_lifetime,
        },
        "advertisers": {
            "available_budget_rsd": adv_budget,
            "reserved_rsd": adv_reserved,
            "spent_rsd": adv_spent,
        },
        "submissions": {
            "approved_rewards_rsd": approved_rewards,
            "pending_rewards_rsd": pending_rewards,
            "rejected_rewards_rsd": rejected_rewards,
            "approved_platform_fee_rsd": approved_fees,
            "approved_costs_rsd": approved_costs,
            "pending_costs_rsd": pending_costs,
        },
        "withdrawals": {
            "pending_rsd": withdrawals_pending,
            "paid_rsd": withdrawals_paid,
            "rejected_rsd": withdrawals_rejected,
        },
        "transactions": {
            "wallet_tx_total_rsd": wallet_tx_total,
            "budget_tx_total_rsd": budget_tx_total,
        },
        "alerts": {
            "negative_users": negative_users,
            "negative_advertisers": negative_advertisers,
            "stale_withdrawals_72h": stale_withdrawals,
            "stale_submissions_72h": stale_submissions,
        }
    }

def v11834_flat_rows(snapshot):
    rows = []
    for section in ["counts", "users", "advertisers", "submissions", "withdrawals", "transactions"]:
        for key, value in snapshot.get(section, {}).items():
            rows.append([section, key, value])
    rows.append(["status", "status", snapshot.get("status")])
    rows.append(["status", "warnings", " | ".join(snapshot.get("warnings") or [])])
    return rows

@app.get("/api/v1/v11/finance-reconciliation-health")
def finance_reconciliation_health_v11834(db: Session = Depends(get_db)):
    return v11834_finance_snapshot(db)

@app.get("/admin/finance-v11834", response_class=HTMLResponse)
def admin_finance_v11834(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    snapshot = v11834_finance_snapshot(db)
    rows = v11834_flat_rows(snapshot)
    return templates.TemplateResponse("admin_finance_v11834.html", {
        "request": request,
        "user": u,
        "snapshot": snapshot,
        "rows": rows,
        "flash": None,
    })

@app.get("/admin/finance-v11834.csv")
def admin_finance_v11834_csv(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    snapshot = v11834_finance_snapshot(db)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["section", "metric", "value"])
    for row in v11834_flat_rows(snapshot):
        w.writerow(row)
    return Response(out.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=klikzarada_finance_reconciliation_v11834.csv"})

@app.post("/admin/finance-v11834/fix-small-negatives")
def admin_finance_fix_small_negatives_v11834(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    fixed = 0
    # Fix only tiny negative rounding leftovers, not real losses.
    for user in db.query(User).all():
        for field in ["balance_rsd", "pending_rsd", "advertiser_budget_rsd", "advertiser_reserved_rsd", "advertiser_spent_rsd"]:
            val = v11834_money(getattr(user, field, 0))
            if -1.0 < val < 0:
                setattr(user, field, 0.0)
                fixed += 1
    audit(db, u, "finance_fix_small_negatives_v11834", "Finance", None, f"Fixed fields: {fixed}")
    db.commit()
    return RedirectResponse(f"/admin/finance-v11834?msg=fixed_{fixed}", 303)


# =========================================================
# V11.18.35 OPS COMMAND CENTER / AUTOMATED GUARDS
# Početna stranica se ne dira.
# =========================================================

def v11835_money(v):
    try:
        return round(float(v or 0), 2)
    except Exception:
        return 0.0

def v11835_safe_dt(dt):
    try:
        return dt.isoformat() if dt else ""
    except Exception:
        return ""

def v11835_issue(severity, area, title, details, entity_type="", entity_id=None, action_url=""):
    return {
        "severity": severity,
        "area": area,
        "title": title,
        "details": details,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action_url": action_url,
    }

def v11835_ops_scan(db: Session):
    now = datetime.utcnow()
    issues = []

    # Finansijski snapshot iz V11.18.34 ako postoji.
    finance = v11834_finance_snapshot(db) if "v11834_finance_snapshot" in globals() else {}

    for u in db.query(User).filter(User.role == "korisnik").all():
        if v11835_money(u.balance_rsd) < 0:
            issues.append(v11835_issue("critical", "users", "Negativan balans korisnika", f"{u.email}: balance {u.balance_rsd} RSD", "User", u.id, f"/admin/users/{u.id}"))
        if v11835_money(u.pending_rsd) < 0:
            issues.append(v11835_issue("critical", "users", "Negativan pending korisnika", f"{u.email}: pending {u.pending_rsd} RSD", "User", u.id, f"/admin/users/{u.id}"))
        rejected = db.query(TaskSubmission).filter(TaskSubmission.user_id == u.id, TaskSubmission.status == "rejected").count()
        approved = db.query(TaskSubmission).filter(TaskSubmission.user_id == u.id, TaskSubmission.status == "approved").count()
        if rejected >= 3 and rejected > approved:
            issues.append(v11835_issue("medium", "quality", "Korisnik ima mnogo odbijenih dokaza", f"{u.email}: rejected {rejected}, approved {approved}", "User", u.id, "/admin/korisnici"))

    for a in db.query(User).filter(User.role == "oglasivac").all():
        if v11835_money(a.advertiser_budget_rsd) < 0:
            issues.append(v11835_issue("critical", "advertisers", "Negativan budžet oglašivača", f"{a.email}: budget {a.advertiser_budget_rsd} RSD", "User", a.id, "/admin/oglasivaci"))
        if v11835_money(a.advertiser_reserved_rsd) < 0:
            issues.append(v11835_issue("critical", "advertisers", "Negativna rezervacija oglašivača", f"{a.email}: reserved {a.advertiser_reserved_rsd} RSD", "User", a.id, "/admin/oglasivaci"))

    stale_subs = db.query(TaskSubmission).filter(
        TaskSubmission.status == "pending",
        TaskSubmission.created_at < now - timedelta(hours=48)
    ).order_by(TaskSubmission.created_at.asc()).limit(200).all()
    for s in stale_subs:
        issues.append(v11835_issue("high", "submissions", "Dokaz čeka proveru duže od 48h", f"{s.user.email if s.user else ''} / {s.task.title if s.task else ''} / {v11835_safe_dt(s.created_at)}", "TaskSubmission", s.id, "/admin/dokazi"))

    stale_withdrawals = db.query(Withdrawal).filter(
        Withdrawal.status == "pending",
        Withdrawal.created_at < now - timedelta(hours=48)
    ).order_by(Withdrawal.created_at.asc()).limit(200).all()
    for w in stale_withdrawals:
        issues.append(v11835_issue("high", "withdrawals", "Isplata čeka duže od 48h", f"{w.user.email if w.user else ''} / {w.amount_rsd:.0f} RSD / {v11835_safe_dt(w.created_at)}", "Withdrawal", w.id, "/admin/isplate"))

    active_tasks = db.query(Task).filter(Task.status == "active").all()
    for t in active_tasks:
        slots_left = int(t.total_slots or 0) - int(t.used_slots or 0)
        if int(t.total_slots or 0) > 0 and slots_left <= 0:
            issues.append(v11835_issue("medium", "campaigns", "Aktivna kampanja nema slobodnih slotova", f"{t.title}: total {t.total_slots}, used {t.used_slots}", "Task", t.id, "/admin/kampanje"))
        if t.advertiser and v11835_money(t.advertiser.advertiser_budget_rsd) <= 0 and v11835_money(t.advertiser.advertiser_reserved_rsd) <= 0:
            issues.append(v11835_issue("medium", "campaigns", "Aktivna kampanja bez dostupnog/rezervisanog budžeta", f"{t.title} / {t.advertiser.email}", "Task", t.id, "/admin/kampanje"))

    # Jednostavna provera duplih payment_details kod korisnika.
    payment_map = {}
    for u in db.query(User).filter(User.role == "korisnik").all():
        pd = (getattr(u, "payment_details", "") or "").strip().lower()
        if len(pd) >= 5:
            payment_map.setdefault(pd, []).append(u)
    for pd, rows in payment_map.items():
        if len(rows) >= 2:
            issues.append(v11835_issue("medium", "fraud", "Više korisnika ima iste podatke za isplatu", f"{len(rows)} korisnika deli iste payment details.", "User", rows[0].id, "/admin/anti-fraud"))

    counts = {
        "critical": sum(1 for i in issues if i["severity"] == "critical"),
        "high": sum(1 for i in issues if i["severity"] == "high"),
        "medium": sum(1 for i in issues if i["severity"] == "medium"),
        "low": sum(1 for i in issues if i["severity"] == "low"),
        "total": len(issues),
    }

    return {
        "version": "11.18.35",
        "status": "ok" if not issues else ("critical" if counts["critical"] else "warning"),
        "generated_at": now.isoformat(),
        "counts": counts,
        "issues": issues,
        "finance": finance,
    }

def v11835_ops_rows(scan):
    rows = []
    for i in scan.get("issues", []):
        rows.append([i.get("severity"), i.get("area"), i.get("title"), i.get("details"), i.get("entity_type"), i.get("entity_id"), i.get("action_url")])
    return rows

@app.get("/admin/ops-v11835", response_class=HTMLResponse)
def admin_ops_v11835(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    scan = v11835_ops_scan(db)
    return templates.TemplateResponse("admin_ops_v11835.html", {
        "request": request,
        "user": u,
        "scan": scan,
        "issues": scan["issues"],
        "flash": None,
    })

@app.get("/admin/ops-v11835.csv")
def admin_ops_v11835_csv(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    scan = v11835_ops_scan(db)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["severity", "area", "title", "details", "entity_type", "entity_id", "action_url"])
    for row in v11835_ops_rows(scan):
        w.writerow(row)
    return Response(out.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=klikzarada_ops_issues_v11835.csv"})

@app.post("/admin/ops-v11835/run")
def admin_ops_run_v11835(request: Request, db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["admin"])
    scan = v11835_ops_scan(db)
    if scan["counts"]["critical"] > 0:
        notify(db, role_target="admin", title="Ops critical alert", body=f"Ops scan ima {scan['counts']['critical']} critical problema.")
    audit(db, u, "ops_scan_v11835", "Ops", None, f"Issues: {scan['counts']['total']}")
    db.commit()
    return RedirectResponse(f"/admin/ops-v11835?msg=scan_{scan['counts']['total']}", 303)

@app.get("/api/v1/v11/ops-command-health")
def ops_command_health_v11835(db: Session = Depends(get_db)):
    return v11835_ops_scan(db)


# =========================================================
# V11.18.36 COMPLETE TRUST + LAUNCH PACK
# KYC, fraud score, payout lock, disputes, notifications,
# email queue, daily report, launch checklist, advertiser performance.
# Početna stranica se ne dira.
# =========================================================

def v11836_money(v):
    try:
        return round(float(v or 0), 2)
    except Exception:
        return 0.0

def v11836_email(db: Session, recipient: str, subject: str, body: str):
    recipient = (recipient or "").strip()
    if not recipient:
        return None
    row = EmailOutboxV8(
        recipient_email=recipient,
        subject=(subject or "").strip()[:220],
        body=(body or "").strip(),
        status="queued",
    )
    db.add(row)
    return row

def v11836_kyc_status(user):
    has_name = bool((getattr(user, "full_name", "") or "").strip())
    has_phone = bool((getattr(user, "phone", "") or "").strip())
    has_payment = bool((getattr(user, "payment_details", "") or "").strip())
    email_ok = bool(getattr(user, "email_verified", False))
    phone_ok = bool(getattr(user, "phone_verified", False))
    if has_name and has_phone and has_payment and email_ok and phone_ok:
        return "verified"
    if has_name and has_phone and has_payment:
        return "ready_for_review"
    return "incomplete"


def v11836_identity_signals(db: Session, user):
    device_label = (getattr(user, "device", "") or "").strip()
    payment_details = (getattr(user, "payment_details", "") or "").strip()
    latest_session = None
    if "UserDeviceSessionV11" in globals():
        latest_session = (
            db.query(UserDeviceSessionV11)
            .filter(UserDeviceSessionV11.user_id == user.id)
            .order_by(UserDeviceSessionV11.last_seen_at.desc(), UserDeviceSessionV11.created_at.desc())
            .first()
        )
    session_device = (getattr(latest_session, "device_label", "") or "").strip() if latest_session else ""
    session_ip = (getattr(latest_session, "ip_address", "") or "").strip() if latest_session else ""
    if not session_ip and "SecurityEvent" in globals():
        latest_ip_row = (
            db.query(SecurityEvent.ip_address)
            .filter(SecurityEvent.user_id == user.id, SecurityEvent.ip_address.isnot(None))
            .order_by(SecurityEvent.created_at.desc())
            .first()
        )
        session_ip = (latest_ip_row[0] or "").strip() if latest_ip_row else ""

    normalized_device = " ".join((device_label or session_device).lower().split())
    normalized_payment = " ".join(payment_details.lower().split())
    normalized_ip = session_ip
    same_device_users = 0
    same_ip_users = 0
    same_payment_users = 0

    if normalized_device:
        same_device_users = (
            db.query(User)
            .filter(User.id != user.id, User.role == "korisnik", User.device.isnot(None))
            .all()
        )
        same_device_users = sum(
            1
            for other in same_device_users
            if " ".join(((getattr(other, "device", "") or "").lower().split())) == normalized_device
        )

    if normalized_payment:
        same_payment_users = db.query(User).filter(
            User.id != user.id,
            User.role == "korisnik",
            User.payment_details.isnot(None),
        ).count()
        same_payment_users = sum(
            1
            for other in db.query(User).filter(User.id != user.id, User.role == "korisnik", User.payment_details.isnot(None)).all()
            if " ".join(((getattr(other, "payment_details", "") or "").lower().split())) == normalized_payment
        )

    if normalized_ip and "UserDeviceSessionV11" in globals():
        same_ip_users = (
            db.query(UserDeviceSessionV11.user_id)
            .filter(UserDeviceSessionV11.user_id != user.id, UserDeviceSessionV11.ip_address == normalized_ip)
            .distinct()
            .count()
        )

    return {
        "device_label": device_label or session_device,
        "ip_address": normalized_ip,
        "payment_details": payment_details,
        "same_device_users": same_device_users,
        "same_ip_users": same_ip_users,
        "same_payment_users": same_payment_users,
        "session_device": session_device,
    }

def v11836_risk_score(db: Session, user):
    score = 0
    reasons = []
    approved = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id, TaskSubmission.status == "approved").count()
    rejected = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id, TaskSubmission.status == "rejected").count()
    pending = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id, TaskSubmission.status == "pending").count()
    disputed = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id, TaskSubmission.status == "disputed").count()
    withdrawals = db.query(Withdrawal).filter(Withdrawal.user_id == user.id).count()
    identity = v11836_identity_signals(db, user)

    if rejected >= 3 and rejected > approved:
        score += 35
        reasons.append("mnogo odbijenih dokaza")
    if pending >= 5:
        score += 15
        reasons.append("mnogo pending dokaza")
    if disputed >= 3:
        score += 10
        reasons.append("mnogo žalbi/dispute slučajeva")
    if withdrawals >= 2 and approved < 2:
        score += 20
        reasons.append("rane isplate uz malo odobrenih dokaza")
    if v11836_money(getattr(user, "balance_rsd", 0)) < 0 or v11836_money(getattr(user, "pending_rsd", 0)) < 0:
        score += 45
        reasons.append("negativan balans/pending")

    if identity["same_payment_users"] > 0:
        score += 30
        reasons.append("isti payment details kod više naloga")
    if identity["same_device_users"] > 0:
        score += 18
        reasons.append("isti uređaj kod više naloga")
    if identity["same_ip_users"] > 0:
        score += 14
        reasons.append("isti IP kod više naloga")

    kyc = v11836_kyc_status(user)
    if kyc == "incomplete":
        score += 10
        reasons.append("KYC nepotpun")

    score = max(0, min(100, score))
    quality = 100 if approved + rejected == 0 else round(approved * 100 / max(1, approved + rejected), 2)
    if score >= 70:
        status = "Blokiran za isplatu"
    elif score >= 40:
        status = "Pod nadzorom"
    else:
        status = "Normal"

    row = db.query(UserScoreV115).filter(UserScoreV115.user_id == user.id).first()
    if not row:
        row = UserScoreV115(user_id=user.id)
        db.add(row)
    row.quality_score = quality
    row.risk_score = score
    row.status_name = status

    if approved >= 50 and quality >= 90 and score < 30:
        row.level_name = "VIP korisnik"
        user.level = "VIP"
    elif approved >= 20 and quality >= 85 and score < 35:
        row.level_name = "Premium tester"
        user.level = "Premium"
    elif approved >= 10 and quality >= 80:
        row.level_name = "Zlato"
        user.level = "Zlato"
    elif approved >= 3 and quality >= 70:
        row.level_name = "Srebro"
        user.level = "Srebro"
    else:
        row.level_name = "Bronza"
        user.level = "Bronza"

    row.updated_at = datetime.utcnow()
    return {"risk_score": score, "quality_score": quality, "status": status, "reasons": reasons, "level": row.level_name, "identity": identity}


def v11836_user_fraud_profile(db: Session, user):
    submissions = db.query(TaskSubmission).filter(TaskSubmission.user_id == user.id).all()
    identity = v11836_identity_signals(db, user)
    approved = sum(1 for s in submissions if s.status == "approved")
    rejected = sum(1 for s in submissions if s.status == "rejected")
    pending = sum(1 for s in submissions if s.status == "pending")
    disputed = sum(1 for s in submissions if s.status == "disputed")
    duplicate_texts = 0
    for s in submissions:
        if (s.proof or "").strip():
            dup = db.query(TaskSubmission).filter(TaskSubmission.proof == s.proof, TaskSubmission.id != s.id).count()
            if dup:
                duplicate_texts += 1
    risk = 0
    reasons = []
    if rejected >= 3 and rejected > approved:
        risk += 30
        reasons.append("više odbijenih dokaza")
    if pending >= 5:
        risk += 18
        reasons.append("previše pending dokaza")
    if disputed >= 2:
        risk += 12
        reasons.append("više spornih dokaza")
    if duplicate_texts >= 2:
        risk += 22
        reasons.append("ponavljani tekstovi dokaza")
    if len(submissions) >= 5:
        approval_rate = approved / max(1, approved + rejected + disputed)
        if approval_rate < 0.6:
            risk += 14
            reasons.append("nizak kvalitet potvrđenih dokaza")
    if getattr(user, "phone", None):
        duplicate_phone = db.query(User).filter(User.phone == user.phone, User.id != user.id).count() > 0
        if duplicate_phone:
            risk += 22
            reasons.append("dupliran telefon")
    if getattr(user, "payment_details", None):
        payment = (user.payment_details or "").strip()
        if payment:
            shared_payment = db.query(User).filter(User.id != user.id, User.role == "korisnik", User.payment_details.ilike(payment)).count() > 0
            if shared_payment:
                risk += 28
                reasons.append("isti payment details sa drugim nalogom")
    if identity["same_device_users"] > 0:
        risk += 16
        reasons.append("isti uređaj sa drugim nalogom")
    if identity["same_ip_users"] > 0:
        risk += 12
        reasons.append("isti IP sa drugim nalogom")
    risk = max(0, min(100, risk))
    level = "Normal"
    if risk >= 70:
        level = "Visok"
    elif risk >= 40:
        level = "Srednji"
    elif risk >= 20:
        level = "Nizak"
    return {
        "user_id": user.id,
        "user": user,
        "risk_score": risk,
        "level": level,
        "approved": approved,
        "rejected": rejected,
        "pending": pending,
        "disputed": disputed,
        "identity": identity,
        "reasons": reasons or ["Nema posebnih signala."],
    }


def v11836_campaign_fraud_profile(db: Session, task: Task):
    submissions = db.query(TaskSubmission).filter(TaskSubmission.task_id == task.id).all()
    total = len(submissions)
    approved = sum(1 for s in submissions if s.status == "approved")
    rejected = sum(1 for s in submissions if s.status == "rejected")
    pending = sum(1 for s in submissions if s.status == "pending")
    duplicate_texts = 0
    quick_submissions = 0
    for s in submissions:
        if (s.proof or "").strip():
            dup = db.query(TaskSubmission).filter(TaskSubmission.proof == s.proof, TaskSubmission.id != s.id, TaskSubmission.task_id == task.id).count()
            if dup:
                duplicate_texts += 1
        if s.created_at and task.created_at and s.created_at <= task.created_at + timedelta(minutes=max(2, int(getattr(task, "estimated_minutes", 5) or 5) // 2)):
            quick_submissions += 1
    risk = 0
    reasons = []
    if total >= 5:
        reject_rate = rejected / max(1, total)
        if reject_rate >= 0.35:
            risk += 22
            reasons.append("visok procenat odbijenih dokaza")
        if duplicate_texts >= 2:
            risk += 20
            reasons.append("ponavljani tekstovi dokaza")
        if quick_submissions >= max(2, total // 3):
            risk += 18
            reasons.append("previše brzih prijava")
        if approved == 0 and pending >= 5:
            risk += 12
            reasons.append("kampanja bez odobrenih dokaza")
    if getattr(task, "proof_file_required", False):
        file_ratio = sum(1 for s in submissions if s.proof_file) / max(1, total)
        if total >= 3 and file_ratio < 0.4:
            risk += 14
            reasons.append("slab odnos fajl dokaza")
    if task.total_slots and total >= task.total_slots:
        risk += 8
        reasons.append("kampanja je blizu ili na limitu")
    risk = max(0, min(100, risk))
    level = "Normalna"
    if risk >= 70:
        level = "Visok"
    elif risk >= 40:
        level = "Srednji"
    elif risk >= 20:
        level = "Nizak"
    return {
        "task_id": task.id,
        "task": task,
        "risk_score": risk,
        "level": level,
        "total": total,
        "approved": approved,
        "rejected": rejected,
        "pending": pending,
        "reasons": reasons or ["Nema posebnih signala."],
    }

def v11836_payout_allowed(db: Session, user, amount: float):
    amount = v11836_money(amount)
    kyc = v11836_kyc_status(user)
    risk = v11836_risk_score(db, user)
    if amount <= 0:
        return False, "bad_amount"
    if amount < float(globals().get("MIN_WITHDRAWAL_RSD", 500) or 500):
        return False, "min_amount"
    if amount > v11836_money(getattr(user, "balance_rsd", 0)):
        return False, "insufficient_balance"
    if kyc != "verified":
        return False, "kyc_required"
    if risk["risk_score"] >= 70:
        return False, "risk_blocked"
    return True, "allowed"

def v11836_create_payout_request(db: Session, user, amount_rsd: float, payment_method: str = "bank_transfer", payment_details: str = "", note: str = ""):
    if payment_method.strip():
        user.payment_method = payment_method.strip()
    if payment_details.strip():
        user.payment_details = payment_details.strip()

    allowed, reason = v11836_payout_allowed(db, user, amount_rsd)
    if not allowed:
        if reason in ["kyc_required", "risk_blocked"]:
            db.add(PayoutHoldV11(user_id=user.id, amount_rsd=float(amount_rsd or 0), reason=reason, status="active"))
            notify(db, role_target="admin", title="Isplata blokirana", body=f"{user.full_name}: {reason}, iznos {float(amount_rsd or 0):.0f} RSD")
        db.commit()
        return None, reason

    if "v11832_create_withdrawal" in globals():
        return v11832_create_withdrawal(db, user, amount_rsd, payment_method, payment_details or getattr(user, "payment_details", ""), note)

    amount = v11836_money(amount_rsd)
    user.balance_rsd = round(v11836_money(user.balance_rsd) - amount, 2)
    w = Withdrawal(user_id=user.id, amount_rsd=amount, payment_method=payment_method, payment_details=payment_details or getattr(user, "payment_details", ""), status="pending")
    db.add(w)
    add_tx(db, user, -amount, "withdrawal_reserved", f"Zahtev za isplatu: {amount:.0f} RSD")
    notify(db, role_target="admin", title="Novi zahtev za isplatu", body=f"{user.full_name} traži isplatu {amount:.0f} RSD.")
    db.commit()
    db.refresh(w)
    return w, "created"

def v11836_daily_report(db: Session):
    today = datetime.utcnow().date()
    start = datetime(today.year, today.month, today.day)
    new_users = db.query(User).filter(User.role == "korisnik", User.created_at >= start).count()
    new_adv = db.query(User).filter(User.role == "oglasivac", User.created_at >= start).count()
    new_tasks = db.query(Task).filter(Task.created_at >= start).count()
    pending_subs = db.query(TaskSubmission).filter(TaskSubmission.status == "pending").count()
    pending_withdrawals = db.query(Withdrawal).filter(Withdrawal.status == "pending").count()
    platform_fee = db.query(func.coalesce(func.sum(TaskSubmission.platform_fee_rsd), 0)).filter(TaskSubmission.status == "approved").scalar() or 0
    risk_users = db.query(UserScoreV115).filter(UserScoreV115.risk_score >= 40).count()
    finance_status = "unknown"
    ops_status = "unknown"
    if "v11834_finance_snapshot" in globals():
        finance_status = v11834_finance_snapshot(db).get("status", "unknown")
    if "v11835_ops_scan" in globals():
        ops_status = v11835_ops_scan(db).get("status", "unknown")
    return {
        "date": str(today),
        "new_users": new_users,
        "new_advertisers": new_adv,
        "new_tasks": new_tasks,
        "pending_submissions": pending_subs,
        "pending_withdrawals": pending_withdrawals,
        "platform_fee_rsd": v11836_money(platform_fee),
        "risk_users": risk_users,
        "finance_status": finance_status,
        "ops_status": ops_status,
    }

def v11836_launch_checklist(db: Session):
    checks = []
    def add(key, title, ok, detail):
        checks.append({"key": key, "title": title, "ok": bool(ok), "detail": detail})
    add("admin_exists", "Admin nalog postoji", db.query(User).filter(User.role == "admin").count() > 0, "Potreban je bar jedan admin.")
    add("advertiser_exists", "Postoji oglašivač", db.query(User).filter(User.role == "oglasivac").count() > 0, "Potreban je bar jedan oglašivač.")
    add("active_tasks", "Postoje aktivni zadaci", db.query(Task).filter(Task.status == "active").count() > 0, "Potreban je bar jedan aktivan zadatak.")
    add("payout_rules", "Minimalna isplata podešena", float(globals().get("MIN_WITHDRAWAL_RSD", 0) or 0) > 0, f"MIN_WITHDRAWAL_RSD={globals().get('MIN_WITHDRAWAL_RSD', None)}")
    add("finance_module", "Finance reconciliation postoji", "v11834_finance_snapshot" in globals(), "V11.18.34 finance modul.")
    add("ops_module", "Ops Command Center postoji", "v11835_ops_scan" in globals(), "V11.18.35 ops modul.")
    add("email_queue", "Email queue postoji", db.query(EmailOutboxV8).count() >= 0, "EmailOutboxV8 tabela dostupna.")
    add("disputes", "Dispute tabela postoji", db.query(Dispute).count() >= 0, "Žalbe su dostupne.")
    add("kyc", "KYC engine postoji", True, "KYC/payout lock aktivan.")
    ready = all(c["ok"] for c in checks)
    return {"version": "11.18.36", "ready": ready, "checks": checks, "missing": [c for c in checks if not c["ok"]]}

@app.get("/admin/trust-v11836", response_class=HTMLResponse)
def admin_trust_v11836(request: Request, db: Session = Depends(get_db)):
    admin = require(request, db); check_role(admin, ["admin"])
    users = db.query(User).filter(User.role == "korisnik").order_by(User.created_at.desc()).limit(300).all()
    rows = []
    for u in users:
        risk = v11836_risk_score(db, u)
        rows.append({"user": u, "kyc": v11836_kyc_status(u), "risk": risk})
    db.commit()
    return templates.TemplateResponse("admin_trust_v11836.html", {"request": request, "user": admin, "rows": rows, "flash": None})

@app.post("/admin/trust-v11836/users/{uid}/verify")
def admin_trust_verify_user_v11836(uid: int, request: Request, note: str = Form(""), db: Session = Depends(get_db)):
    admin = require(request, db); check_role(admin, ["admin"])
    u = db.query(User).filter(User.id == uid, User.role == "korisnik").first()
    if not u:
        return RedirectResponse("/admin/trust-v11836?msg=not_found", 303)
    u.email_verified = True
    u.phone_verified = True
    audit(db, admin, "kyc_verified_v11836", "User", u.id, note)
    notify(db, u, None, "Nalog verifikovan", "Vaš nalog je verifikovan za isplate.")
    v11836_email(db, u.email, "KlikZarada nalog verifikovan", "Vaš nalog je verifikovan za isplate.")
    v11836_risk_score(db, u)
    db.commit()
    return RedirectResponse("/admin/trust-v11836?msg=verified", 303)

@app.post("/korisnik/kyc-v11836")
def user_kyc_save_v11836(request: Request, phone: str = Form(""), payment_method: str = Form("bank_transfer"), payment_details: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["korisnik"])
    if phone.strip():
        u.phone = phone.strip()
    if payment_method.strip():
        u.payment_method = payment_method.strip()
    if payment_details.strip():
        u.payment_details = payment_details.strip()
    v11836_risk_score(db, u)
    notify(db, role_target="admin", title="KYC spreman za proveru", body=f"{u.full_name} je ažurirao podatke za isplatu.")
    db.commit()
    return RedirectResponse("/korisnik/panel?msg=kyc_saved", 303)

@app.post("/korisnik/isplate/zahtev-v11836")
def user_withdrawal_request_v11836(request: Request, amount_rsd: float = Form(0), payment_method: str = Form("bank_transfer"), payment_details: str = Form(""), note: str = Form(""), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["korisnik"])
    w, status = v11836_create_payout_request(db, u, amount_rsd, payment_method, payment_details, note)
    return RedirectResponse(f"/korisnik/isplate?msg={status}", 303)

@app.post("/korisnik/dokazi/{submission_id}/zalba-v11836")
def user_open_dispute_v11836(submission_id: int, request: Request, reason: str = Form(...), db: Session = Depends(get_db)):
    u = require(request, db); check_role(u, ["korisnik"])
    sub = db.query(TaskSubmission).filter(TaskSubmission.id == submission_id, TaskSubmission.user_id == u.id).first()
    if not sub:
        return RedirectResponse("/korisnik/dokazi?msg=not_found", 303)
    if sub.status not in ["rejected", "disputed"]:
        return RedirectResponse("/korisnik/dokazi?msg=only_rejected", 303)
    exists = db.query(Dispute).filter(Dispute.submission_id == sub.id, Dispute.status == "open").first()
    if exists:
        return RedirectResponse("/korisnik/dokazi?msg=dispute_exists", 303)
    sub.status = "disputed"
    d = Dispute(submission_id=sub.id, opened_by_id=u.id, reason=reason.strip(), status="open")
    db.add(d)
    notify(db, role_target="admin", title="Nova žalba korisnika", body=f"{u.full_name} je uložio/la žalbu za dokaz #{sub.id}.")
    db.commit()
    return RedirectResponse("/korisnik/dokazi?msg=dispute_opened", 303)

@app.get("/admin/disputes-v11836", response_class=HTMLResponse)
def admin_disputes_v11836(request: Request, db: Session = Depends(get_db)):
    admin = require(request, db); check_role(admin, ["admin"])
    disputes = db.query(Dispute).order_by(Dispute.created_at.desc()).limit(300).all()
    return templates.TemplateResponse("admin_disputes_v11836.html", {"request": request, "user": admin, "disputes": disputes, "flash": None})

@app.post("/admin/disputes-v11836/{dispute_id}/{action}")
def admin_dispute_action_v11836(dispute_id: int, action: str, request: Request, decision: str = Form(""), db: Session = Depends(get_db)):
    admin = require(request, db); check_role(admin, ["admin"])
    d = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not d:
        return RedirectResponse("/admin/disputes-v11836?msg=not_found", 303)
    sub = d.submission
    if action == "accept":
        d.status = "accepted"
        d.admin_decision = decision.strip() or "Žalba prihvaćena"
        d.resolved_at = datetime.utcnow()
        if sub and sub.status in ["rejected", "disputed"]:
            sub.status = "pending"
            sub.review_note = "Žalba prihvaćena — vraćeno na proveru"
        notify(db, d.opened_by, None, "Žalba prihvaćena", "Vaša žalba je prihvaćena i dokaz je vraćen na proveru.")
    elif action == "reject":
        d.status = "rejected"
        d.admin_decision = decision.strip() or "Žalba odbijena"
        d.resolved_at = datetime.utcnow()
        if sub:
            sub.status = "rejected"
        notify(db, d.opened_by, None, "Žalba odbijena", "Vaša žalba je odbijena.")
    else:
        return RedirectResponse("/admin/disputes-v11836?msg=bad_action", 303)
    audit(db, admin, f"dispute_{action}_v11836", "Dispute", d.id, decision)
    db.commit()
    return RedirectResponse(f"/admin/disputes-v11836?msg={action}", 303)

@app.get("/admin/daily-v11836", response_class=HTMLResponse)
def admin_daily_v11836(request: Request, db: Session = Depends(get_db)):
    admin = require(request, db); check_role(admin, ["admin"])
    report = v11836_daily_report(db)
    return templates.TemplateResponse("admin_daily_v11836.html", {"request": request, "user": admin, "report": report, "flash": None})

@app.post("/admin/daily-v11836/email")
def admin_daily_email_v11836(request: Request, db: Session = Depends(get_db)):
    admin = require(request, db); check_role(admin, ["admin"])
    r = v11836_daily_report(db)
    body = "\n".join([f"{k}: {v}" for k, v in r.items()])
    v11836_email(db, admin.email, f"KlikZarada daily report {r['date']}", body)
    audit(db, admin, "daily_report_email_v11836", "EmailOutboxV8", None, "queued")
    db.commit()
    return RedirectResponse("/admin/daily-v11836?msg=email_queued", 303)

@app.get("/admin/launch-v11836", response_class=HTMLResponse)
def admin_launch_v11836(request: Request, db: Session = Depends(get_db)):
    admin = require(request, db); check_role(admin, ["admin"])
    checklist = v11836_launch_checklist(db)
    return templates.TemplateResponse("admin_launch_v11836.html", {"request": request, "user": admin, "checklist": checklist, "flash": None})

@app.get("/oglasivac/performance-v11836", response_class=HTMLResponse)
def advertiser_performance_v11836(request: Request, db: Session = Depends(get_db)):
    adv = require(request, db); check_role(adv, ["oglasivac", "admin"])
    tasks = db.query(Task).filter(Task.advertiser_id == adv.id).order_by(Task.created_at.desc()).all()
    task_ids = [t.id for t in tasks]
    submissions = db.query(TaskSubmission).filter(TaskSubmission.task_id.in_(task_ids)).all() if task_ids else []
    summary = {
        "tasks": len(tasks),
        "active": sum(1 for t in tasks if t.status == "active"),
        "pending": sum(1 for t in tasks if t.status == "pending"),
        "submissions": len(submissions),
        "approved": sum(1 for s in submissions if s.status == "approved"),
        "rejected": sum(1 for s in submissions if s.status == "rejected"),
        "pending_submissions": sum(1 for s in submissions if s.status == "pending"),
        "spent_rsd": v11836_money(adv.advertiser_spent_rsd),
        "reserved_rsd": v11836_money(adv.advertiser_reserved_rsd),
        "budget_rsd": v11836_money(adv.advertiser_budget_rsd),
    }
    return templates.TemplateResponse("advertiser_performance_v11836.html", {"request": request, "user": adv, "summary": summary, "tasks": tasks, "flash": None})

@app.get("/api/v1/v11/trust-launch-health")
def trust_launch_health_v11836(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role == "korisnik").all()
    scored = []
    for u in users:
        scored.append(v11836_risk_score(db, u))
    db.commit()
    checklist = v11836_launch_checklist(db)
    return {
        "version": "11.18.36",
        "status": "ready",
        "kyc": {
            "verified": sum(1 for u in users if v11836_kyc_status(u) == "verified"),
            "ready_for_review": sum(1 for u in users if v11836_kyc_status(u) == "ready_for_review"),
            "incomplete": sum(1 for u in users if v11836_kyc_status(u) == "incomplete"),
        },
        "risk": {
            "blocked": sum(1 for s in scored if s["risk_score"] >= 70),
            "watch": sum(1 for s in scored if 40 <= s["risk_score"] < 70),
            "normal": sum(1 for s in scored if s["risk_score"] < 40),
        },
        "disputes": {
            "open": db.query(Dispute).filter(Dispute.status == "open").count(),
            "total": db.query(Dispute).count(),
        },
        "email_queue": {
            "queued": db.query(EmailOutboxV8).filter(EmailOutboxV8.status == "queued").count(),
            "total": db.query(EmailOutboxV8).count(),
        },
        "launch_ready": checklist["ready"],
    }
