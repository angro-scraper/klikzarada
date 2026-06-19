from __future__ import annotations

import os
from pathlib import Path
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services.admin_auth import require_admin_session
from ..services.excel_database import excel_status
from ..services.notifications import notification_status
from ..services.payment_providers import get_payment_provider_status
from ..services.json_store import read_json

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/summary", response_model=dict)
def operations_summary(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    products_total = db.query(func.count(models.Product.id)).scalar() or 0
    public_products = db.query(func.count(models.Product.id)).filter(models.Product.status.in_(["public_discount", "seller_verified", "near_expiry"])).scalar() or 0
    products_with_images = db.query(func.count(models.Product.id)).filter(models.Product.image_url.isnot(None), models.Product.image_url != "").scalar() or 0
    stores_total = db.query(func.count(models.Store.id)).scalar() or 0
    stores_verified = db.query(func.count(models.Store.id)).filter(models.Store.verified == True).scalar() or 0
    reservations_total = db.query(func.count(models.Reservation.id)).scalar() or 0
    reservations_pending = db.query(func.count(models.Reservation.id)).filter(models.Reservation.status == "pending").scalar() or 0
    paid_total = float(db.query(func.coalesce(func.sum(models.Reservation.payable_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0)
    fee_total = float(db.query(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0)
    support_rows = read_json("support_tickets.json", [])
    seller_apps = read_json("seller_applications.json", [])
    return {
        "health": "ok",
        "products_total": products_total,
        "public_products": public_products,
        "products_with_images": products_with_images,
        "image_coverage_percent": round((products_with_images / products_total * 100), 1) if products_total else 0,
        "stores_total": stores_total,
        "stores_verified": stores_verified,
        "reservations_total": reservations_total,
        "reservations_pending": reservations_pending,
        "paid_total": round(paid_total, 2),
        "platform_fee_total": round(fee_total, 2),
        "support_open": sum(1 for r in support_rows if r.get("status") in {"open", "in_progress", "waiting_customer"}),
        "seller_applications_new": sum(1 for r in seller_apps if r.get("status") == "new"),
        "excel": excel_status(),
        "notifications": notification_status(),
        "payments": get_payment_provider_status(),
    }


@router.get("/readiness", response_model=dict)
def readiness(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    payment = get_payment_provider_status()
    notifications = notification_status()
    checks = [
        {"key": "admin_security", "label": "Admin PIN zaštita", "ok": bool(os.getenv("ADMIN_PIN")), "fix": "Postavi ADMIN_PIN u .env"},
        {"key": "payment_provider", "label": "Payment provider", "ok": bool(payment.get("provider_ready")), "fix": "Popuni MERCHANT_ACCOUNT ili gateway kredencijale"},
        {"key": "sms_provider", "label": "SMS/OTP servis", "ok": bool(notifications.get("configured")), "fix": "Podesi SMS_HTTP_URL ako koristiš realan SMS"},
        {"key": "excel_backup", "label": "Excel backup", "ok": bool(excel_status().get("exists")), "fix": "Klikni Snimi bazu u Excel"},
        {"key": "public_products", "label": "Javne ponude", "ok": (db.query(func.count(models.Product.id)).filter(models.Product.status.in_(["public_discount", "seller_verified", "near_expiry"])).scalar() or 0) > 0, "fix": "Dodaj ili odobri ponude"},
    ]
    score = round(sum(1 for c in checks if c["ok"]) / len(checks) * 100)
    return {"score": score, "checks": checks}
