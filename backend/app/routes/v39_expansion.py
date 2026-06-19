from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services.admin_auth import require_admin_session
from ..services.json_store import read_json, write_json, append_json_row, update_json_row

router = APIRouter(prefix="/expansion-api", tags=["v39-expansion-suite"])
VISIBLE = {"public_discount", "seller_verified", "near_expiry"}
ACTIVE_RES = {"pending", "confirmed", "ready_for_pickup", "awaiting_payment", "paid"}

CORPORATE_SEED = [
    {"name": "IT Office Novi Beograd", "city": "Beograd - Novi Beograd", "contact": "office@example.com", "employees": 120, "category_interest": "sendviči, gotova jela, salate", "status": "lead", "note": "Test B2B lunch bundle za firme posle 15h."},
    {"name": "Coworking Dorćol", "city": "Beograd - Dorćol", "contact": "coworking@example.com", "employees": 45, "category_interest": "pekara, poslastice, kafa", "status": "lead", "note": "Paket ponude za članove coworking prostora."},
    {"name": "Studentski dom pilot", "city": "Beograd", "contact": "studenti@example.com", "employees": 300, "category_interest": "pekara, gotova jela", "status": "research", "note": "Velika potražnja za niskim cenama uveče."},
]

DONATION_SEED = [
    {"name": "Humanitarna kuhinja — pilot", "city": "Beograd", "contact": "donacije@example.com", "pickup_window": "21-22h", "category_accepts": "hleb, pecivo, gotova jela", "status": "available", "note": "Koristiti samo za ponude koje prodavac označi za donaciju."},
    {"name": "Udruženje za pomoć porodicama", "city": "Beograd", "contact": "pomoc@example.com", "pickup_window": "20-22h", "category_accepts": "pekara, poslastice, market", "status": "available", "note": "MVP evidencija, bez automatskog transfera hrane."},
]

COURIER_SEED = [
    {"name": "Pešačka zona Vračar", "city": "Beograd - Vračar", "radius_km": 1.2, "fee_rsd": 120, "status": "draft", "coverage_note": "Test za gušće kvartove i kratke rute."},
    {"name": "Bicikl zona Novi Beograd", "city": "Beograd - Novi Beograd", "radius_km": 2.5, "fee_rsd": 180, "status": "draft", "coverage_note": "Samo za plaćene porudžbine i partner prodavce."},
    {"name": "Zemun večernja ruta", "city": "Beograd - Zemun", "radius_km": 2.0, "fee_rsd": 160, "status": "research", "coverage_note": "Moguća ruta za korpe posle 18h."},
]

AUTOMATION_SEED = [
    {"name": "Sakrij istekle ponude", "trigger": "svakih 15 min", "action": "product.status=expired/hidden", "status": "ready", "risk": "low", "note": "Sakriva ponude kojima je prošao rok preuzimanja ili datum isteka."},
    {"name": "Podsetnik 30 min pre preuzimanja", "trigger": "pickup_window - 30min", "action": "SMS/push kupcu", "status": "ready", "risk": "low", "note": "Smanjuje no-show i kašnjenje."},
    {"name": "Upozori prodavca na čekanje potvrde", "trigger": "rezervacija pending > 10 min", "action": "SMS/push prodavcu", "status": "ready", "risk": "medium", "note": "Povećava brzinu potvrde."},
    {"name": "Blokiraj objavu bez slike", "trigger": "product publish", "action": "reject if no image", "status": "ready", "risk": "low", "note": "Slika je obavezna za poverenje kupca."},
]

EXPERIMENT_SEED = [
    {"name": "PRVI5 vs PECIVO18", "goal": "povećati prvu rezervaciju", "variant_a": "PRVI5", "variant_b": "PECIVO18", "metric": "conversion_rate", "status": "draft", "note": "Meri koja kampanja bolje aktivira prve korisnike."},
    {"name": "Mapa prvo vs lista prvo", "goal": "veća interakcija sa ponudama u blizini", "variant_a": "map_first", "variant_b": "list_first", "metric": "offer_detail_clicks", "status": "draft", "note": "Korisno kada imamo dovoljan broj lokacija."},
    {"name": "Cena 25% provizija vs paket partnera", "goal": "prihvatanje prodavaca", "variant_a": "25_percent_commission", "variant_b": "monthly_partner_plan", "metric": "seller_acceptance", "status": "research", "note": "Ne menja produkcionu cenu bez odluke admina."},
]

PLAYBOOK_SEED = [
    {"title": "Pilot pekara — poziv", "type": "seller_outreach", "status": "ready", "body": "Dobar dan, pravimo aplikaciju koja pomaže pekarama da prodaju višak peciva u poslednjim satima rada. Ne tražimo stalnu obavezu — za pilot je dovoljno da testiramo 3 dana i da ponuda ima sliku, cenu i vreme preuzimanja."},
    {"title": "Kupac — objašnjenje plaćanja", "type": "customer_support", "status": "ready", "body": "Rezervaciju možete platiti online/IPS QR kada je opcija uključena. Prodavac vidi status plaćanja, a digitalna karta služi kao dokaz rezervacije."},
    {"title": "Prodavac — pravilo slike", "type": "seller_training", "status": "ready", "body": "Svaka javna ponuda mora imati realnu sliku proizvoda. Generičke slike se koriste samo za test/pilot seed, ne za stvarne ponude prodavca."},
]

class CorporateCreate(BaseModel):
    name: str
    city: str | None = None
    contact: str | None = None
    employees: int | None = None
    category_interest: str | None = None
    status: str = "lead"
    note: str | None = None

class DonationCreate(BaseModel):
    name: str
    city: str | None = None
    contact: str | None = None
    pickup_window: str | None = None
    category_accepts: str | None = None
    status: str = "available"
    note: str | None = None

class CourierZoneCreate(BaseModel):
    name: str
    city: str | None = None
    radius_km: float = Field(default=2, ge=0)
    fee_rsd: float = Field(default=0, ge=0)
    status: str = "draft"
    coverage_note: str | None = None

class SimpleStatusPatch(BaseModel):
    status: str
    note: str | None = None

class ExperimentCreate(BaseModel):
    name: str
    goal: str | None = None
    variant_a: str | None = None
    variant_b: str | None = None
    metric: str | None = None
    status: str = "draft"
    note: str | None = None

class AutomationCreate(BaseModel):
    name: str
    trigger: str | None = None
    action: str | None = None
    status: str = "draft"
    risk: str = "low"
    note: str | None = None


def money(x: Any) -> float:
    return round(float(x or 0), 2)


def _counts(db: Session) -> dict[str, Any]:
    products = db.query(func.count(models.Product.id)).scalar() or 0
    visible = db.query(func.count(models.Product.id)).filter(models.Product.status.in_(VISIBLE)).scalar() or 0
    visible_with_image = db.query(func.count(models.Product.id)).filter(models.Product.status.in_(VISIBLE), models.Product.image_url.isnot(None), models.Product.image_url != "").scalar() or 0
    stores = db.query(func.count(models.Store.id)).scalar() or 0
    verified = db.query(func.count(models.Store.id)).filter(models.Store.verified == True).scalar() or 0
    reservations = db.query(func.count(models.Reservation.id)).scalar() or 0
    active_res = db.query(func.count(models.Reservation.id)).filter(models.Reservation.status.in_(ACTIVE_RES)).scalar() or 0
    paid = db.query(func.coalesce(func.sum(models.Reservation.payable_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    fee = db.query(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    refunds = db.query(func.count(models.Reservation.id)).filter(models.Reservation.status.in_(["refunded", "cancelled_by_customer", "cancelled_by_seller"])).scalar() or 0
    return {
        "products_total": int(products),
        "visible_offers": int(visible),
        "image_coverage_percent": round((visible_with_image / visible * 100), 1) if visible else 0,
        "stores_total": int(stores),
        "verified_stores": int(verified),
        "reservations_total": int(reservations),
        "active_reservations": int(active_res),
        "paid_amount": money(paid),
        "platform_fee": money(fee),
        "refund_like_count": int(refunds),
    }


@router.get("/overview", response_model=dict)
def overview(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    c = _counts(db)
    return {
        "version": "V39 Expansion OS",
        **c,
        "corporate_clients": len(read_json("v39_corporate_clients.json", [])),
        "donation_partners": len(read_json("v39_donation_partners.json", [])),
        "courier_zones": len(read_json("v39_courier_zones.json", [])),
        "automation_rules": len(read_json("v39_automation_rules.json", [])),
        "experiments": len(read_json("v39_experiments.json", [])),
        "playbooks": len(read_json("v39_playbooks.json", [])),
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.post("/seed-all", response_model=dict)
def seed_all(request: Request, _: bool = Depends(require_admin_session)):
    seeds = [
        ("v39_corporate_clients.json", CORPORATE_SEED, "corporate_clients"),
        ("v39_donation_partners.json", DONATION_SEED, "donation_partners"),
        ("v39_courier_zones.json", COURIER_SEED, "courier_zones"),
        ("v39_automation_rules.json", AUTOMATION_SEED, "automation_rules"),
        ("v39_experiments.json", EXPERIMENT_SEED, "experiments"),
        ("v39_playbooks.json", PLAYBOOK_SEED, "playbooks"),
    ]
    added: dict[str, int] = {}
    for filename, rows, key in seeds:
        existing = read_json(filename, [])
        names = {str(x.get("name") or x.get("title") or "").lower() for x in existing}
        count = 0
        for row in rows:
            marker = str(row.get("name") or row.get("title") or "").lower()
            if marker not in names:
                append_json_row(filename, row)
                count += 1
        added[key] = count
    return {"ok": True, "added": added, "message": "V39 komplet podataka je učitan."}


@router.get("/corporate-clients", response_model=list[dict])
def corporate_clients(request: Request, _: bool = Depends(require_admin_session)):
    return read_json("v39_corporate_clients.json", [])

@router.post("/corporate-clients", response_model=dict)
def add_corporate(payload: CorporateCreate, request: Request, _: bool = Depends(require_admin_session)):
    return {"ok": True, "row": append_json_row("v39_corporate_clients.json", payload.model_dump())}

@router.patch("/corporate-clients/{row_id}", response_model=dict)
def patch_corporate(row_id: str, payload: SimpleStatusPatch, request: Request, _: bool = Depends(require_admin_session)):
    row = update_json_row("v39_corporate_clients.json", row_id, payload.model_dump(exclude_none=True))
    if not row:
        raise HTTPException(status_code=404, detail="Corporate client not found")
    return {"ok": True, "row": row}

@router.get("/donation-partners", response_model=list[dict])
def donation_partners(request: Request, _: bool = Depends(require_admin_session)):
    return read_json("v39_donation_partners.json", [])

@router.post("/donation-partners", response_model=dict)
def add_donation(payload: DonationCreate, request: Request, _: bool = Depends(require_admin_session)):
    return {"ok": True, "row": append_json_row("v39_donation_partners.json", payload.model_dump())}

@router.patch("/donation-partners/{row_id}", response_model=dict)
def patch_donation(row_id: str, payload: SimpleStatusPatch, request: Request, _: bool = Depends(require_admin_session)):
    row = update_json_row("v39_donation_partners.json", row_id, payload.model_dump(exclude_none=True))
    if not row:
        raise HTTPException(status_code=404, detail="Donation partner not found")
    return {"ok": True, "row": row}

@router.get("/courier-zones", response_model=list[dict])
def courier_zones(request: Request, _: bool = Depends(require_admin_session)):
    return read_json("v39_courier_zones.json", [])

@router.post("/courier-zones", response_model=dict)
def add_courier(payload: CourierZoneCreate, request: Request, _: bool = Depends(require_admin_session)):
    return {"ok": True, "row": append_json_row("v39_courier_zones.json", payload.model_dump())}

@router.patch("/courier-zones/{row_id}", response_model=dict)
def patch_courier(row_id: str, payload: SimpleStatusPatch, request: Request, _: bool = Depends(require_admin_session)):
    row = update_json_row("v39_courier_zones.json", row_id, payload.model_dump(exclude_none=True))
    if not row:
        raise HTTPException(status_code=404, detail="Courier zone not found")
    return {"ok": True, "row": row}

@router.get("/automation-rules", response_model=list[dict])
def automation_rules(request: Request, _: bool = Depends(require_admin_session)):
    return read_json("v39_automation_rules.json", [])

@router.post("/automation-rules", response_model=dict)
def add_automation(payload: AutomationCreate, request: Request, _: bool = Depends(require_admin_session)):
    return {"ok": True, "row": append_json_row("v39_automation_rules.json", payload.model_dump())}

@router.patch("/automation-rules/{row_id}", response_model=dict)
def patch_automation(row_id: str, payload: SimpleStatusPatch, request: Request, _: bool = Depends(require_admin_session)):
    row = update_json_row("v39_automation_rules.json", row_id, payload.model_dump(exclude_none=True))
    if not row:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    return {"ok": True, "row": row}

@router.get("/experiments", response_model=list[dict])
def experiments(request: Request, _: bool = Depends(require_admin_session)):
    return read_json("v39_experiments.json", [])

@router.post("/experiments", response_model=dict)
def add_experiment(payload: ExperimentCreate, request: Request, _: bool = Depends(require_admin_session)):
    return {"ok": True, "row": append_json_row("v39_experiments.json", payload.model_dump())}

@router.patch("/experiments/{row_id}", response_model=dict)
def patch_experiment(row_id: str, payload: SimpleStatusPatch, request: Request, _: bool = Depends(require_admin_session)):
    row = update_json_row("v39_experiments.json", row_id, payload.model_dump(exclude_none=True))
    if not row:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"ok": True, "row": row}

@router.get("/playbooks", response_model=list[dict])
def playbooks(request: Request, _: bool = Depends(require_admin_session)):
    return read_json("v39_playbooks.json", [])


@router.get("/risk-audit", response_model=dict)
def risk_audit(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    no_image = db.query(func.count(models.Product.id)).filter(models.Product.status.in_(VISIBLE), ((models.Product.image_url.is_(None)) | (models.Product.image_url == ""))).scalar() or 0
    low_conf = db.query(func.count(models.Product.id)).filter(models.Product.confidence_score < 0.55).scalar() or 0
    unpaid_paid_status = db.query(func.count(models.Reservation.id)).filter(models.Reservation.status.in_(["paid", "ready_for_pickup", "picked_up"]), models.Reservation.payment_status != "paid").scalar() or 0
    no_show = db.query(func.count(models.Reservation.id)).filter(models.Reservation.status == "no_show").scalar() or 0
    refunds = db.query(func.count(models.Reservation.id)).filter(models.Reservation.status.in_(["refunded", "cancelled_by_customer", "cancelled_by_seller"])).scalar() or 0
    recommendations = []
    if no_image:
        recommendations.append("Blokirati ili sakriti javne ponude bez slike pre šireg testiranja.")
    if low_conf:
        recommendations.append("Pregledati kandidate niskog confidence score-a i ostaviti ih samo za internu bazu.")
    if unpaid_paid_status:
        recommendations.append("Proveriti rezervacije koje imaju status preuzimanja, ali nisu označene kao plaćene.")
    if no_show > 3:
        recommendations.append("Aktivirati no-show pravilo i podsetnik 30 minuta pre preuzimanja.")
    if refunds > 5:
        recommendations.append("Analizirati razloge refund/reklamacija po prodavcu.")
    if not recommendations:
        recommendations.append("Nema kritičnih signala. Nastaviti ručni pilot i pratiti nove rezervacije.")
    return {
        "no_image_visible_offers": int(no_image),
        "low_confidence_products": int(low_conf),
        "payment_status_mismatch": int(unpaid_paid_status),
        "no_show_count": int(no_show),
        "refund_like_count": int(refunds),
        "recommendations": recommendations,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/route-plan", response_model=dict)
def route_plan(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    stores = db.query(models.Store).filter(models.Store.latitude.isnot(None), models.Store.longitude.isnot(None)).limit(30).all()
    by_city: dict[str, list[dict]] = defaultdict(list)
    for s in stores:
        offers = db.query(func.count(models.Product.id)).filter(models.Product.store_id == s.id, models.Product.status.in_(VISIBLE)).scalar() or 0
        if offers:
            by_city[s.city or "Nepoznato"].append({"store_id": s.id, "name": s.name, "address": s.address, "offers": int(offers), "lat": s.latitude, "lng": s.longitude})
    routes = []
    for city, items in by_city.items():
        if len(items) >= 2:
            routes.append({"city": city, "stops": items[:8], "note": "Pilot ruta: proveriti ručno redosled po mapi pre stvarnog dostavljača."})
    return {"routes": routes, "stores_with_geo_and_offers": sum(len(x) for x in by_city.values())}


@router.get("/board-memo", response_model=dict)
def board_memo(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    c = _counts(db)
    campaigns = read_json("growth_campaigns.json", [])
    leads = read_json("growth_leads.json", [])
    corporate = read_json("v39_corporate_clients.json", [])
    experiments = read_json("v39_experiments.json", [])
    risks = risk_audit(request, db, True)
    memo = [
        "V39 izvršni rezime za pilot:",
        f"Javne ponude: {c['visible_offers']} ({c['image_coverage_percent']}% sa slikom).",
        f"Prodavci: {c['verified_stores']} verifikovanih od ukupno {c['stores_total']}.",
        f"Rezervacije: {c['reservations_total']} ukupno, {c['active_reservations']} aktivnih.",
        f"Plaćen promet: {c['paid_amount']} RSD, provizija platforme: {c['platform_fee']} RSD.",
        f"Growth: {len(campaigns)} kampanja, {len(leads)} leadova, {len(corporate)} B2B/corporate leadova.",
        f"Eksperimenti: {len(experiments)} pripremljeno.",
        "Top rizici: " + "; ".join(risks.get("recommendations", [])[:3]),
        "Sledeći fokus: 10 verifikovanih partnera, 50+ realnih ponuda sa slikama i merenje prve rezervacije po kampanji.",
    ]
    return {"memo": "\n".join(memo), "metrics": c, "generated_at": datetime.utcnow().isoformat()}


@router.get("/ai-expansion-plan", response_model=dict)
def ai_expansion_plan(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    c = _counts(db)
    actions = []
    if c["visible_offers"] < 50:
        actions.append({"area": "Ponude", "priority": "high", "action": "Prvo održati 50+ javnih ponuda sa slikama svakog dana.", "why": "Bez ponuda nema konverzije, AI pretraga nema šta da preporuči."})
    if c["verified_stores"] < 10:
        actions.append({"area": "Partneri", "priority": "high", "action": "Zaključati 10 verifikovanih partnera u Beogradu pre otvaranja novih gradova.", "why": "Gustina ponude je važnija od širokog, praznog pokrivanja."})
    if c["image_coverage_percent"] < 95:
        actions.append({"area": "Kvalitet", "priority": "medium", "action": "Uključiti hard rule: javna ponuda ne može bez slike.", "why": "Slika direktno utiče na poverenje kupca."})
    actions.append({"area": "Novi kanal", "priority": "medium", "action": "Testirati B2B lunch bundle sa 2 firme i jednim coworking prostorom.", "why": "B2B narudžbine mogu popuniti potražnju pre nego što consumer marketing proradi."})
    actions.append({"area": "Donacije", "priority": "low", "action": "Pripremiti donacioni tok za neprodate ponude posle kraja pickup prozora.", "why": "Daje društvenu vrednost i bolji PR, ali ne sme ometati core prodaju."})
    actions.append({"area": "Automatizacija", "priority": "medium", "action": "Aktivirati podsetnike za kupca i prodavca pre preuzimanja.", "why": "Smanjuje no-show i podršku."})
    return {"actions": actions, "generated_at": datetime.utcnow().isoformat()}
