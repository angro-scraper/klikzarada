from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services.admin_auth import require_admin_session
from ..services.json_store import read_json, write_json, append_json_row, update_json_row
from ..services.seller_discovery import discover_sellers

router = APIRouter(prefix="/scale-api", tags=["v37-scale-suite"])
VISIBLE = {"public_discount", "seller_verified", "near_expiry"}
ACTIVE_RES = {"pending", "confirmed", "ready_for_pickup", "awaiting_payment", "paid"}

SERBIA_CITIES = [
    {"city": "Beograd", "priority": 1, "status": "active_pilot", "target_partners": 30, "categories": "pekare, restorani, marketi, poslastice", "note": "Fokus na opštine sa velikom gustinom: Vračar, Zvezdara, Novi Beograd, Zemun, Palilula."},
    {"city": "Novi Sad", "priority": 2, "status": "next", "target_partners": 20, "categories": "pekare, restorani, marketi, zdrava hrana", "note": "Dobar drugi grad zbog studentske populacije i gustih zona preuzimanja."},
    {"city": "Niš", "priority": 3, "status": "next", "target_partners": 15, "categories": "pekare, gotova jela, marketi", "note": "Pilot sa nižim cenama i velikim akcentom na dnevne ponude."},
    {"city": "Kragujevac", "priority": 4, "status": "research", "target_partners": 12, "categories": "pekare, restorani, marketi", "note": "Test za centralnu Srbiju."},
    {"city": "Subotica", "priority": 5, "status": "research", "target_partners": 10, "categories": "pekare, poslastice, restorani", "note": "Manji grad za proveru lokalnog modela."},
    {"city": "Čačak", "priority": 6, "status": "research", "target_partners": 8, "categories": "pekare, marketi, gotova jela", "note": "Dobar za ručni partnerski outreach."},
    {"city": "Kraljevo", "priority": 7, "status": "research", "target_partners": 8, "categories": "pekare, restorani", "note": "Pilot posle validacije većih gradova."},
    {"city": "Zrenjanin", "priority": 8, "status": "research", "target_partners": 8, "categories": "pekare, marketi", "note": "Vojvodina, manja konkurencija."},
]

DEFAULT_CAMPAIGNS = [
    {"name": "Pekare posle 18h", "city": "Beograd", "category": "pekara", "channel": "push_sms", "coupon_code": "PECIVO18", "discount_percent": 3, "budget_rsd": 15000, "status": "draft", "goal": "Aktivirati kupce za večernje preuzimanje pekarskih proizvoda."},
    {"name": "Prva rezervacija", "city": "Svi gradovi", "category": "sve", "channel": "app", "coupon_code": "PRVI5", "discount_percent": 5, "budget_rsd": 25000, "status": "draft", "goal": "Povećati broj prvih rezervacija za nove korisnike."},
    {"name": "Vikend gotova jela", "city": "Beograd", "category": "gotova jela", "channel": "push_sms", "coupon_code": "VIKEND3", "discount_percent": 3, "budget_rsd": 12000, "status": "draft", "goal": "Testirati potražnju za gotovim jelima vikendom."},
]

class CityUpsert(BaseModel):
    city: str
    priority: int = 10
    status: str = "research"
    target_partners: int = 10
    categories: str = "pekare, restorani, marketi"
    note: str | None = None

class CampaignCreate(BaseModel):
    name: str
    city: str = "Svi gradovi"
    category: str = "sve"
    channel: str = "app"
    coupon_code: str | None = None
    discount_percent: float = Field(default=1, ge=0, le=5)
    budget_rsd: float = Field(default=0, ge=0)
    status: str = "draft"
    goal: str | None = None

class StatusPatch(BaseModel):
    status: str
    note: str | None = None

class DemandCreate(BaseModel):
    phone: str | None = None
    city: str | None = None
    category: str | None = None
    query: str | None = None
    radius_km: float | None = None
    note: str | None = None

class LeadCreate(BaseModel):
    name: str
    city: str | None = None
    category: str | None = None
    contact: str | None = None
    source: str = "manual"
    status: str = "new"
    score: int = Field(default=50, ge=0, le=100)
    note: str | None = None

class SellerDiscoveryRequest(BaseModel):
    city: str | None = "Beograd"
    category: str | None = "pekara"
    query: str | None = None
    limit: int = Field(default=12, ge=1, le=50)
    include_existing: bool = True
    include_research_tasks: bool = True
    web_search: bool = False
    import_to_stores: bool = False
    create_sources: bool = True


def money(x: Any) -> float:
    return round(float(x or 0), 2)


def _city_rows(db: Session) -> list[dict]:
    rows = db.query(models.Store.city, func.count(models.Store.id)).group_by(models.Store.city).all()
    store_count = {city or "Nepoznato": int(count or 0) for city, count in rows}
    product_rows = db.query(models.Store.city, func.count(models.Product.id)).join(models.Product, models.Product.store_id == models.Store.id).filter(models.Product.status.in_(VISIBLE)).group_by(models.Store.city).all()
    product_count = {city or "Nepoznato": int(count or 0) for city, count in product_rows}
    res_rows = db.query(models.Store.city, func.count(models.Reservation.id)).join(models.Product, models.Reservation.product_id == models.Product.id).join(models.Store, models.Product.store_id == models.Store.id).group_by(models.Store.city).all()
    reservation_count = {city or "Nepoznato": int(count or 0) for city, count in res_rows}
    cities = sorted(set(store_count) | set(product_count) | set(reservation_count))
    return [{"city": c, "stores": store_count.get(c, 0), "offers": product_count.get(c, 0), "reservations": reservation_count.get(c, 0)} for c in cities]


@router.get("/overview", response_model=dict)
def overview(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    today = datetime.utcnow().date()
    visible = db.query(func.count(models.Product.id)).filter(models.Product.status.in_(VISIBLE)).scalar() or 0
    visible_with_image = db.query(func.count(models.Product.id)).filter(models.Product.status.in_(VISIBLE), models.Product.image_url.isnot(None), models.Product.image_url != "").scalar() or 0
    stores = db.query(func.count(models.Store.id)).scalar() or 0
    verified = db.query(func.count(models.Store.id)).filter(models.Store.verified == True).scalar() or 0
    reservations = db.query(func.count(models.Reservation.id)).scalar() or 0
    active_res = db.query(func.count(models.Reservation.id)).filter(models.Reservation.status.in_(ACTIVE_RES)).scalar() or 0
    paid_amount = db.query(func.coalesce(func.sum(models.Reservation.payable_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    fee_amount = db.query(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    campaigns = read_json("growth_campaigns.json", [])
    demand = read_json("customer_demand_requests.json", [])
    leads = read_json("growth_leads.json", [])
    return {
        "version": "V37 Growth & Scale Suite",
        "visible_offers": visible,
        "image_coverage_percent": round((visible_with_image / visible * 100), 1) if visible else 0,
        "stores_total": stores,
        "verified_stores": verified,
        "reservations_total": reservations,
        "active_reservations": active_res,
        "paid_amount": money(paid_amount),
        "platform_fee": money(fee_amount),
        "campaigns": len(campaigns),
        "active_campaigns": sum(1 for c in campaigns if c.get("status") == "active"),
        "demand_requests": len(demand),
        "leads": len(leads),
        "cities": _city_rows(db),
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.post("/cities/seed", response_model=dict)
def seed_cities(request: Request, _: bool = Depends(require_admin_session)):
    existing = read_json("city_launch_plans.json", [])
    existing_names = {str(x.get("city", "")).lower() for x in existing}
    added = 0
    for row in SERBIA_CITIES:
        if row["city"].lower() not in existing_names:
            append_json_row("city_launch_plans.json", row)
            added += 1
    return {"ok": True, "added": added, "message": f"Dodato gradova: {added}"}


@router.get("/cities", response_model=list[dict])
def list_cities(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    plans = read_json("city_launch_plans.json", [])
    metrics = {r["city"]: r for r in _city_rows(db)}
    out = []
    for row in plans:
        m = metrics.get(row.get("city"), {})
        out.append({**row, "stores_current": m.get("stores", 0), "offers_current": m.get("offers", 0), "reservations_current": m.get("reservations", 0)})
    return sorted(out, key=lambda x: int(x.get("priority") or 99))


@router.post("/cities", response_model=dict)
def create_city(payload: CityUpsert, request: Request, _: bool = Depends(require_admin_session)):
    row = append_json_row("city_launch_plans.json", payload.model_dump())
    return {"ok": True, "city": row}


@router.patch("/cities/{row_id}", response_model=dict)
def patch_city(row_id: str, payload: StatusPatch, request: Request, _: bool = Depends(require_admin_session)):
    row = update_json_row("city_launch_plans.json", row_id, {"status": payload.status, "note": payload.note})
    if not row:
        raise HTTPException(status_code=404, detail="Grad nije pronađen")
    return {"ok": True, "city": row}


@router.post("/campaigns/seed", response_model=dict)
def seed_campaigns(request: Request, _: bool = Depends(require_admin_session)):
    existing = read_json("growth_campaigns.json", [])
    codes = {str(x.get("coupon_code", "")).upper() for x in existing if x.get("coupon_code")}
    added = 0
    for row in DEFAULT_CAMPAIGNS:
        code = str(row.get("coupon_code", "")).upper()
        if code and code not in codes:
            append_json_row("growth_campaigns.json", row)
            added += 1
    return {"ok": True, "added": added, "message": f"Dodato kampanja: {added}"}


@router.post("/campaigns", response_model=dict)
def create_campaign(payload: CampaignCreate, request: Request, _: bool = Depends(require_admin_session)):
    row = append_json_row("growth_campaigns.json", payload.model_dump())
    return {"ok": True, "campaign": row}


@router.get("/campaigns", response_model=list[dict])
def list_campaigns(request: Request, _: bool = Depends(require_admin_session)):
    return list(reversed(read_json("growth_campaigns.json", [])))


@router.patch("/campaigns/{row_id}", response_model=dict)
def patch_campaign(row_id: str, payload: StatusPatch, request: Request, _: bool = Depends(require_admin_session)):
    row = update_json_row("growth_campaigns.json", row_id, {"status": payload.status, "note": payload.note})
    if not row:
        raise HTTPException(status_code=404, detail="Kampanja nije pronađena")
    return {"ok": True, "campaign": row}


@router.post("/demand", response_model=dict)
def create_demand(payload: DemandCreate):
    row = append_json_row("customer_demand_requests.json", payload.model_dump())
    return {"ok": True, "demand": row, "message": "Zahtev je sačuvan. Kada bude sličnih ponuda, korisnik može dobiti obaveštenje."}


@router.get("/demand", response_model=dict)
def demand_summary(request: Request, _: bool = Depends(require_admin_session)):
    rows = read_json("customer_demand_requests.json", [])
    city_counter = Counter((r.get("city") or "Nepoznato") for r in rows)
    cat_counter = Counter((r.get("category") or "Nepoznato") for r in rows)
    latest = list(reversed(rows))[:100]
    return {"total": len(rows), "by_city": city_counter.most_common(20), "by_category": cat_counter.most_common(20), "latest": latest}


@router.post("/leads", response_model=dict)
def create_lead(payload: LeadCreate, request: Request, _: bool = Depends(require_admin_session)):
    row = append_json_row("growth_leads.json", payload.model_dump())
    return {"ok": True, "lead": row}


@router.get("/leads", response_model=list[dict])
def list_leads(request: Request, status: str | None = None, _: bool = Depends(require_admin_session)):
    rows = list(reversed(read_json("growth_leads.json", [])))
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return rows[:500]


@router.post("/seller-discovery/search", response_model=dict)
def seller_discovery_search(payload: SellerDiscoveryRequest, request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    return discover_sellers(
        db,
        city=payload.city,
        category=payload.category,
        query=payload.query,
        limit=payload.limit,
        include_existing=payload.include_existing,
        include_research_tasks=payload.include_research_tasks,
        web_search=payload.web_search,
        import_to_stores=payload.import_to_stores,
        create_sources=payload.create_sources,
    )


@router.get("/seller-discovery/runs", response_model=list[dict])
def seller_discovery_runs(request: Request, _: bool = Depends(require_admin_session)):
    return list(reversed(read_json("seller_discovery_runs.json", [])))[:100]


@router.patch("/leads/{row_id}", response_model=dict)
def patch_lead(row_id: str, payload: StatusPatch, request: Request, _: bool = Depends(require_admin_session)):
    row = update_json_row("growth_leads.json", row_id, {"status": payload.status, "note": payload.note})
    if not row:
        raise HTTPException(status_code=404, detail="Lead nije pronađen")
    return {"ok": True, "lead": row}


@router.get("/ai/next-actions", response_model=dict)
def ai_next_actions(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    o = overview(request, db, True)
    actions = []
    if o["visible_offers"] < 50:
        actions.append({"priority": "high", "area": "Ponude", "action": "Dodati minimum 50 javnih ponuda pre šireg testiranja.", "why": "Bez dovoljno ponuda AI pretraga i kampanje neće imati efekat."})
    if o["image_coverage_percent"] < 95:
        actions.append({"priority": "high", "area": "Kvalitet", "action": "Blokirati objavu ponuda bez slike ili ubaciti obavezno slikanje kroz seller panel.", "why": "Slika je ključna za poverenje kupca."})
    if o["verified_stores"] < 10:
        actions.append({"priority": "medium", "area": "Prodavci", "action": "Kontaktirati 20 pekara/restorana i dovesti 10 verifikovanih partnera.", "why": "Pilot mora imati dovoljno lokacija blizu korisnika."})
    if o["active_campaigns"] == 0:
        actions.append({"priority": "medium", "area": "Marketing", "action": "Aktivirati kampanju za prvu rezervaciju ili pekare posle 18h.", "why": "Bez inicijalnog podsticaja korisnici sporije menjaju navike."})
    demand = read_json("customer_demand_requests.json", [])
    if len(demand) > 0:
        top_city = Counter((r.get("city") or "Nepoznato") for r in demand).most_common(1)[0]
        actions.append({"priority": "medium", "area": "Potražnja", "action": f"Dodati ponude za grad/zonu: {top_city[0]}", "why": f"Ima {top_city[1]} zahteva korisnika za obaveštenje."})
    if not actions:
        actions.append({"priority": "low", "area": "Pilot", "action": "Sistem je spreman za kontrolisanu promotivnu kampanju.", "why": "Osnovni uslovi izgledaju zadovoljeni."})
    return {"actions": actions, "overview": o}


@router.get("/seller-advice", response_model=dict)
def seller_advice(store_id: int, request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    store = db.get(models.Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Prodavac nije pronađen")
    products = db.query(models.Product).filter(models.Product.store_id == store_id).all()
    reservations = db.query(models.Reservation).join(models.Product).filter(models.Product.store_id == store_id).all()
    visible = [p for p in products if p.status in VISIBLE]
    advice = []
    if not visible:
        advice.append("Prodavac nema javne ponude. Predložiti mu 2–3 dnevne ponude sa slikom i jasnim vremenom preuzimanja.")
    no_image = [p for p in visible if not p.image_url]
    if no_image:
        advice.append(f"{len(no_image)} javnih ponuda nema sliku. Tražiti prodavcu da koristi kameru u seller panelu.")
    if len(reservations) == 0 and len(visible) > 0:
        advice.append("Ima javne ponude, ali nema rezervacija. Probati veći popust, jasniji naziv ili kampanju u okolini.")
    avg_discount = round(sum(float(p.discount_percent or 0) for p in visible) / len(visible), 1) if visible else 0
    if avg_discount < 20 and visible:
        advice.append("Prosečan popust je nizak. Za proizvode pred kraj dana testirati 25–40% popusta.")
    if not advice:
        advice.append("Prodavac izgleda dobro za pilot. Pratiti preuzimanja i ocene.")
    return {"store": {"id": store.id, "name": store.name, "city": store.city}, "visible_offers": len(visible), "reservations": len(reservations), "average_discount": avg_discount, "advice": advice}


@router.get("/seo-pages", response_model=list[dict])
def seo_pages(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    rows = _city_rows(db)
    categories = db.query(models.Product.category, func.count(models.Product.id)).filter(models.Product.status.in_(VISIBLE)).group_by(models.Product.category).all()
    cats = [c or "ponude" for c, count in categories if count]
    pages = []
    for city in rows[:20]:
        pages.append({"title": f"Hrana na popustu u {city['city']}", "url": f"/offers?city={city['city']}", "type": "city", "offers": city.get("offers", 0)})
        for cat in cats[:8]:
            pages.append({"title": f"{cat.title()} na popustu — {city['city']}", "url": f"/offers?city={city['city']}&category={cat}", "type": "city_category"})
    return pages[:200]
