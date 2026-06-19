from __future__ import annotations

from datetime import date, datetime, timedelta
from random import Random
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services.admin_auth import require_admin_session
from ..services.json_store import read_json, write_json, append_json_row, update_json_row

router = APIRouter(prefix="/launch-api", tags=["v38-launch-execution-suite"])
VISIBLE_STATUSES = {"public_discount", "seller_verified", "near_expiry"}
ACTIVE_RESERVATION_STATUSES = {"pending", "confirmed", "awaiting_payment", "paid", "ready_for_pickup"}

PRODUCT_LIBRARY = [
    {"name": "Korpa peciva mix", "category": "pekara", "old": 580, "new": 349, "qty": 8, "pickup": "danas 18-21h", "image": "/admin-assets/seed-images/pecivo-mix.svg"},
    {"name": "Burek sa sirom 1/4", "category": "pekara", "old": 240, "new": 159, "qty": 12, "pickup": "danas 17-20h", "image": "/admin-assets/seed-images/burek-sir.svg"},
    {"name": "Kroasan puter", "category": "pekara", "old": 190, "new": 119, "qty": 10, "pickup": "danas 18-21h", "image": "/admin-assets/seed-images/kroasan.svg"},
    {"name": "Integralni hleb 500g", "category": "pekara", "old": 210, "new": 139, "qty": 7, "pickup": "danas 16-19h", "image": "/admin-assets/seed-images/hleb-integralni.svg"},
    {"name": "Kiflice sa sirom 6 kom", "category": "pekara", "old": 420, "new": 269, "qty": 9, "pickup": "danas 18-21h", "image": "/admin-assets/seed-images/kiflice.svg"},
    {"name": "Pita sa jabukama", "category": "poslastice", "old": 260, "new": 169, "qty": 6, "pickup": "danas 18-20h", "image": "/admin-assets/seed-images/pita-jabuka.svg"},
    {"name": "Sendvič šunka sir", "category": "sendviči", "old": 390, "new": 249, "qty": 8, "pickup": "danas 15-18h", "image": "/admin-assets/seed-images/sendvic.svg"},
    {"name": "Dnevni meni porcija", "category": "gotova jela", "old": 690, "new": 449, "qty": 5, "pickup": "danas 16-19h", "image": "/admin-assets/seed-images/dnevni-meni.svg"},
    {"name": "Salata obrok", "category": "salate", "old": 520, "new": 349, "qty": 4, "pickup": "danas 15-18h", "image": "/admin-assets/seed-images/salata.svg"},
    {"name": "Kolač dana", "category": "poslastice", "old": 320, "new": 199, "qty": 10, "pickup": "danas 18-21h", "image": "/admin-assets/seed-images/kolac.svg"},
]

PILOT_STORES = [
    {"name": "Pilot Pekara Vračar", "city": "Beograd - Vračar", "address": "Bulevar kralja Aleksandra 122", "lat": 44.8034, "lng": 20.4759, "phone": "0600001001", "kind": "pekara"},
    {"name": "Pilot Pekara Dorćol", "city": "Beograd - Dorćol", "address": "Cara Dušana 45", "lat": 44.8232, "lng": 20.4589, "phone": "0600001002", "kind": "pekara"},
    {"name": "Pilot Pekara Zemun", "city": "Beograd - Zemun", "address": "Glavna 18", "lat": 44.8457, "lng": 20.4111, "phone": "0600001003", "kind": "pekara"},
    {"name": "Pilot Pekara Novi Beograd", "city": "Beograd - Novi Beograd", "address": "Bulevar Zorana Đinđića 64", "lat": 44.8176, "lng": 20.4251, "phone": "0600001004", "kind": "pekara"},
    {"name": "Pilot Pekara Banovo brdo", "city": "Beograd - Banovo brdo", "address": "Požeška 88", "lat": 44.7782, "lng": 20.4195, "phone": "0600001005", "kind": "pekara"},
    {"name": "Pilot Restoran Dnevni meni", "city": "Beograd - Palilula", "address": "Cvijićeva 37", "lat": 44.8153, "lng": 20.4832, "phone": "0600001006", "kind": "restoran"},
    {"name": "Pilot Poslastičarnica Centar", "city": "Beograd - Stari grad", "address": "Knez Mihailova 12", "lat": 44.8172, "lng": 20.4569, "phone": "0600001007", "kind": "poslastice"},
    {"name": "Pilot Market Zvezdara", "city": "Beograd - Zvezdara", "address": "Dimitrija Tucovića 101", "lat": 44.7979, "lng": 20.5002, "phone": "0600001008", "kind": "market"},
]

LAUNCH_TASKS = [
    {"area": "Ponude", "title": "Dodati 50 javnih ponuda", "priority": "high", "status": "todo", "owner": "admin", "due_in_days": 3, "note": "Bez dovoljno ponuda AI pretraga i kampanje nemaju efekat."},
    {"area": "Kvalitet", "title": "Blokirati ponude bez slike", "priority": "high", "status": "todo", "owner": "product", "due_in_days": 1, "note": "Javna ponuda mora imati sliku, cenu, količinu i vreme preuzimanja."},
    {"area": "Prodavci", "title": "Kontaktirati 20 pekara/restorana", "priority": "medium", "status": "todo", "owner": "sales", "due_in_days": 7, "note": "Cilj je minimum 10 verifikovanih partnera za pilot."},
    {"area": "Marketing", "title": "Aktivirati kampanju za prvu rezervaciju", "priority": "medium", "status": "todo", "owner": "growth", "due_in_days": 5, "note": "Testirati PRVI5 i PECIVO18 kupon."},
    {"area": "Operacije", "title": "Pripremiti pilot checklistu", "priority": "medium", "status": "todo", "owner": "ops", "due_in_days": 2, "note": "Proveriti rezervacije, plaćanje, QR, refund, SMS i seller PIN."},
]

OUTREACH_LEADS = [
    {"name": "Pekara Vračar 1", "city": "Beograd - Vračar", "category": "pekara", "contact": "Instagram / telefon", "score": 82},
    {"name": "Pekara Zvezdara 1", "city": "Beograd - Zvezdara", "category": "pekara", "contact": "Google Maps", "score": 78},
    {"name": "Pekara Dorćol 1", "city": "Beograd - Stari grad", "category": "pekara", "contact": "telefon", "score": 75},
    {"name": "Pekara Novi Beograd 1", "city": "Beograd - Novi Beograd", "category": "pekara", "contact": "Instagram", "score": 80},
    {"name": "Pekara Zemun 1", "city": "Beograd - Zemun", "category": "pekara", "contact": "telefon", "score": 76},
    {"name": "Restoran dnevni meni 1", "city": "Beograd - Palilula", "category": "restoran", "contact": "telefon", "score": 70},
    {"name": "Poslastičarnica centar 1", "city": "Beograd - Stari grad", "category": "poslastice", "contact": "Instagram", "score": 72},
    {"name": "Market lokalni 1", "city": "Beograd - Zvezdara", "category": "market", "contact": "telefon", "score": 65},
]

class TaskPatch(BaseModel):
    status: str | None = None
    owner: str | None = None
    note: str | None = None

class LeadPatch(BaseModel):
    status: str | None = None
    note: str | None = None
    score: int | None = Field(default=None, ge=0, le=100)


def pct(old: float, new: float) -> float:
    return round(max(0, (old - new) / old * 100), 1) if old else 0


def money(x: Any) -> float:
    return round(float(x or 0), 2)


def _visible_query(db: Session):
    return db.query(models.Product).filter(models.Product.status.in_(VISIBLE_STATUSES))


def _metric_snapshot(db: Session) -> dict:
    visible = _visible_query(db).count()
    with_image = _visible_query(db).filter(models.Product.image_url.isnot(None), models.Product.image_url != "").count()
    stores_total = db.query(models.Store).count()
    verified = db.query(models.Store).filter(models.Store.verified == True).count()
    pending_res = db.query(models.Reservation).filter(models.Reservation.status.in_(ACTIVE_RESERVATION_STATUSES)).count()
    paid = db.query(func.coalesce(func.sum(models.Reservation.payable_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    fee = db.query(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    tasks = read_json("launch_tasks.json", [])
    leads = read_json("launch_outreach_leads.json", [])
    return {
        "visible_offers": visible,
        "offers_with_image": with_image,
        "image_coverage_percent": round((with_image / visible * 100), 1) if visible else 0,
        "stores_total": stores_total,
        "verified_stores": verified,
        "active_reservations": pending_res,
        "paid_amount": money(paid),
        "platform_fee": money(fee),
        "tasks_total": len(tasks),
        "tasks_done": sum(1 for t in tasks if t.get("status") == "done"),
        "leads_total": len(leads),
        "leads_contacted": sum(1 for l in leads if l.get("status") in {"contacted", "meeting", "approved", "won"}),
        "generated_at": datetime.utcnow().isoformat(),
    }


def _readiness(snapshot: dict) -> list[dict]:
    checks = []
    def add(name, ok, current, target, note):
        checks.append({"name": name, "ok": bool(ok), "current": current, "target": target, "note": note})
    add("Minimum 50 javnih ponuda", snapshot["visible_offers"] >= 50, snapshot["visible_offers"], 50, "Seeduj demo ponude ili unesi stvarne ponude iz seller panela.")
    add("Slike na javnim ponudama", snapshot["image_coverage_percent"] >= 95, f"{snapshot['image_coverage_percent']}%", "95%", "Ponude bez slike treba sakriti ili dopuniti slikom.")
    add("Minimum 10 verifikovanih partnera", snapshot["verified_stores"] >= 10, snapshot["verified_stores"], 10, "Pre pilota kontaktirati i odobriti partnere.")
    add("Outreach pipeline", snapshot["leads_total"] >= 20, snapshot["leads_total"], 20, "Dodati bar 20 leadova za prve pozive.")
    add("Operativni taskovi", snapshot["tasks_done"] >= 3, snapshot["tasks_done"], 3, "Zatvoriti najvažnije pilot taskove pre javnog testa.")
    return checks


@router.get("/overview", response_model=dict)
def overview(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    snapshot = _metric_snapshot(db)
    checks = _readiness(snapshot)
    ready = all(c["ok"] for c in checks[:3])
    return {"version": "V38 Launch Execution Suite", "ready_for_private_pilot": ready, "metrics": snapshot, "checks": checks}


@router.post("/seed/tasks", response_model=dict)
def seed_tasks(request: Request, _: bool = Depends(require_admin_session)):
    existing = read_json("launch_tasks.json", [])
    titles = {str(x.get("title", "")).lower() for x in existing}
    added = 0
    for row in LAUNCH_TASKS:
        if row["title"].lower() not in titles:
            payload = dict(row)
            payload["due_date"] = (date.today() + timedelta(days=int(row.get("due_in_days", 3)))).isoformat()
            payload.pop("due_in_days", None)
            append_json_row("launch_tasks.json", payload)
            added += 1
    return {"ok": True, "added": added}


@router.get("/tasks", response_model=list[dict])
def list_tasks(request: Request, _: bool = Depends(require_admin_session)):
    return list(reversed(read_json("launch_tasks.json", [])))


@router.patch("/tasks/{task_id}", response_model=dict)
def patch_task(task_id: str, payload: TaskPatch, request: Request, _: bool = Depends(require_admin_session)):
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    row = update_json_row("launch_tasks.json", task_id, patch)
    if not row:
        return {"ok": False, "error": "Task nije pronađen"}
    return {"ok": True, "task": row}


@router.post("/seed/outreach", response_model=dict)
def seed_outreach(request: Request, count: int = Query(default=20, ge=1, le=100), _: bool = Depends(require_admin_session)):
    existing = read_json("launch_outreach_leads.json", [])
    names = {str(x.get("name", "")).lower() for x in existing}
    added = 0
    base = OUTREACH_LEADS
    for idx in range(count):
        template = dict(base[idx % len(base)])
        n = idx + 1
        if idx >= len(base):
            template["name"] = f"{template['category'].title()} lead BG {n}"
            template["score"] = max(45, int(template.get("score", 60)) - (idx % 12))
        template.setdefault("source", "launch_seed")
        template.setdefault("status", "new")
        template.setdefault("note", "Kontaktirati za pilot: bez troška ulaska, brzo slikanje ponuda, isplata po obračunu.")
        if template["name"].lower() not in names:
            append_json_row("launch_outreach_leads.json", template)
            added += 1
    return {"ok": True, "added": added}


@router.get("/outreach", response_model=list[dict])
def list_outreach(request: Request, _: bool = Depends(require_admin_session)):
    return list(reversed(read_json("launch_outreach_leads.json", [])))


@router.patch("/outreach/{lead_id}", response_model=dict)
def patch_lead(lead_id: str, payload: LeadPatch, request: Request, _: bool = Depends(require_admin_session)):
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    row = update_json_row("launch_outreach_leads.json", lead_id, patch)
    if not row:
        return {"ok": False, "error": "Lead nije pronađen"}
    return {"ok": True, "lead": row}


@router.get("/outreach/templates", response_model=dict)
def outreach_templates(request: Request, _: bool = Depends(require_admin_session)):
    return {
        "phone_script": "Dobar dan, zovem u vezi platforme koja pomaže pekarama i restoranima da prodaju višak hrane pred kraj dana umesto da se baca. U pilotu je unos ponude preko telefona za manje od 30 sekundi, kupac rezerviše i preuzima kod vas. Da li možemo da vam pokažemo probu bez obaveze?",
        "sms_short": "Zdravo! Pokrećemo lokalnu aplikaciju za prodaju viška hrane po sniženoj ceni. Unos ponude traje 30 sekundi, kupac preuzima kod vas. Da li ste zainteresovani za pilot?",
        "instagram_dm": "Pozdrav! Radimo pilot aplikacije koja pomaže pekarama da prodaju višak peciva/hleba pred kraj dana. Prodavac samo slika ponudu, unese cenu i vreme preuzimanja. Da li možemo da vam pošaljemo kratak demo?",
        "objection_fee": "Provizija se računa samo na uspešno plaćene/preuzete rezervacije. U pilotu pratimo rezultat i podešavamo model da bude isplativ prodavcu.",
        "objection_time": "Prodavac ne mora da unosi veliki katalog. Dovoljno je jedna slika, naziv, cena, količina i vreme preuzimanja. Ideja je da unos traje ispod 30 sekundi.",
    }


@router.post("/seed/public-offers", response_model=dict)
def seed_public_offers(request: Request, db: Session = Depends(get_db), count: int = Query(default=50, ge=1, le=200), _: bool = Depends(require_admin_session)):
    rng = Random(38)
    created_stores = 0
    created_products = 0
    stores = []
    for item in PILOT_STORES:
        store = db.query(models.Store).filter(models.Store.name == item["name"]).first()
        if not store:
            store = models.Store(
                name=item["name"], city=item["city"], address=item["address"], latitude=item["lat"], longitude=item["lng"],
                phone=item["phone"], verified=True, website="https://example.com/pilot"
            )
            db.add(store)
            db.flush()
            created_stores += 1
        stores.append(store)
    db.commit()

    existing_keys = set()
    for p in db.query(models.Product.name, models.Product.store_id).all():
        existing_keys.add((p.name.lower(), p.store_id))

    i = 0
    attempts = 0
    while created_products < count and attempts < count * 5:
        attempts += 1
        store = stores[i % len(stores)]
        base = dict(PRODUCT_LIBRARY[(i + rng.randint(0, 7)) % len(PRODUCT_LIBRARY)])
        variant = (i // len(PRODUCT_LIBRARY)) + 1
        name = base["name"] if variant == 1 else f"{base['name']} — paket {variant}"
        key = (name.lower(), store.id)
        i += 1
        if key in existing_keys:
            continue
        old_price = float(base["old"] + rng.choice([0, 10, 20, 30]))
        new_price = float(base["new"] + rng.choice([0, 5, 10, 15]))
        product = models.Product(
            store_id=store.id,
            name=name,
            category=base["category"],
            original_price=old_price,
            discounted_price=new_price,
            discount_percent=pct(old_price, new_price),
            currency="RSD",
            expiry_date=date.today() + timedelta(days=rng.choice([0, 1, 1, 2])),
            expiry_type="best_before",
            quantity=int(base["qty"] + rng.randint(0, 5)),
            pickup_window=base["pickup"],
            image_url=base["image"],
            source_url="launch_seed",
            confidence_score=0.92,
            status="seller_verified",
        )
        db.add(product)
        existing_keys.add(key)
        created_products += 1
    db.commit()
    return {"ok": True, "created_stores": created_stores, "created_products": created_products, "message": "Dodate su pilot ponude sa slikama. Zameniti ih stvarnim ponudama pre javne produkcije."}


@router.post("/quality/enforce-images", response_model=dict)
def enforce_images(request: Request, db: Session = Depends(get_db), dry_run: bool = Query(default=True), _: bool = Depends(require_admin_session)):
    bad = _visible_query(db).filter((models.Product.image_url.is_(None)) | (models.Product.image_url == "")).all()
    rows = [{"id": p.id, "name": p.name, "status": p.status, "store_id": p.store_id} for p in bad]
    if not dry_run:
        for p in bad:
            p.status = "hidden"
        db.commit()
    return {"ok": True, "dry_run": dry_run, "affected": len(bad), "products": rows[:200], "message": "Dry-run prikazuje šta bi bilo sakriveno. Sa dry_run=false ponude bez slike idu u hidden."}


@router.post("/campaigns/activate-first", response_model=dict)
def activate_first_campaign(request: Request, _: bool = Depends(require_admin_session)):
    rows = read_json("growth_campaigns.json", [])
    target_codes = {"PRVI5", "PECIVO18"}
    updated = 0
    for row in rows:
        if str(row.get("coupon_code", "")).upper() in target_codes:
            row["status"] = "active"
            row["note"] = "Aktivirano iz V38 Launch centra"
            updated += 1
    if updated == 0:
        rows.extend([
            {"name": "Prva rezervacija", "city": "Svi gradovi", "category": "sve", "channel": "app", "coupon_code": "PRVI5", "discount_percent": 5, "budget_rsd": 25000, "status": "active", "goal": "Povećati broj prvih rezervacija."},
            {"name": "Pekare posle 18h", "city": "Beograd", "category": "pekara", "channel": "push_sms", "coupon_code": "PECIVO18", "discount_percent": 3, "budget_rsd": 15000, "status": "active", "goal": "Aktivirati večernje preuzimanje peciva."},
        ])
        updated = 2
    write_json("growth_campaigns.json", rows)
    return {"ok": True, "activated": updated}


@router.get("/pilot-report", response_model=dict)
def pilot_report(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    snap = _metric_snapshot(db)
    checks = _readiness(snap)
    actions = []
    for c in checks:
        if not c["ok"]:
            actions.append({"priority": "high" if c["name"] in {"Minimum 50 javnih ponuda", "Slike na javnim ponudama"} else "medium", "action": c["note"], "metric": c["name"]})
    return {"summary": snap, "checks": checks, "next_actions": actions, "generated_at": datetime.utcnow().isoformat()}
