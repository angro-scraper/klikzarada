from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services.admin_auth import require_admin_session
from ..services.json_store import read_json, write_json, append_json_row, update_json_row

router = APIRouter(prefix="/v40-api", tags=["v40-market-ops-suite"])

VISIBLE_STATUSES = {"public_discount", "seller_verified", "near_expiry"}
ACTIVE_ORDER_STATUSES = {"pending", "awaiting_payment", "paid", "confirmed", "ready_for_pickup"}
FINAL_BAD_STATUSES = {"cancelled_by_customer", "cancelled_by_seller", "refunded", "expired", "no_show"}

CITY_LAUNCH_PACKS = [
    {"city": "Beograd", "priority": 1, "target_verified_sellers": 30, "target_public_offers": 250, "pilot_areas": "Vračar, Dorćol, Novi Beograd, Zemun, Zvezdara", "categories": "pekare, restorani, marketi, poslastice", "status": "active_pilot", "note": "Prvi grad; fokus na gustim zonama i večernim ponudama."},
    {"city": "Novi Sad", "priority": 2, "target_verified_sellers": 20, "target_public_offers": 150, "pilot_areas": "Centar, Liman, Grbavica, Detelinara", "categories": "pekare, gotova jela, poslastice", "status": "next_city", "note": "Dobar grad za studentsku publiku i lokalne pekare."},
    {"city": "Niš", "priority": 3, "target_verified_sellers": 15, "target_public_offers": 100, "pilot_areas": "Centar, Bulevar Nemanjića, Palilula", "categories": "pekare, restorani, marketi", "status": "research", "note": "Niži CAC, dobar za proveru modela van Beograda."},
    {"city": "Kragujevac", "priority": 4, "target_verified_sellers": 12, "target_public_offers": 80, "pilot_areas": "Centar, Aerodrom", "categories": "pekare, marketi", "status": "research", "note": "Test manji grad / drugačije navike kupovine."},
    {"city": "Subotica", "priority": 5, "target_verified_sellers": 10, "target_public_offers": 70, "pilot_areas": "Centar, Prozivka", "categories": "pekare, poslastice", "status": "research", "note": "Pogodno za lokalne radionice i turizam."},
]

MERCHANT_PLANS = [
    {"name": "Pilot Free", "monthly_fee_rsd": 0, "commission_percent": 25, "included_offers": "neograničeno u pilotu", "best_for": "prve pekare i restorani", "status": "active", "note": "Bez fiksnog troška, provizija samo na uspešne plaćene/preuzete rezervacije."},
    {"name": "Partner", "monthly_fee_rsd": 4900, "commission_percent": 18, "included_offers": "neograničeno", "best_for": "stabilni prodavci sa dnevnim viškom", "status": "draft", "note": "Niža provizija uz mesečnu pretplatu."},
    {"name": "Chain", "monthly_fee_rsd": 19900, "commission_percent": 12, "included_offers": "više objekata", "best_for": "lanci pekara/marketa", "status": "draft", "note": "Više lokacija, izveštaji, import i podrška."},
    {"name": "Donation Partner", "monthly_fee_rsd": 0, "commission_percent": 0, "included_offers": "donacije", "best_for": "humanitarni partneri", "status": "draft", "note": "Neprofitni tok za višak koji se ne proda."},
]

CONTRACT_CLAUSES = [
    {"title": "Tačnost podataka", "type": "seller_rule", "required": True, "body": "Prodavac potvrđuje da su naziv, cena, količina, slika, vreme preuzimanja i rok tačni u trenutku objave ponude."},
    {"title": "Bezbednost hrane", "type": "seller_rule", "required": True, "body": "Prodavac potvrđuje da hrana nije istekla, da je pravilno čuvana i da je bezbedna za preuzimanje u navedenom vremenu."},
    {"title": "Slika proizvoda", "type": "quality_rule", "required": True, "body": "Javna ponuda mora imati realnu fotografiju proizvoda ili jasno obeleženu pilot sliku. Za produkciju se preporučuje realna fotografija."},
    {"title": "Provizija platforme", "type": "commercial_rule", "required": True, "body": "Platforma obračunava proviziju na uspešno plaćene/preuzete rezervacije prema trenutno aktivnom planu prodavca."},
    {"title": "Otkazivanje i refund", "type": "support_rule", "required": True, "body": "Ako prodavac ne može da isporuči rezervisanu ponudu, mora otkazati rezervaciju i navesti razlog radi refund/reklamacionog procesa."},
]

NOTIFICATION_JOURNEYS = [
    {"name": "Kupac — nova rezervacija", "audience": "customer", "trigger": "reservation_created", "channels": "in-app, SMS", "message": "Rezervacija {code} je kreirana. Preuzimanje: {pickup_window}. Plaćanje je dostupno preko QR-a ako je uključeno."},
    {"name": "Kupac — podsetnik", "audience": "customer", "trigger": "30_min_before_pickup", "channels": "SMS", "message": "Podsetnik: ponuda {product} čeka na preuzimanje. Pokažite digitalnu kartu prodavcu."},
    {"name": "Prodavac — nova rezervacija", "audience": "seller", "trigger": "reservation_created", "channels": "seller_panel, SMS", "message": "Nova rezervacija {code}. Potvrdite ili otkažite što pre."},
    {"name": "Admin — problem", "audience": "admin", "trigger": "support_ticket_high_priority", "channels": "ops_panel", "message": "Nova hitna prijava problema vezana za rezervaciju {code}."},
    {"name": "Kupac — nova ponuda u blizini", "audience": "customer", "trigger": "saved_search_match", "channels": "push/SMS later", "message": "Pojavila se nova ponuda u vašoj blizini: {product}, {price} RSD."},
]

CONTENT_CALENDAR = [
    {"day": 1, "channel": "Instagram/TikTok", "topic": "Pekare posle 18h", "hook": "Šta se dešava sa pecivom koje ostane pred zatvaranje?", "cta": "Rezerviši korpu večeras"},
    {"day": 2, "channel": "Google Business / SEO", "topic": "Hrana na popustu Beograd", "hook": "Mapa lokalnih ponuda na popustu", "cta": "Pogledaj ponude u blizini"},
    {"day": 3, "channel": "SMS/referral", "topic": "Prva rezervacija", "hook": "Dobijaš 5% na prvu rezervaciju", "cta": "Iskoristi PRVI5"},
    {"day": 4, "channel": "LinkedIn/B2B", "topic": "Manje bacanja hrane u firmama", "hook": "Office lunch bundle od lokalnih partnera", "cta": "Prijavi firmu za pilot"},
    {"day": 5, "channel": "Prodavac outreach", "topic": "Brz unos ponuda", "hook": "Jedna slika i 30 sekundi za novu prodaju", "cta": "Postani partner"},
]

RISK_RULES = [
    {"name": "Ponuda bez slike", "severity": "high", "rule": "visible_offer_without_image", "action": "sakriti ili tražiti sliku", "status": "ready"},
    {"name": "Previše otkazivanja prodavca", "severity": "high", "rule": "seller_cancel_rate_gt_15", "action": "kontaktirati prodavca / privremeno limitirati ponude", "status": "draft"},
    {"name": "No-show kupac", "severity": "medium", "rule": "customer_no_show_gt_3", "action": "smanjiti prioritet / tražiti plaćanje unapred", "status": "draft"},
    {"name": "Sumnjivo niska cena", "severity": "medium", "rule": "discount_gt_85_percent", "action": "admin review", "status": "ready"},
    {"name": "Istekao rok", "severity": "critical", "rule": "expiry_date_lt_today", "action": "automatski sakriti", "status": "ready"},
]

DATA_PIPELINES = [
    {"name": "Excel master import", "source": "Excel", "frequency": "ručno", "owner": "admin", "status": "ready", "note": "Masovni import prodavaca i artikala."},
    {"name": "Seller camera quick-add", "source": "seller panel", "frequency": "uživo", "owner": "prodavac", "status": "ready", "note": "Najpouzdaniji izvor realnih ponuda."},
    {"name": "Crawler discovery", "source": "web", "frequency": "povremeno", "owner": "ops", "status": "limited", "note": "Koristi se za leadove i akcije, ne za potvrđen rok."},
    {"name": "Finance reconciliation", "source": "bank/provider", "frequency": "dnevno", "owner": "finance", "status": "manual_mvp", "note": "Ručna potvrda IPS QR uplata dok nema webhook-a."},
]

OKR_SEED = [
    {"objective": "Pokrenuti Beograd pilot", "key_result": "10 verifikovanih prodavaca", "target": 10, "current": 0, "owner": "ops", "status": "active"},
    {"objective": "Likvidnost ponuda", "key_result": "250 javnih ponuda sa slikom", "target": 250, "current": 0, "owner": "supply", "status": "active"},
    {"objective": "Prve rezervacije", "key_result": "100 uspešnih preuzimanja", "target": 100, "current": 0, "owner": "growth", "status": "active"},
    {"objective": "Poverenje", "key_result": "<5% reklamacija", "target": 5, "current": 0, "owner": "support", "status": "active"},
    {"objective": "Finansije", "key_result": "Tačan dnevni obračun isplata", "target": 1, "current": 0, "owner": "finance", "status": "active"},
]

class RowPatch(BaseModel):
    status: str | None = None
    owner: str | None = None
    note: str | None = None
    current: float | None = None

class GenericRow(BaseModel):
    name: str
    status: str = "draft"
    note: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


def money(value: Any) -> float:
    return round(float(value or 0), 2)


def _db_metrics(db: Session) -> dict[str, Any]:
    products_total = db.query(func.count(models.Product.id)).scalar() or 0
    visible_q = db.query(models.Product).filter(models.Product.status.in_(VISIBLE_STATUSES))
    visible = visible_q.count()
    with_image = visible_q.filter(models.Product.image_url.isnot(None), models.Product.image_url != "").count()
    without_image = max(0, visible - with_image)
    stores_total = db.query(func.count(models.Store.id)).scalar() or 0
    verified = db.query(func.count(models.Store.id)).filter(models.Store.verified == True).scalar() or 0
    reservations_total = db.query(func.count(models.Reservation.id)).scalar() or 0
    active_orders = db.query(func.count(models.Reservation.id)).filter(models.Reservation.status.in_(ACTIVE_ORDER_STATUSES)).scalar() or 0
    cancelled_like = db.query(func.count(models.Reservation.id)).filter(models.Reservation.status.in_(FINAL_BAD_STATUSES)).scalar() or 0
    paid_count = db.query(func.count(models.Reservation.id)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    paid_sum = db.query(func.coalesce(func.sum(models.Reservation.payable_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    platform_fee = db.query(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    seller_net = db.query(func.coalesce(func.sum(models.Reservation.seller_net_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    # Conservative MVP estimate: one saved reservation = 0.35kg food saved, 0.875kg CO2e avoided.
    picked_up = db.query(func.count(models.Reservation.id)).filter(models.Reservation.status == "picked_up").scalar() or 0
    kg_saved = round(float(picked_up or 0) * 0.35, 2)
    co2_saved = round(kg_saved * 2.5, 2)
    cities = Counter()
    cats = Counter()
    for city, category in db.query(models.Store.city, models.Product.category).join(models.Product, models.Product.store_id == models.Store.id).filter(models.Product.status.in_(VISIBLE_STATUSES)).all():
        if city:
            cities[str(city)] += 1
        if category:
            cats[str(category)] += 1
    return {
        "products_total": int(products_total),
        "visible_offers": int(visible),
        "offers_with_image": int(with_image),
        "offers_without_image": int(without_image),
        "image_coverage_percent": round(with_image / visible * 100, 1) if visible else 0,
        "stores_total": int(stores_total),
        "verified_stores": int(verified),
        "reservations_total": int(reservations_total),
        "active_orders": int(active_orders),
        "cancelled_like": int(cancelled_like),
        "paid_count": int(paid_count),
        "paid_amount": money(paid_sum),
        "platform_fee": money(platform_fee),
        "seller_net": money(seller_net),
        "estimated_kg_saved": kg_saved,
        "estimated_co2e_saved": co2_saved,
        "top_cities": cities.most_common(8),
        "top_categories": cats.most_common(8),
        "generated_at": datetime.utcnow().isoformat(),
    }


def _readiness(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    def add(name: str, ok: bool, current: Any, target: Any, area: str, fix: str):
        checks.append({"name": name, "ok": bool(ok), "current": current, "target": target, "area": area, "fix": fix})
    add("Javne ponude", metrics["visible_offers"] >= 250, metrics["visible_offers"], 250, "Supply", "Dodati/aktivirati ponude kroz seller panel, Excel import ili launch seed.")
    add("Pokriće slikama", metrics["image_coverage_percent"] >= 95, f"{metrics['image_coverage_percent']}%", "95%", "Trust", "Sakriti ponude bez slike ili tražiti sliku od prodavca.")
    add("Verifikovani prodavci", metrics["verified_stores"] >= 10, metrics["verified_stores"], 10, "Supply", "Kontaktirati leadove i odobriti prodavce.")
    add("Plaćanja", metrics["paid_count"] >= 10, metrics["paid_count"], 10, "Finance", "Testirati IPS QR / checkout tok sa pilot ponudama.")
    add("Preuzimanja", metrics["estimated_kg_saved"] >= 5, f"{metrics['estimated_kg_saved']}kg", "5kg", "Impact", "Zatvoriti rezervacije kao preuzete posle testova.")
    return checks


@router.get("/overview", response_model=dict)
def overview(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    metrics = _db_metrics(db)
    checks = _readiness(metrics)
    data_counts = {
        "city_launch_packs": len(read_json("v40_city_launch_packs.json", [])),
        "merchant_plans": len(read_json("v40_merchant_plans.json", [])),
        "contract_clauses": len(read_json("v40_contract_clauses.json", [])),
        "notification_journeys": len(read_json("v40_notification_journeys.json", [])),
        "content_items": len(read_json("v40_content_calendar.json", [])),
        "risk_rules": len(read_json("v40_risk_rules.json", [])),
        "data_pipelines": len(read_json("v40_data_pipelines.json", [])),
        "okrs": len(read_json("v40_okrs.json", [])),
    }
    return {
        "version": "V40 Market Operations Suite",
        "pilot_ready": all(c["ok"] for c in checks[:3]),
        "metrics": metrics,
        "checks": checks,
        "data_counts": data_counts,
    }


@router.post("/seed/all", response_model=dict)
def seed_all(request: Request, _: bool = Depends(require_admin_session)):
    bundles = {
        "v40_city_launch_packs.json": CITY_LAUNCH_PACKS,
        "v40_merchant_plans.json": MERCHANT_PLANS,
        "v40_contract_clauses.json": CONTRACT_CLAUSES,
        "v40_notification_journeys.json": NOTIFICATION_JOURNEYS,
        "v40_content_calendar.json": CONTENT_CALENDAR,
        "v40_risk_rules.json": RISK_RULES,
        "v40_data_pipelines.json": DATA_PIPELINES,
        "v40_okrs.json": OKR_SEED,
    }
    result: dict[str, int] = {}
    for filename, rows in bundles.items():
        existing = read_json(filename, [])
        key_field = "name"
        if filename == "v40_city_launch_packs.json":
            key_field = "city"
        if filename == "v40_contract_clauses.json":
            key_field = "title"
        if filename == "v40_content_calendar.json":
            key_field = "topic"
        if filename == "v40_okrs.json":
            key_field = "key_result"
        existing_keys = {str(r.get(key_field, "")).lower() for r in existing if isinstance(r, dict)}
        added = 0
        for row in rows:
            if str(row.get(key_field, "")).lower() not in existing_keys:
                append_json_row(filename, row)
                added += 1
        result[filename] = added
    return {"ok": True, "added": result}


def _read_named(name: str) -> list[dict[str, Any]]:
    rows = read_json(name, [])
    return rows if isinstance(rows, list) else []


@router.get("/city-launch", response_model=list[dict])
def city_launch(request: Request, _: bool = Depends(require_admin_session)):
    return _read_named("v40_city_launch_packs.json")


@router.get("/merchant-plans", response_model=list[dict])
def merchant_plans(request: Request, _: bool = Depends(require_admin_session)):
    return _read_named("v40_merchant_plans.json")


@router.get("/contracts", response_model=list[dict])
def contracts(request: Request, _: bool = Depends(require_admin_session)):
    return _read_named("v40_contract_clauses.json")


@router.get("/notification-journeys", response_model=list[dict])
def notification_journeys(request: Request, _: bool = Depends(require_admin_session)):
    return _read_named("v40_notification_journeys.json")


@router.get("/content-calendar", response_model=list[dict])
def content_calendar(request: Request, _: bool = Depends(require_admin_session)):
    return _read_named("v40_content_calendar.json")


@router.get("/risk-rules", response_model=list[dict])
def risk_rules(request: Request, _: bool = Depends(require_admin_session)):
    return _read_named("v40_risk_rules.json")


@router.get("/data-pipelines", response_model=list[dict])
def data_pipelines(request: Request, _: bool = Depends(require_admin_session)):
    return _read_named("v40_data_pipelines.json")


@router.get("/okrs", response_model=list[dict])
def okrs(request: Request, _: bool = Depends(require_admin_session)):
    return _read_named("v40_okrs.json")


@router.patch("/okrs/{row_id}", response_model=dict)
def patch_okr(row_id: str, payload: RowPatch, request: Request, _: bool = Depends(require_admin_session)):
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    row = update_json_row("v40_okrs.json", row_id, patch)
    return {"ok": bool(row), "row": row}


@router.get("/ai-board", response_model=dict)
def ai_board(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    metrics = _db_metrics(db)
    checks = _readiness(metrics)
    priorities = []
    if metrics["visible_offers"] < 250:
        priorities.append({"priority": "Supply", "action": "Povećati javne ponude do 250", "why": "Bez likvidnosti ponuda AI pretraga, kampanje i plaćanje nemaju dovoljno efekta.", "next_step": "Uključiti 10 prodavaca i tražiti 5 dnevnih ponuda po prodavcu."})
    if metrics["image_coverage_percent"] < 95:
        priorities.append({"priority": "Trust", "action": "Blokirati ponude bez slike", "why": "Slika direktno utiče na rezervacije i smanjuje reklamacije.", "next_step": "Seller panel: obavezna kamera/foto pre objave."})
    if metrics["verified_stores"] < 10:
        priorities.append({"priority": "Partners", "action": "Zatvoriti 10 partnera", "why": "Pilot mora imati dovoljnu pokrivenost lokacija u blizini korisnika.", "next_step": "Koristiti /launch outreach skripte i CRM leadove."})
    if metrics["paid_count"] == 0:
        priorities.append({"priority": "Payments", "action": "Završiti end-to-end payment test", "why": "Provizija i finansije ne mogu se proveriti bez plaćenih rezervacija.", "next_step": "Testirati checkout, QR i ručnu potvrdu u /finance."})
    priorities.append({"priority": "Scale", "action": "Pripremiti Novi Sad kao drugi grad", "why": "Kada Beograd pilot pređe 250 ponuda, drugi grad potvrđuje ponovljivost modela.", "next_step": "Seed city launch pack i 20 leadova za Novi Sad."})
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "one_sentence_strategy": "Prvo povećati realne ponude sa slikama i verifikovane prodavce, zatim skalirati kroz gradove, B2B i donacije.",
        "metrics": metrics,
        "readiness_checks": checks,
        "priorities": priorities,
        "90_day_plan": [
            {"phase": "0-14 dana", "focus": "Beograd likvidnost", "targets": "10 partnera, 250 ponuda, 95% slika"},
            {"phase": "15-45 dana", "focus": "Plaćanje i poverenje", "targets": "100 preuzimanja, <5% reklamacija, dnevni obračun isplata"},
            {"phase": "46-90 dana", "focus": "Širenje", "targets": "Novi Sad pilot, B2B 3 firme, donacije 2 partnera"},
        ],
    }


@router.post("/quality/enforce-no-image", response_model=dict)
def enforce_no_image(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    rows = db.query(models.Product).filter(models.Product.status.in_(VISIBLE_STATUSES)).filter((models.Product.image_url.is_(None)) | (models.Product.image_url == "")).all()
    count = 0
    for product in rows:
        product.status = "hidden"
        product.updated_at = datetime.utcnow()
        count += 1
    db.commit()
    return {"ok": True, "hidden": count, "message": "Javne ponude bez slike su sakrivene."}


@router.get("/investor-snapshot", response_model=dict)
def investor_snapshot(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    metrics = _db_metrics(db)
    return {
        "title": "Sačuvaj Hranu — MVP snapshot",
        "date": date.today().isoformat(),
        "traction": {
            "visible_offers": metrics["visible_offers"],
            "verified_stores": metrics["verified_stores"],
            "reservations_total": metrics["reservations_total"],
            "paid_amount_rsd": metrics["paid_amount"],
            "platform_fee_rsd": metrics["platform_fee"],
        },
        "impact": {
            "estimated_kg_saved": metrics["estimated_kg_saved"],
            "estimated_co2e_saved": metrics["estimated_co2e_saved"],
            "model_note": "MVP procena: 0.35kg po preuzetoj rezervaciji i 2.5kg CO2e po kg hrane.",
        },
        "business_model": "25% provizija u MVP-u, plus nacrt Partner/Chain planova za kasnije smanjenje provizije uz pretplatu.",
        "next_milestones": ["250 ponuda sa slikama", "10 verifikovanih prodavaca", "100 uspešnih preuzimanja", "Novi Sad kao drugi grad"],
    }
