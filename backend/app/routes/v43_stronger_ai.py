from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services.admin_auth import require_admin_session
from ..services.json_store import append_json_row, read_json, write_json, utc_now

router = APIRouter(prefix="/v43-api", tags=["v43-stronger-ai"])

LIVE_STATUSES = {"seller_verified", "near_expiry", "public_discount"}
CATALOG_STATUSES = {"real_catalog_reference", "candidate", "public_discount"}

TARGET_SELLERS: list[dict[str, Any]] = [
    {"name": "Skroz dobra pekara - pilot kontakt", "city": "Beograd", "category": "pekara", "priority": 98, "reason": "lanac sa više lokacija i velikim dnevnim prometom peciva", "channel": "telefon + poseta objekta", "offer_angle": "večernje korpe peciva posle 18h"},
    {"name": "Pekara Kirćanski - Novi Beograd", "city": "Beograd", "category": "pekara", "priority": 94, "reason": "javna kataloška ponuda i dobar fit za korpe", "channel": "direktan obilazak", "offer_angle": "burek/peciva pred kraj dana"},
    {"name": "Pekara na Bulevaru", "city": "Beograd", "category": "pekara", "priority": 91, "reason": "vidljivi proizvodi i cene u javnim katalozima", "channel": "telefon + WhatsApp", "offer_angle": "pita, hleb i slatkiši pred zatvaranje"},
    {"name": "Baba Višnjine kiflice", "city": "Beograd", "category": "pekara", "priority": 88, "reason": "standardizovan proizvod i dobra fotografija proizvoda", "channel": "email + poziv", "offer_angle": "paketi kiflica za preuzimanje istog dana"},
    {"name": "Lokalne pekare Vračar", "city": "Beograd", "category": "pekara", "priority": 85, "reason": "gusta zona kupaca i pešačko preuzimanje", "channel": "terenski obilazak", "offer_angle": "dnevni višak od 17h do 20h"},
    {"name": "Lokalne pekare Novi Beograd", "city": "Beograd", "category": "pekara", "priority": 84, "reason": "velika naselja, dobra potražnja za blizinom", "channel": "terenski obilazak", "offer_angle": "korpe peciva za porodice"},
    {"name": "Lokalni restorani dnevni meni", "city": "Beograd", "category": "gotova jela", "priority": 80, "reason": "dnevni meni često ima višak posle ručka", "channel": "poziv u 15h", "offer_angle": "gotova jela pre kraja dana"},
    {"name": "Poslastičarnice u centru", "city": "Beograd", "category": "poslastice", "priority": 78, "reason": "slike su bitne i proizvodi su vizuelno atraktivni", "channel": "Instagram + poseta", "offer_angle": "kolači/kroasani pred zatvaranje"},
]

PRODUCT_MISSION_TEMPLATES: list[dict[str, Any]] = [
    {"category": "pekara", "title": "Korpa peciva pred zatvaranje", "min_photo_count": 1, "required_fields": ["slika", "cena", "količina", "vreme preuzimanja"], "suggested_discount": "30-50%", "pickup_window": "18-21h"},
    {"category": "pekara", "title": "Burek / pita na komad", "min_photo_count": 1, "required_fields": ["slika", "vrsta", "gramaža", "cena", "količina"], "suggested_discount": "20-40%", "pickup_window": "posle 17h"},
    {"category": "gotova jela", "title": "Dnevni meni pred kraj smene", "min_photo_count": 1, "required_fields": ["slika", "opis", "porcija", "alergeni", "vreme preuzimanja"], "suggested_discount": "25-45%", "pickup_window": "15-18h"},
    {"category": "poslastice", "title": "Kolači / kroasani istog dana", "min_photo_count": 1, "required_fields": ["slika", "naziv", "komada", "cena", "rok"], "suggested_discount": "20-35%", "pickup_window": "18-21h"},
    {"category": "market", "title": "Artikli kraćeg roka", "min_photo_count": 2, "required_fields": ["slika proizvoda", "slika deklaracije", "cena", "rok", "količina"], "suggested_discount": "25-60%", "pickup_window": "danas/sutra"},
]

AI_PLAYBOOKS: list[dict[str, Any]] = [
    {"name": "AI kupac - nema rezultata", "goal": "pretvori praznu pretragu u zahtev za obaveštenje", "script": "Trenutno nema ponuda za taj filter. Mogu da sačuvam tvoju pretragu i predložim najbliže slične ponude."},
    {"name": "AI prodavac - brzo objavljivanje", "goal": "smanji unos ponude na 15 sekundi", "script": "Slikaj proizvod, reci cenu i količinu. Ja ću popuniti naziv, kategoriju, popust i vreme preuzimanja."},
    {"name": "AI admin - realna baza", "goal": "razdvoji katalog od live ponude", "script": "Kataloški proizvod nije live ponuda dok prodavac ne potvrdi količinu, rok i vreme preuzimanja."},
    {"name": "AI support - plaćanje", "goal": "jasno objasni online plaćanje i QR", "script": "Plaćanje može ići kroz aplikaciju/QR kada je omogućeno. Ako nije potvrđeno, proveru vrši admin preko finansijskog pregleda."},
    {"name": "AI quality gate", "goal": "blokiraj slabe ponude", "script": "Za javnu objavu tražim sliku, cenu, količinu, prodavca, vreme preuzimanja i status roka."},
]

QUALITY_GATES: list[dict[str, Any]] = [
    {"gate": "Slika obavezna", "rule": "Javna ponuda ne sme bez image_url ili upload slike", "severity": "critical", "auto_action": "hide_or_block"},
    {"gate": "Cena obavezna", "rule": "discounted_price ili original_price mora biti > 0", "severity": "critical", "auto_action": "needs_review"},
    {"gate": "Rok istine", "rule": "near_expiry samo ako prodavac potvrdi expiry_date ili expiry_type", "severity": "critical", "auto_action": "downgrade_to_seller_verified"},
    {"gate": "Količina", "rule": "quantity mora biti veći od 0 za rezervaciju", "severity": "high", "auto_action": "pause_offer"},
    {"gate": "Preuzimanje", "rule": "pickup_window mora postojati kod live ponude", "severity": "medium", "auto_action": "needs_review"},
    {"gate": "Ekstreman popust", "rule": "popust preko 80% traži admin proveru", "severity": "medium", "auto_action": "flag"},
]

OUTREACH_SCRIPTS = {
    "phone_short": "Dobar dan, pravimo lokalnu aplikaciju koja pomaže pekarama da prodaju višak peciva pred kraj dana umesto da se baca. Prvih 30 dana pilot je bez mesečne naknade. Treba samo da slikate ponudu i unesete cenu/količinu. Da li možemo da vam otvorimo test nalog?",
    "whatsapp": "Zdravo, Sačuvaj Hranu pomaže lokalnim pekarama da prodaju dnevni višak hrane uz popust. Kupci rezervišu, vi vidite kod i preuzimanje. Prvih 30 dana pilot bez obaveze. Mogu da vam pošaljem seller link i PIN za test?",
    "email": "Poštovani, pokrećemo pilot platformu za prodaju dnevnog viška hrane i proizvoda kraćeg roka u Srbiji. Cilj je manje bacanja hrane i dodatna zarada za lokalne prodavce. U pilotu dobijate seller panel, rezervacije, QR proveru i AI brzo dodavanje ponuda. Predlažemo kratko testiranje sa 3-5 ponuda dnevno.",
    "visit_checklist": "1) pitati kada ostaje višak, 2) slikati 2 probne ponude, 3) dogovoriti pickup window, 4) objasniti rezervacioni kod, 5) uzeti kontakt vlasnika/menadžera, 6) proveriti da li prihvata online plaćanje ili plaćanje u lokalu.",
}

class LeadCreate(BaseModel):
    name: str
    city: str = "Beograd"
    category: str = "pekara"
    phone: str | None = None
    website: str | None = None
    priority: int = 70
    note: str | None = None

class MissionCreate(BaseModel):
    store_id: int | None = None
    store_name: str | None = None
    category: str = "pekara"
    title: str = "Terenska provera proizvoda"
    due_days: int = 3


def _metrics(db: Session) -> dict[str, Any]:
    stores = db.query(models.Store).all()
    products = db.query(models.Product).all()
    reservations = db.query(models.Reservation).all()
    live_products = [p for p in products if p.status in LIVE_STATUSES]
    catalog_products = [p for p in products if p.status in CATALOG_STATUSES]
    with_image = [p for p in products if p.image_url]
    with_price = [p for p in products if (p.discounted_price or p.original_price or 0) > 0]
    verified_stores = [s for s in stores if s.verified]
    paid_reservations = [r for r in reservations if r.payment_status == "paid"]
    return {
        "stores": len(stores),
        "verified_stores": len(verified_stores),
        "products": len(products),
        "live_products": len(live_products),
        "catalog_products": len(catalog_products),
        "products_with_image": len(with_image),
        "products_with_price": len(with_price),
        "reservations": len(reservations),
        "paid_reservations": len(paid_reservations),
        "image_rate": round((len(with_image) / len(products) * 100), 1) if products else 0,
        "price_rate": round((len(with_price) / len(products) * 100), 1) if products else 0,
        "status_breakdown": dict(Counter([p.status for p in products])),
        "category_breakdown": dict(Counter([(p.category or "unknown") for p in products])),
        "city_breakdown": dict(Counter([(s.city or "unknown") for s in stores])),
    }


def _read_all() -> dict[str, Any]:
    return {
        "leads": read_json("v43_seller_leads.json", []),
        "missions": read_json("v43_capture_missions.json", []),
        "ai_playbooks": read_json("v43_ai_playbooks.json", []),
        "quality_gates": read_json("v43_quality_gates.json", []),
        "autopilot_actions": read_json("v43_autopilot_actions.json", []),
        "weekly_plan": read_json("v43_weekly_plan.json", {}),
        "scripts": read_json("v43_outreach_scripts.json", OUTREACH_SCRIPTS),
    }


@router.get("/overview")
def overview(db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    data = _read_all()
    metrics = _metrics(db)
    readiness = 0
    readiness += min(metrics["verified_stores"], 10) * 5
    readiness += min(metrics["live_products"], 50) * 0.6
    readiness += 10 if metrics["image_rate"] >= 80 else metrics["image_rate"] * 0.1
    readiness += 10 if metrics["price_rate"] >= 95 else metrics["price_rate"] * 0.05
    readiness += min(metrics["reservations"], 20) * 0.5
    return {"metrics": metrics, "readiness_score": min(round(readiness, 1), 100), **data}


@router.post("/load-suite")
def load_suite(db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    write_json("v43_ai_playbooks.json", AI_PLAYBOOKS)
    write_json("v43_quality_gates.json", QUALITY_GATES)
    write_json("v43_outreach_scripts.json", OUTREACH_SCRIPTS)
    existing = read_json("v43_seller_leads.json", [])
    seen = {str(x.get("name", "")).lower() for x in existing}
    added = 0
    for item in TARGET_SELLERS:
        if item["name"].lower() not in seen:
            row = dict(item)
            row.update({"status": "new", "owner": "founder", "created_at": utc_now(), "updated_at": utc_now()})
            existing.append(row)
            added += 1
    write_json("v43_seller_leads.json", existing)
    return {"ok": True, "message": "V43 paket učitan", "leads_added": added, "metrics": _metrics(db)}


@router.post("/add-lead")
def add_lead(payload: LeadCreate, _: bool = Depends(require_admin_session)):
    row = payload.model_dump()
    row.update({"status": "new", "owner": "founder", "created_at": utc_now(), "updated_at": utc_now()})
    return append_json_row("v43_seller_leads.json", row)


@router.post("/generate-contact-plan")
def generate_contact_plan(db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    leads = read_json("v43_seller_leads.json", [])
    stores = db.query(models.Store).all()
    by_name = {str(x.get("name", "")).lower(): x for x in leads}
    for store in stores:
        key = store.name.lower()
        if key not in by_name:
            leads.append({
                "name": store.name,
                "city": store.city or "Beograd",
                "category": "pekara" if "pek" in store.name.lower() else "food",
                "priority": 65 + (15 if store.website else 0) + (10 if store.verified else 0),
                "reason": "postojeći prodavac/lead iz baze aplikacije",
                "channel": "telefon + seller link",
                "offer_angle": "brzo dodavanje ponuda kamerom",
                "status": "verified" if store.verified else "new",
                "store_id": store.id,
                "seller_link": f"/seller?store_id={store.id}",
                "created_at": utc_now(),
                "updated_at": utc_now(),
            })
    leads = sorted(leads, key=lambda x: int(x.get("priority", 0)), reverse=True)
    write_json("v43_seller_leads.json", leads)
    tasks = []
    for idx, lead in enumerate(leads[:30], start=1):
        tasks.append({
            "id": f"contact-{idx:03d}",
            "title": f"Kontaktirati: {lead.get('name')}",
            "priority": lead.get("priority", 70),
            "status": "todo",
            "due_at": (datetime.utcnow() + timedelta(days=idx // 5)).date().isoformat(),
            "script": OUTREACH_SCRIPTS["phone_short"],
            "channel": lead.get("channel", "telefon"),
            "goal": "dobiti potvrdu za 3 probne live ponude sa slikom",
        })
    write_json("v43_contact_tasks.json", tasks)
    return {"ok": True, "leads": len(leads), "tasks": len(tasks), "tasks_preview": tasks[:5]}


@router.post("/generate-capture-missions")
def generate_capture_missions(db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    stores = db.query(models.Store).order_by(models.Store.created_at.desc()).limit(60).all()
    missions = []
    for store in stores:
        for template in PRODUCT_MISSION_TEMPLATES[:2 if "pek" in store.name.lower() else 1]:
            missions.append({
                "id": f"mission-{store.id}-{len(missions)+1}",
                "store_id": store.id,
                "store_name": store.name,
                "city": store.city or "Beograd",
                "title": template["title"],
                "category": template["category"],
                "status": "todo",
                "required_fields": template["required_fields"],
                "min_photo_count": template["min_photo_count"],
                "suggested_discount": template["suggested_discount"],
                "pickup_window": template["pickup_window"],
                "deadline": (datetime.utcnow() + timedelta(days=3)).date().isoformat(),
                "ai_instruction": "Prodavac treba da slika stvaran proizvod tog dana. Katalog nije dovoljan za live ponudu.",
            })
    if not missions:
        for idx, target in enumerate(TARGET_SELLERS, start=1):
            t = PRODUCT_MISSION_TEMPLATES[0]
            missions.append({
                "id": f"mission-lead-{idx}", "store_id": None, "store_name": target["name"], "city": target["city"],
                "title": t["title"], "category": t["category"], "status": "todo", "required_fields": t["required_fields"],
                "min_photo_count": t["min_photo_count"], "suggested_discount": t["suggested_discount"], "pickup_window": t["pickup_window"],
                "deadline": (datetime.utcnow() + timedelta(days=3)).date().isoformat(),
                "ai_instruction": "Otvoriti partnera i odmah uhvatiti 3 realne ponude kamerom.",
            })
    write_json("v43_capture_missions.json", missions)
    return {"ok": True, "missions": len(missions), "preview": missions[:6]}


@router.post("/ai-autopilot")
def ai_autopilot(db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    products = db.query(models.Product).all()
    stores = {s.id: s for s in db.query(models.Store).all()}
    actions: list[dict[str, Any]] = []
    now = datetime.utcnow().date()
    for p in products:
        issues = []
        if p.status in LIVE_STATUSES and not p.image_url:
            issues.append("nema sliku")
        if p.status in LIVE_STATUSES and not ((p.discounted_price or 0) > 0 or (p.original_price or 0) > 0):
            issues.append("nema cenu")
        if p.status == "near_expiry" and not p.expiry_date:
            issues.append("near_expiry bez datuma roka")
        if p.quantity is not None and p.quantity <= 0 and p.status in LIVE_STATUSES:
            issues.append("nema dostupnu količinu")
        if p.expiry_date and p.expiry_date < now and p.status in LIVE_STATUSES:
            issues.append("istekao rok")
        if p.discount_percent and p.discount_percent > 80:
            issues.append("ekstreman popust")
        if issues:
            store = stores.get(p.store_id) if p.store_id else None
            actions.append({
                "product_id": p.id,
                "product": p.name,
                "store": store.name if store else "Nepoznat prodavac",
                "status": p.status,
                "issues": issues,
                "recommended_action": "sakriti/proveriti" if any(x in issues for x in ["nema sliku", "istekao rok", "near_expiry bez datuma roka"]) else "ručna provera",
                "severity": "critical" if any(x in issues for x in ["nema sliku", "istekao rok", "near_expiry bez datuma roka"]) else "medium",
                "created_at": utc_now(),
            })
    write_json("v43_autopilot_actions.json", actions)
    return {"ok": True, "actions": len(actions), "critical": len([a for a in actions if a["severity"] == "critical"]), "preview": actions[:10]}


@router.post("/safe-apply-quality")
def safe_apply_quality(db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    hidden = 0
    reviewed = 0
    today = datetime.utcnow().date()
    for p in db.query(models.Product).all():
        if p.status in LIVE_STATUSES and not p.image_url:
            p.status = "hidden"
            hidden += 1
        elif p.status == "near_expiry" and not p.expiry_date:
            p.status = "seller_verified"
            reviewed += 1
        elif p.expiry_date and p.expiry_date < today and p.status in LIVE_STATUSES:
            p.status = "expired"
            hidden += 1
    db.commit()
    return {"ok": True, "hidden_or_expired": hidden, "downgraded_to_seller_verified": reviewed}


@router.post("/weekly-plan")
def weekly_plan(db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    metrics = _metrics(db)
    plan = {
        "generated_at": utc_now(),
        "north_star": "10 verifikovanih partnera, 50 live ponuda sa slikom, 100 rezervacija u pilot zoni",
        "week_focus": [],
        "daily_actions": [],
        "blocked_by": [],
    }
    if metrics["verified_stores"] < 10:
        plan["week_focus"].append("Partneri: dovesti još verifikovanih prodavaca")
        plan["blocked_by"].append("malo verifikovanih prodavaca")
    if metrics["live_products"] < 50:
        plan["week_focus"].append("Ponude: prikupiti realne ponude kamerom")
        plan["blocked_by"].append("nedovoljno live ponuda")
    if metrics["image_rate"] < 90:
        plan["week_focus"].append("Kvalitet: blokirati ponude bez slike")
        plan["blocked_by"].append("slab image coverage")
    plan["daily_actions"] = [
        {"day": "Ponedeljak", "actions": ["kontakt 10 leadova", "otvoriti 3 seller naloga", "uhvatiti 10 ponuda sa slikom"]},
        {"day": "Utorak", "actions": ["terenski obilazak 5 lokacija", "testirati rezervaciju i QR", "AI audit baze"]},
        {"day": "Sreda", "actions": ["aktivirati PRVI5 kampanju", "pozvati kupce iz čekanja", "proveriti finance settlement"]},
        {"day": "Četvrtak", "actions": ["seller trening", "dodati 15 ponuda", "sakriti slabe ponude"]},
        {"day": "Petak", "actions": ["pilot report", "identifikovati top 5 prodavaca", "pripremiti vikend kampanju"]},
    ]
    write_json("v43_weekly_plan.json", plan)
    return plan


@router.get("/export-pack")
def export_pack(_: bool = Depends(require_admin_session)):
    return _read_all()
