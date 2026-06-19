from __future__ import annotations

import random
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services.admin_auth import require_admin_session
from ..services.json_store import append_json_row, read_json, update_json_row
from ..services.notifications import send_sms

router = APIRouter(prefix="/seller-applications", tags=["seller-applications"])
APPLICATIONS_FILE = "seller_applications.json"


class SellerApplicationCreate(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=180)
    category: str = Field(default="pekara", max_length=80)
    city: str = Field(..., min_length=2, max_length=120)
    address: str = Field(..., min_length=3, max_length=255)
    contact_name: str = Field(..., min_length=2, max_length=120)
    phone: str = Field(..., min_length=5, max_length=80)
    email: str | None = Field(default=None, max_length=160)
    website: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=2000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class SellerApplicationUpdate(BaseModel):
    status: str = Field(default="new", pattern="^(new|contacted|approved|rejected|duplicate)$")
    internal_note: str | None = Field(default=None, max_length=2000)


@router.post("", response_model=dict)
def create_seller_application(payload: SellerApplicationCreate):
    row = append_json_row(APPLICATIONS_FILE, {
        "business_name": payload.business_name.strip(),
        "category": payload.category.strip().lower(),
        "city": payload.city.strip(),
        "address": payload.address.strip(),
        "contact_name": payload.contact_name.strip(),
        "phone": payload.phone.strip(),
        "email": payload.email.strip() if payload.email else None,
        "website": payload.website.strip() if payload.website else None,
        "note": payload.note.strip() if payload.note else None,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "status": "new",
        "store_id": None,
        "seller_pin": None,
        "internal_note": None,
    })
    return {"ok": True, "application": row, "message": "Prijava je primljena. Kontaktiraćemo vas za potvrdu."}


@router.get("", response_model=list[dict])
def list_seller_applications(
    request: Request,
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    _: bool = Depends(require_admin_session),
):
    rows = list(reversed(read_json(APPLICATIONS_FILE, [])))
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return rows[:limit]


@router.patch("/{application_id}", response_model=dict)
def update_seller_application(application_id: str, payload: SellerApplicationUpdate, request: Request, _: bool = Depends(require_admin_session)):
    updated = update_json_row(APPLICATIONS_FILE, application_id, payload.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Prijava nije pronađena")
    return {"ok": True, "application": updated}


@router.post("/{application_id}/approve", response_model=dict)
def approve_seller_application(application_id: str, request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    rows = read_json(APPLICATIONS_FILE, [])
    application = next((r for r in rows if str(r.get("id")) == str(application_id)), None)
    if not application:
        raise HTTPException(status_code=404, detail="Prijava nije pronađena")
    if application.get("store_id"):
        store = db.get(models.Store, int(application["store_id"]))
        return {"ok": True, "store_id": application.get("store_id"), "seller_pin": application.get("seller_pin"), "message": "Prijava je već odobrena", "store": store}
    pin = str(random.randint(100000, 999999))
    store = models.Store(
        name=application.get("business_name"),
        city=application.get("city"),
        address=application.get("address"),
        latitude=application.get("latitude"),
        longitude=application.get("longitude"),
        website=application.get("website"),
        phone=application.get("phone"),
        seller_pin=pin,
        verified=True,
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    updated = update_json_row(APPLICATIONS_FILE, application_id, {"status": "approved", "store_id": store.id, "seller_pin": pin})
    if application.get("phone"):
        try:
            send_sms(application["phone"], f"Sačuvaj Hranu: vaš prodavac nalog je odobren. PIN za ulaz je {pin}. Link: /seller?store_id={store.id}", purpose="seller_application_approved", metadata={"store_id": store.id, "application_id": application_id})
        except Exception:
            pass
    return {"ok": True, "application": updated, "store_id": store.id, "seller_pin": pin, "seller_url": f"/seller?store_id={store.id}"}
