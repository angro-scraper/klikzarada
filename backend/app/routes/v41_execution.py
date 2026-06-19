from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services.admin_auth import require_admin_session
from ..services.json_store import read_json, write_json, append_json_row, update_json_row, utc_now

router = APIRouter(prefix="/v41-api", tags=["v41-execution-engine"])

VISIBLE_STATUSES = {"public_discount", "seller_verified", "near_expiry"}
ACTIVE_ORDER_STATUSES = {"pending", "awaiting_payment", "paid", "confirmed", "confirmed_by_seller", "ready_for_pickup"}
DONE_STATUSES = {"picked_up"}
BAD_ORDER_STATUSES = {"cancelled_by_customer", "cancelled_by_seller", "refunded", "expired", "no_show"}

EXECUTION_TASKS = [
    {"title": "Zaključati pravilo: javna ponuda mora imati sliku", "lane": "Trust", "owner": "ops", "priority": "high", "status": "open", "due_days": 1, "playbook": "quality_gate", "note": "Bez slike nema poverenja kupca. U produkciji ne objavljivati ponude bez realne slike."},
    {"title": "Kontaktirati 20 prodavaca iz lead CRM-a", "lane": "Supply", "owner": "sales", "priority": "high", "status": "open", "due_days": 2, "playbook": "seller_outreach", "note": "Cilj: 10 verifikovanih prodavaca za Beograd pilot."},
    {"title": "Ubaciti 250 pilot ponuda sa slikama", "lane": "Supply", "owner": "supply", "priority": "high", "status": "open", "due_days": 4, "playbook": "offer_liquidity", "note": "Kombinacija seller kamera, Excel import i pilot seed."},
    {"title": "Testirati checkout + IPS QR + ručnu potvrdu uplate", "lane": "Finance", "owner": "finance", "priority": "high", "status": "open", "due_days": 2, "playbook": "payment_reconciliation", "note": "End-to-end plaćanje mora biti provereno pre korisnika."},
    {"title": "Napraviti refund test scenario", "lane": "Support", "owner": "support", "priority": "medium", "status": "open", "due_days": 3, "playbook": "refund_flow", "note": "Kupac platio, prodavac otkazao, admin odobrava refund."},
    {"title": "Podesiti notification journey za novu rezervaciju", "lane": "Notifications", "owner": "ops", "priority": "medium", "status": "open", "due_days": 3, "playbook": "notifications", "note": "Kupac i prodavac moraju dobiti jasnu poruku nakon rezervacije."},
    {"title": "Pripremiti onboarding paket za prvih 10 prodavaca", "lane": "Seller Success", "owner": "success", "priority": "medium", "status": "open", "due_days": 5, "playbook": "seller_training", "note": "PIN, seller-pro link, pravila, primeri ponuda i fotografisanja."},
    {"title": "Objaviti PRVI5 i PECIVO18 kampanje", "lane": "Growth", "owner": "growth", "priority": "medium", "status": "open", "due_days": 5, "playbook": "campaigns", "note": "Kampanje za prvu rezervaciju i večernje pekarske ponude."},
    {"title": "Pokrenuti dnevni finansijski izveštaj", "lane": "Finance", "owner": "finance", "priority": "medium", "status": "open", "due_days": 6, "playbook": "finance_daily", "note": "Plaćeno, provizija, neto za prodavce i pending isplate."},
    {"title": "Napraviti support makroe za 10 najčešćih problema", "lane": "Support", "owner": "support", "priority": "low", "status": "open", "due_days": 7, "playbook": "support_macros", "note": "Kašnjenje, otkazivanje, refund, pogrešna cena, GPS, QR, OTP."},
]

AUTOMATION_RULES = [
    {"name": "Sakrij istekle ponude", "trigger": "hourly", "risk": "critical", "enabled": True, "mode": "safe", "action": "expiry_date < today -> status expired/hidden"},
    {"name": "Blokiraj javno bez slike", "trigger": "before_publish", "risk": "high", "enabled": True, "mode": "safe", "action": "visible offer without image -> needs_review/hidden"},
    {"name": "Flag ekstreman popust", "trigger": "before_publish", "risk": "medium", "enabled": True, "mode": "review", "action": "discount > 85% -> admin review"},
    {"name": "Podsetnik kupcu", "trigger": "30_min_before_pickup", "risk": "low", "enabled": False, "mode": "notification", "action": "send SMS/push reminder"},
    {"name": "Prodavac ne potvrđuje rezervacije", "trigger": "reservation_age_gt_30min", "risk": "medium", "enabled": False, "mode": "notification", "action": "notify seller/support"},
]

PLAYBOOKS = [
    {"name": "Seller outreach — prvi poziv", "audience": "sales", "steps": ["Predstavi problem viška hrane", "Objasni da se objava radi slikom za 30 sekundi", "Naglasiti bez fiksnog troška u pilotu", "Dogovoriti 3 dana testiranja", "Poslati seller link i PIN"], "success_metric": "seller_verified"},
    {"name": "Seller onboarding — prvi dan", "audience": "seller_success", "steps": ["Dodati lokaciju i radno vreme", "Objasniti realnu sliku proizvoda", "Napraviti prvu test ponudu", "Testirati rezervaciju", "Dogovoriti dnevno vreme objave"], "success_metric": "first_public_offer"},
    {"name": "Quality gate — javna ponuda", "audience": "ops", "steps": ["Naziv jasan", "Cena i popust realni", "Količina uneta", "Slika postoji", "Vreme preuzimanja jasno", "Rok nije istekao"], "success_metric": "offer_approved"},
    {"name": "Refund handling", "audience": "support", "steps": ["Otvoriti rezervaciju", "Proveriti payment status", "Zabeležiti razlog", "Kontaktirati prodavca ako treba", "Odobriti ili odbiti refund", "Zatvoriti ticket"], "success_metric": "resolved_ticket"},
    {"name": "Daily finance reconciliation", "audience": "finance", "steps": ["Skinuti izvod/bankovni pregled", "Uporediti reference", "Potvrditi uplate", "Obračunati 25% proviziju", "Označiti isplate prodavcima"], "success_metric": "settlement_complete"},
]

SLA_RULES = [
    {"name": "Prodavac potvrđuje rezervaciju", "target_minutes": 30, "severity": "medium", "owner": "seller", "escalation": "seller_success"},
    {"name": "Support odgovor kupcu", "target_minutes": 120, "severity": "medium", "owner": "support", "escalation": "ops"},
    {"name": "Refund odluka", "target_minutes": 1440, "severity": "high", "owner": "finance/support", "escalation": "admin"},
    {"name": "Sporna ponuda", "target_minutes": 60, "severity": "high", "owner": "ops", "escalation": "admin"},
]

class TaskPatch(BaseModel):
    status: str | None = None
    owner: str | None = None
    priority: str | None = None
    note: str | None = None
    due_date: str | None = None

class TaskCreate(BaseModel):
    title: str
    lane: str = "Ops"
    owner: str = "ops"
    priority: str = "medium"
    status: str = "open"
    note: str | None = None


def money(value: Any) -> float:
    return round(float(value or 0), 2)


def _metrics(db: Session) -> dict[str, Any]:
    products_total = db.query(func.count(models.Product.id)).scalar() or 0
    visible_q = db.query(models.Product).filter(models.Product.status.in_(VISIBLE_STATUSES))
    visible = visible_q.count()
    with_image = visible_q.filter(models.Product.image_url.isnot(None), models.Product.image_url != "").count()
    stores_total = db.query(func.count(models.Store.id)).scalar() or 0
    verified = db.query(func.count(models.Store.id)).filter(models.Store.verified == True).scalar() or 0
    reservations_total = db.query(func.count(models.Reservation.id)).scalar() or 0
    active = db.query(func.count(models.Reservation.id)).filter(models.Reservation.status.in_(ACTIVE_ORDER_STATUSES)).scalar() or 0
    picked_up = db.query(func.count(models.Reservation.id)).filter(models.Reservation.status.in_(DONE_STATUSES)).scalar() or 0
    bad = db.query(func.count(models.Reservation.id)).filter(models.Reservation.status.in_(BAD_ORDER_STATUSES)).scalar() or 0
    paid_count = db.query(func.count(models.Reservation.id)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    paid_sum = db.query(func.coalesce(func.sum(models.Reservation.payable_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    fee_sum = db.query(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    seller_net = db.query(func.coalesce(func.sum(models.Reservation.seller_net_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    city_counts = Counter()
    cat_counts = Counter()
    for city, cat in db.query(models.Store.city, models.Product.category).join(models.Product, models.Product.store_id == models.Store.id).filter(models.Product.status.in_(VISIBLE_STATUSES)).all():
        city_counts[city or "Nepoznato"] += 1
        cat_counts[cat or "ostalo"] += 1
    img_pct = round((with_image / visible) * 100, 1) if visible else 0
    pickup_rate = round((picked_up / reservations_total) * 100, 1) if reservations_total else 0
    issue_rate = round((bad / reservations_total) * 100, 1) if reservations_total else 0
    readiness_score = round(min(100, (visible / 250) * 35 + (img_pct / 95) * 25 + (verified / 10) * 25 + (paid_count / 10) * 15), 1)
    return {
        "products_total": int(products_total),
        "visible_offers": int(visible),
        "offers_with_image": int(with_image),
        "offers_without_image": int(max(0, visible - with_image)),
        "image_coverage_percent": img_pct,
        "stores_total": int(stores_total),
        "verified_stores": int(verified),
        "reservations_total": int(reservations_total),
        "active_orders": int(active),
        "picked_up": int(picked_up),
        "bad_orders": int(bad),
        "pickup_rate_percent": pickup_rate,
        "issue_rate_percent": issue_rate,
        "paid_count": int(paid_count),
        "paid_amount": money(paid_sum),
        "platform_fee": money(fee_sum),
        "seller_net": money(seller_net),
        "readiness_score": readiness_score,
        "estimated_kg_saved": round(int(picked_up) * 0.35, 2),
        "top_cities": city_counts.most_common(10),
        "top_categories": cat_counts.most_common(10),
        "generated_at": datetime.utcnow().isoformat(),
    }


def _gap_tasks(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    def add(key: str, title: str, lane: str, priority: str, target: Any, current: Any, note: str):
        rows.append({"key": key, "title": title, "lane": lane, "priority": priority, "target": target, "current": current, "note": note, "status": "open", "owner": lane.lower().replace(" ", "_"), "created_from": "metrics"})
    if metrics["visible_offers"] < 250:
        add("gap_visible_offers", "Dostići 250 javnih ponuda", "Supply", "high", 250, metrics["visible_offers"], "Bez dovoljno ponuda nema efekta pretrage, AI asistenta ni kampanja.")
    if metrics["image_coverage_percent"] < 95:
        add("gap_images", "Podići pokrivenost slikama na 95%", "Trust", "high", "95%", f"{metrics['image_coverage_percent']}%", "Sakriti ponude bez slike i forsirati kameru u seller panelu.")
    if metrics["verified_stores"] < 10:
        add("gap_verified_sellers", "Dovesti 10 verifikovanih partnera", "Sales", "high", 10, metrics["verified_stores"], "Kontaktirati leadove i završiti onboarding prvih partnera.")
    if metrics["paid_count"] < 10:
        add("gap_payments", "Zatvoriti 10 test plaćanja", "Finance", "medium", 10, metrics["paid_count"], "Proveriti QR, checkout i ručnu potvrdu uplata.")
    if metrics["issue_rate_percent"] > 5:
        add("gap_issues", "Spustiti reklamacije/loše ishode ispod 5%", "Support", "high", "<5%", f"{metrics['issue_rate_percent']}%", "Analizirati otkazivanja, no-show i refund razloge.")
    return rows


@router.get("/dashboard", response_model=dict)
def dashboard(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    metrics = _metrics(db)
    tasks = read_json("v41_execution_tasks.json", [])
    open_tasks = [t for t in tasks if isinstance(t, dict) and t.get("status") not in {"done", "cancelled"}]
    lanes = Counter([t.get("lane", "Ops") for t in tasks if isinstance(t, dict)])
    return {
        "version": "V41 Execution Engine",
        "metrics": metrics,
        "open_tasks": len(open_tasks),
        "task_lanes": lanes.most_common(),
        "gaps": _gap_tasks(metrics),
        "next_phase": "Pretvoriti strategiju iz V40 u svakodnevno izvršavanje: taskovi, seller score, city readiness, automatizacije i weekly brief.",
    }


@router.post("/seed/all", response_model=dict)
def seed_all(request: Request, _: bool = Depends(require_admin_session)):
    today = date.today()
    existing = read_json("v41_execution_tasks.json", [])
    existing_titles = {str(x.get("title", "")).lower() for x in existing if isinstance(x, dict)}
    added = 0
    for row in EXECUTION_TASKS:
        if row["title"].lower() in existing_titles:
            continue
        payload = dict(row)
        payload["due_date"] = (today + timedelta(days=int(payload.pop("due_days", 7)))).isoformat()
        append_json_row("v41_execution_tasks.json", payload)
        added += 1
    write_json("v41_automation_rules.json", AUTOMATION_RULES)
    write_json("v41_playbooks.json", PLAYBOOKS)
    write_json("v41_sla_rules.json", SLA_RULES)
    return {"ok": True, "tasks_added": added, "automations": len(AUTOMATION_RULES), "playbooks": len(PLAYBOOKS), "sla_rules": len(SLA_RULES)}


@router.get("/tasks", response_model=list[dict])
def list_tasks(request: Request, _: bool = Depends(require_admin_session)):
    return read_json("v41_execution_tasks.json", [])


@router.post("/tasks", response_model=dict)
def add_task(payload: TaskCreate, request: Request, _: bool = Depends(require_admin_session)):
    row = payload.model_dump()
    row.setdefault("created_from", "manual")
    row.setdefault("due_date", (date.today() + timedelta(days=7)).isoformat())
    return append_json_row("v41_execution_tasks.json", row)


@router.patch("/tasks/{task_id}", response_model=dict)
def patch_task(task_id: str, payload: TaskPatch, request: Request, _: bool = Depends(require_admin_session)):
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    row = update_json_row("v41_execution_tasks.json", task_id, patch)
    return {"ok": bool(row), "row": row}


@router.post("/tasks/generate-from-metrics", response_model=dict)
def generate_tasks_from_metrics(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    metrics = _metrics(db)
    gaps = _gap_tasks(metrics)
    rows = read_json("v41_execution_tasks.json", [])
    existing_keys = {str(x.get("key", "")) for x in rows if isinstance(x, dict)}
    added = 0
    for gap in gaps:
        if gap["key"] in existing_keys:
            continue
        payload = dict(gap)
        payload["due_date"] = (date.today() + timedelta(days=5 if gap["priority"] == "high" else 10)).isoformat()
        append_json_row("v41_execution_tasks.json", payload)
        added += 1
    return {"ok": True, "added": added, "gaps": gaps}


@router.get("/seller-scorecards", response_model=dict)
def seller_scorecards(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    stores = db.query(models.Store).all()
    cards = []
    for store in stores:
        products = db.query(models.Product).filter(models.Product.store_id == store.id).all()
        visible = [p for p in products if p.status in VISIBLE_STATUSES]
        with_img = [p for p in visible if p.image_url]
        reservations = db.query(models.Reservation).join(models.Product, models.Reservation.product_id == models.Product.id).filter(models.Product.store_id == store.id).all()
        paid = [r for r in reservations if r.payment_status == "paid"]
        picked = [r for r in reservations if r.status in DONE_STATUSES]
        image_pct = round(len(with_img) / len(visible) * 100, 1) if visible else 0
        score = 0
        score += 25 if store.verified else 0
        score += min(25, len(visible) * 5)
        score += min(20, image_pct / 5)
        score += min(20, len(reservations) * 4)
        score += min(10, len(paid) * 5)
        if not store.verified:
            action = "Verifikovati prodavca i završiti onboarding."
        elif len(visible) == 0:
            action = "Tražiti prve javne ponude kroz seller panel."
        elif image_pct < 95:
            action = "Dopuniti fotografije proizvoda."
        elif len(reservations) == 0:
            action = "Uključiti u kampanju / ponuditi večernji popust."
        else:
            action = "Dobro radi — skalirati broj ponuda."
        cards.append({
            "store_id": store.id, "name": store.name, "city": store.city, "verified": store.verified,
            "visible_offers": len(visible), "image_coverage_percent": image_pct,
            "reservations": len(reservations), "paid": len(paid), "picked_up": len(picked),
            "score": round(score, 1), "recommended_action": action,
        })
    cards.sort(key=lambda x: x["score"], reverse=True)
    return {"count": len(cards), "top": cards[:10], "needs_attention": list(reversed(cards[-10:])) if cards else []}


@router.get("/city-readiness", response_model=list[dict])
def city_readiness(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    stores = db.query(models.Store).all()
    by_city: dict[str, dict[str, Any]] = defaultdict(lambda: {"stores": 0, "verified": 0, "offers": 0, "offers_with_image": 0, "reservations": 0, "paid": 0})
    for s in stores:
        city = s.city or "Nepoznato"
        by_city[city]["stores"] += 1
        if s.verified:
            by_city[city]["verified"] += 1
    product_rows = db.query(models.Product, models.Store.city).outerjoin(models.Store, models.Product.store_id == models.Store.id).all()
    for p, city in product_rows:
        c = city or "Nepoznato"
        if p.status in VISIBLE_STATUSES:
            by_city[c]["offers"] += 1
            if p.image_url:
                by_city[c]["offers_with_image"] += 1
    reservation_rows = db.query(models.Reservation, models.Store.city).join(models.Product, models.Reservation.product_id == models.Product.id).outerjoin(models.Store, models.Product.store_id == models.Store.id).all()
    for r, city in reservation_rows:
        c = city or "Nepoznato"
        by_city[c]["reservations"] += 1
        if r.payment_status == "paid":
            by_city[c]["paid"] += 1
    result = []
    for city, x in by_city.items():
        image_pct = round(x["offers_with_image"] / x["offers"] * 100, 1) if x["offers"] else 0
        score = round(min(100, (x["verified"] / 10) * 35 + (x["offers"] / 250) * 35 + (image_pct / 95) * 20 + (x["reservations"] / 100) * 10), 1)
        stage = "pilot_ready" if score >= 75 else "build_supply" if score >= 40 else "research"
        result.append({"city": city, **x, "image_coverage_percent": image_pct, "readiness_score": score, "stage": stage})
    result.sort(key=lambda x: x["readiness_score"], reverse=True)
    return result


@router.get("/automation-rules", response_model=list[dict])
def automation_rules(request: Request, _: bool = Depends(require_admin_session)):
    return read_json("v41_automation_rules.json", [])


@router.post("/automations/run-safe-checks", response_model=dict)
def run_safe_checks(request: Request, dry_run: bool = Query(True), db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    today = date.today()
    expired = db.query(models.Product).filter(models.Product.status.in_(VISIBLE_STATUSES)).filter(models.Product.expiry_date.isnot(None)).filter(models.Product.expiry_date < today).all()
    no_image = db.query(models.Product).filter(models.Product.status.in_(VISIBLE_STATUSES)).filter((models.Product.image_url.is_(None)) | (models.Product.image_url == "")).all()
    extreme_discount = db.query(models.Product).filter(models.Product.status.in_(VISIBLE_STATUSES)).filter(models.Product.discount_percent != None).filter(models.Product.discount_percent > 85).all()
    changed = {"expired_hidden": 0, "no_image_hidden": 0, "extreme_discount_review": len(extreme_discount)}
    if not dry_run:
        for p in expired:
            p.status = "expired"
            p.updated_at = datetime.utcnow()
            changed["expired_hidden"] += 1
        for p in no_image:
            p.status = "hidden"
            p.updated_at = datetime.utcnow()
            changed["no_image_hidden"] += 1
        db.commit()
    return {"ok": True, "dry_run": dry_run, "found": {"expired": len(expired), "no_image": len(no_image), "extreme_discount": len(extreme_discount)}, "changed": changed}


@router.get("/playbooks", response_model=list[dict])
def playbooks(request: Request, _: bool = Depends(require_admin_session)):
    return read_json("v41_playbooks.json", [])


@router.get("/sla", response_model=list[dict])
def sla(request: Request, _: bool = Depends(require_admin_session)):
    return read_json("v41_sla_rules.json", [])


@router.get("/weekly-brief", response_model=dict)
def weekly_brief(request: Request, db: Session = Depends(get_db), _: bool = Depends(require_admin_session)):
    metrics = _metrics(db)
    tasks = read_json("v41_execution_tasks.json", [])
    open_high = [t for t in tasks if isinstance(t, dict) and t.get("status") != "done" and t.get("priority") == "high"]
    city_rows = city_readiness(request, db, True)  # type: ignore[arg-type]
    return {
        "title": "Sačuvaj Hranu — weekly execution brief",
        "generated_at": utc_now(),
        "readiness_score": metrics["readiness_score"],
        "headline": "Prioritet ostaje likvidnost ponuda sa slikama i verifikacija prodavaca pre agresivnog marketinga.",
        "numbers": {
            "visible_offers": metrics["visible_offers"],
            "image_coverage": f"{metrics['image_coverage_percent']}%",
            "verified_stores": metrics["verified_stores"],
            "reservations": metrics["reservations_total"],
            "paid_amount_rsd": metrics["paid_amount"],
            "platform_fee_rsd": metrics["platform_fee"],
        },
        "top_risks": _gap_tasks(metrics),
        "high_priority_tasks": open_high[:8],
        "best_city": city_rows[0] if city_rows else None,
        "recommended_next_7_days": [
            "Dovesti 10 partnera u Beogradu i naterati seller kameru kao glavni unos.",
            "Sakriti ponude bez slike i ne puštati marketing dok pokrivenost slikama nije preko 95%.",
            "Napraviti 10 test plaćanja i završiti ručnu finansijsku potvrdu.",
            "Koristiti PRVI5 i PECIVO18 samo u zonama gde ima dovoljno ponuda.",
        ],
    }
