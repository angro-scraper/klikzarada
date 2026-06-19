
from __future__ import annotations

import random
import string
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services.admin_auth import require_admin_session
from ..services.json_store import append_json_row, read_json, update_json_row, write_json
from ..services.pricing import normalize_phone

router = APIRouter(prefix="/engagement", tags=["v36-customer-engagement"])

class FavoriteCreate(BaseModel):
    phone: str = Field(..., min_length=5, max_length=80)
    store_id: int

class SavedSearchCreate(BaseModel):
    phone: str = Field(..., min_length=5, max_length=80)
    label: str = Field(..., min_length=2, max_length=120)
    query: str | None = Field(default=None, max_length=300)
    city: str | None = Field(default=None, max_length=120)
    category: str | None = Field(default=None, max_length=120)
    radius_km: float | None = Field(default=None, ge=0, le=100)
    max_price: float | None = Field(default=None, ge=0)

class ReviewCreate(BaseModel):
    reservation_code: str = Field(..., min_length=4, max_length=40)
    phone: str = Field(..., min_length=5, max_length=80)
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)

class ReferralCreate(BaseModel):
    phone: str = Field(..., min_length=5, max_length=80)


def _phone_key(phone: str) -> str:
    value = normalize_phone(phone)
    if len(value) < 5:
        raise HTTPException(status_code=400, detail="Telefon nije ispravan")
    return value

@router.post("/favorites", response_model=dict)
def add_favorite(payload: FavoriteCreate, db: Session = Depends(get_db)):
    store = db.get(models.Store, payload.store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Prodavac nije pronađen")
    phone = _phone_key(payload.phone)
    rows = read_json("customer_favorites.json", [])
    for row in rows:
        if row.get("phone") == phone and int(row.get("store_id") or 0) == payload.store_id:
            return {"ok": True, "favorite": row, "message": "Već je u omiljenima"}
    row = append_json_row("customer_favorites.json", {"phone": phone, "store_id": payload.store_id, "store_name": store.name})
    return {"ok": True, "favorite": row}

@router.get("/favorites", response_model=list[dict])
def list_favorites(phone: str, db: Session = Depends(get_db)):
    key = _phone_key(phone)
    rows = [r for r in read_json("customer_favorites.json", []) if r.get("phone") == key]
    out = []
    for row in rows:
        store = db.get(models.Store, int(row.get("store_id") or 0))
        out.append({**row, "store": {"id": store.id, "name": store.name, "city": store.city, "address": store.address} if store else None})
    return out

@router.delete("/favorites/{favorite_id}", response_model=dict)
def remove_favorite(favorite_id: str, phone: str):
    key = _phone_key(phone)
    rows = read_json("customer_favorites.json", [])
    kept = [r for r in rows if not (str(r.get("id")) == str(favorite_id) and r.get("phone") == key)]
    write_json("customer_favorites.json", kept)
    return {"ok": True, "removed": len(rows) - len(kept)}

@router.post("/saved-searches", response_model=dict)
def create_saved_search(payload: SavedSearchCreate):
    phone = _phone_key(payload.phone)
    row = append_json_row("customer_saved_searches.json", {**payload.model_dump(), "phone": phone})
    return {"ok": True, "saved_search": row}

@router.get("/saved-searches", response_model=list[dict])
def list_saved_searches(phone: str):
    key = _phone_key(phone)
    return [r for r in reversed(read_json("customer_saved_searches.json", [])) if r.get("phone") == key]

@router.post("/reviews", response_model=dict)
def create_review(payload: ReviewCreate, db: Session = Depends(get_db)):
    reservation = db.query(models.Reservation).filter(models.Reservation.reservation_code == payload.reservation_code.upper()).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena")
    if not normalize_phone(reservation.customer_phone).endswith(_phone_key(payload.phone)[-6:]):
        raise HTTPException(status_code=401, detail="Telefon se ne poklapa sa rezervacijom")
    if reservation.status != "picked_up":
        raise HTTPException(status_code=400, detail="Ocena se ostavlja posle preuzimanja")
    existing = [r for r in read_json("customer_reviews.json", []) if r.get("reservation_code") == reservation.reservation_code]
    if existing:
        return {"ok": True, "review": existing[-1], "message": "Rezervacija je već ocenjena"}
    product = reservation.product
    store = product.store if product and product.store else None
    row = append_json_row("customer_reviews.json", {
        "reservation_code": reservation.reservation_code,
        "phone": _phone_key(payload.phone),
        "rating": payload.rating,
        "comment": payload.comment,
        "product_id": product.id if product else None,
        "product_name": product.name if product else None,
        "store_id": store.id if store else None,
        "store_name": store.name if store else None,
    })
    return {"ok": True, "review": row}

@router.get("/reviews", response_model=list[dict])
def list_reviews(store_id: int | None = None, limit: int = Query(default=50, ge=1, le=500)):
    rows = list(reversed(read_json("customer_reviews.json", [])))
    if store_id:
        rows = [r for r in rows if int(r.get("store_id") or 0) == store_id]
    return rows[:limit]

@router.get("/reviews/summary", response_model=dict)
def review_summary(store_id: int | None = None):
    rows = read_json("customer_reviews.json", [])
    if store_id:
        rows = [r for r in rows if int(r.get("store_id") or 0) == store_id]
    avg = round(sum(float(r.get("rating") or 0) for r in rows) / len(rows), 2) if rows else 0
    return {"count": len(rows), "average_rating": avg}

@router.post("/referrals", response_model=dict)
def referral_code(payload: ReferralCreate):
    phone = _phone_key(payload.phone)
    rows = read_json("customer_referrals.json", [])
    existing = next((r for r in rows if r.get("phone") == phone), None)
    if existing:
        return {"ok": True, "referral": existing}
    code = "SH" + "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    row = append_json_row("customer_referrals.json", {"phone": phone, "code": code, "uses": 0, "reward_note": "MVP: nagrada se obračunava ručno u pilotu"})
    return {"ok": True, "referral": row}

@router.get("/admin/reviews", response_model=list[dict])
def admin_reviews(request: Request, limit: int = Query(default=200, ge=1, le=1000), _: bool = Depends(require_admin_session)):
    return list(reversed(read_json("customer_reviews.json", [])))[:limit]
