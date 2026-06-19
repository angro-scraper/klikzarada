from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from random import Random
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db

router = APIRouter(prefix="/v48", tags=["V48 Super App"])

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR.parent
DATA_DIR = BACKEND_DIR / "data" / "v48_super_app"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = DATA_DIR / "state.json"

CITY_COORDS = {
    "Beograd": (44.8125, 20.4612),
    "Novi Sad": (45.2671, 19.8335),
    "Niš": (43.3209, 21.8958),
    "Kragujevac": (44.0128, 20.9114),
    "Subotica": (46.1005, 19.6651),
    "Čačak": (43.8914, 20.3497),
    "Kraljevo": (43.7234, 20.6870),
    "Leskovac": (42.9981, 21.9461),
    "Valjevo": (44.2751, 19.8982),
    "Zrenjanin": (45.3836, 20.3819),
    "Pančevo": (44.8708, 20.6403),
    "Šabac": (44.7562, 19.6922),
    "Sombor": (45.7733, 19.1151),
    "Užice": (43.8586, 19.8442),
    "Kruševac": (43.5800, 21.3267),
    "Smederevo": (44.6659, 20.9335),
    "Novi Pazar": (43.1375, 20.5149),
    "Pirot": (43.1531, 22.5861),
    "Zaječar": (43.9019, 22.2738),
    "Jagodina": (43.9791, 21.2612),
    "Loznica": (44.5335, 19.2258),
    "Vršac": (45.1169, 21.3036),
    "Ruma": (45.0081, 19.8222),
    "Kikinda": (45.8297, 20.4653),
    "Bor": (44.0749, 22.0959),
}

STORE_KINDS = [
    ("Pekara", "pekara"),
    ("Dnevna kuhinja", "gotova jela"),
    ("Mini market", "market"),
    ("Voće i povrće", "voće i povrće"),
    ("Poslastičarnica", "poslastice"),
    ("Mlečni kutak", "mlečni proizvodi"),
    ("Sendvič bar", "sendviči"),
    ("Zdravi obrok", "salate"),
    ("Delikates", "delikates"),
    ("Market Express", "korpa iznenađenja"),
]

PRODUCTS = [
    ("Pekarski miks posle 18h", "pekara", 420, 239, "best_before", "danas 18-21h", "pecivo-mix.svg"),
    ("Burek sa sirom 1/4", "pekara", 240, 159, "best_before", "danas 17-20h", "burek-sir.svg"),
    ("Burek sa mesom 1/4", "pekara", 280, 189, "best_before", "danas 17-20h", "burek-sir.svg"),
    ("Kiflice mix 6 kom", "pekara", 390, 229, "best_before", "danas 18-21h", "kiflice.svg"),
    ("Integralni hleb 500g", "pekara", 190, 119, "best_before", "danas 16-20h", "hleb-integralni.svg"),
    ("Kroasan čokolada", "pekara", 220, 139, "best_before", "danas 18-21h", "kroasan.svg"),
    ("Dnevni meni — porcija", "gotova jela", 690, 449, "use_by", "danas 16-19h", "dnevni-meni.svg"),
    ("Kuvani obrok dana", "kuvana jela", 760, 499, "use_by", "danas 16-19h", "topli-obrok.svg"),
    ("Pileća salata", "salate", 540, 349, "use_by", "danas 15-18h", "salata.svg"),
    ("Sendvič šunka sir", "sendviči", 390, 249, "use_by", "danas 16-20h", "sendvic.svg"),
    ("Sendvič piletina", "sendviči", 460, 299, "use_by", "danas 16-20h", "sendvic.svg"),
    ("Jogurt 1kg", "mlečni proizvodi", 230, 159, "best_before", "sutra 10-20h", "mleko.svg"),
    ("Mleko 1l", "mlečni proizvodi", 175, 129, "best_before", "sutra 10-20h", "mleko.svg"),
    ("Mladi sir 250g", "mlečni proizvodi", 350, 229, "best_before", "sutra 10-20h", "mleko.svg"),
    ("Pakovanje banana 1kg", "voće i povrće", 200, 119, "best_before", "danas 12-20h", "voce-povrce.svg"),
    ("Paradajz 1kg", "voće i povrće", 280, 169, "best_before", "danas 12-20h", "voce-povrce.svg"),
    ("Mešana salata za kuvanje", "voće i povrće", 330, 199, "best_before", "danas 12-20h", "voce-povrce.svg"),
    ("Kolač dana", "poslastice", 360, 229, "best_before", "danas 17-21h", "kolac.svg"),
    ("Torta parče", "poslastice", 420, 269, "best_before", "danas 17-21h", "kolac.svg"),
    ("Korpa iznenađenja", "korpa iznenađenja", 790, 449, "best_before", "danas 19-21h", "paket.svg"),
    ("Kafa + kroasan", "kafa i doručak", 440, 299, "best_before", "sutra 08-11h", "kroasan.svg"),
    ("Zdravi doručak paket", "zdrava hrana", 590, 379, "use_by", "danas 14-18h", "salata.svg"),
]


def _read_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"campaigns": [], "experiments": [], "journeys": [], "created_at": datetime.utcnow().isoformat()}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"campaigns": [], "experiments": [], "journeys": [], "created_at": datetime.utcnow().isoformat()}


def _write_state(state: dict[str, Any]) -> dict[str, Any]:
    state["updated_at"] = datetime.utcnow().isoformat()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def _discount(old: float, new: float) -> float:
    return round(max(0, (old - new) / old * 100), 1) if old else 0.0


def _image(name: str) -> str:
    return f"/admin-assets/seed-images/{name}"


def _visible_products(db: Session):
    return db.query(models.Product).filter(models.Product.status.in_(["seller_verified", "near_expiry", "public_discount"]))


@router.get("/status")
def status(db: Session = Depends(get_db)):
    products_q = _visible_products(db)
    products = products_q.all()
    stores = db.query(models.Store).all()
    reservations = db.query(models.Reservation).all()
    paid = [r for r in reservations if (r.payment_status or "").lower() in {"paid", "confirmed", "settled"}]
    city_counts = dict(db.query(models.Store.city, func.count(models.Product.id)).join(models.Product, models.Product.store_id == models.Store.id).filter(models.Product.status.in_(["seller_verified", "near_expiry", "public_discount"])).group_by(models.Store.city).all())
    with_image = [p for p in products if p.image_url]
    with_gps = [p for p in products if p.store and p.store.latitude is not None and p.store.longitude is not None]
    verified_stores = [s for s in stores if s.verified]
    revenue = round(sum((r.payable_amount or 0) for r in paid), 2)
    platform_fee = round(sum((r.platform_fee_amount or 0) for r in paid), 2)
    score = 0
    checks = [
        (len(products) >= 250, 18, "250+ javnih ponuda"),
        (len(with_image) / len(products) >= 0.95 if products else False, 14, "95% ponuda sa slikom"),
        (len(with_gps) / len(products) >= 0.90 if products else False, 14, "90% ponuda sa GPS-om"),
        (len(city_counts) >= 10, 12, "10+ gradova sa ponudama"),
        (len(verified_stores) >= 50, 12, "50+ verifikovanih prodavaca"),
        (len(reservations) >= 10, 8, "10+ test rezervacija"),
        (revenue > 0, 7, "test plaćanja/provizije"),
        (bool(_read_state().get("journeys")), 7, "notification journeys"),
        (bool(_read_state().get("experiments")), 8, "growth eksperimenti"),
    ]
    missing = []
    for ok, pts, label in checks:
        if ok:
            score += pts
        else:
            missing.append(label)
    return {
        "ok": True,
        "score": min(score, 100),
        "missing": missing,
        "metrics": {
            "public_products": len(products),
            "products_with_image": len(with_image),
            "products_with_gps": len(with_gps),
            "stores_total": len(stores),
            "verified_stores": len(verified_stores),
            "cities_with_offers": len(city_counts),
            "reservations": len(reservations),
            "paid_reservations": len(paid),
            "paid_revenue": revenue,
            "platform_fee": platform_fee,
            "city_counts": city_counts,
        },
        "state": _read_state(),
    }


@router.post("/seed-super-database")
def seed_super_database(db: Session = Depends(get_db)):
    rng = Random(4800)
    created_stores = 0
    created_products = 0
    today = date.today()
    for city, (lat, lng) in CITY_COORDS.items():
        for idx, (kind, base_category) in enumerate(STORE_KINDS, start=1):
            store_name = f"{kind} {city} — Super Pilot {idx}"
            store = db.query(models.Store).filter(models.Store.name == store_name, models.Store.city == city).first()
            if not store:
                store = models.Store(
                    name=store_name,
                    city=city,
                    address=f"Centar {idx}, {city}",
                    latitude=lat + rng.uniform(-0.03, 0.03),
                    longitude=lng + rng.uniform(-0.03, 0.03),
                    website="https://example.com/super-pilot",
                    phone=f"060{rng.randint(1000000, 9999999)}",
                    verified=True,
                )
                db.add(store)
                db.flush()
                created_stores += 1
            compatible = [p for p in PRODUCTS if p[1] == base_category or base_category in {"market", "korpa iznenađenja"}]
            if len(compatible) < 4:
                compatible = PRODUCTS[:]
            rng.shuffle(compatible)
            for n, item in enumerate(compatible[:8], start=1):
                name, category, old, new, expiry_type, pickup, img = item
                source_url = f"seed://v48/{city}/{idx}/{n}/{name.lower().replace(' ', '-') }"
                exists = db.query(models.Product.id).filter(models.Product.source_url == source_url).first()
                if exists:
                    continue
                multiplier = rng.choice([0.88, 0.94, 1.0, 1.06, 1.12])
                original = round(old * multiplier / 10) * 10
                discounted = round(new * multiplier / 10) * 10
                exp_days = rng.choice([0, 0, 1, 1, 2, 3])
                status = "near_expiry" if exp_days <= 1 else rng.choice(["seller_verified", "public_discount"])
                db.add(models.Product(
                    store_id=store.id,
                    name=f"{name} — {city}",
                    category=category,
                    original_price=float(original),
                    discounted_price=float(discounted),
                    discount_percent=_discount(original, discounted),
                    currency="RSD",
                    expiry_date=today + timedelta(days=exp_days),
                    expiry_type=expiry_type,
                    quantity=rng.randint(5, 30),
                    pickup_window=pickup,
                    image_url=_image(img),
                    source_url=source_url,
                    confidence_score=0.96,
                    status=status,
                ))
                created_products += 1
    db.commit()
    return {
        "ok": True,
        "created_stores": created_stores,
        "created_products": created_products,
        "message": "Super pilot baza je napunjena: više gradova, prodavaca, GPS, slike, cene, količine i rokovi.",
    }


@router.post("/activate-growth-system")
def activate_growth_system():
    state = _read_state()
    state["campaigns"] = [
        {"code": "PRVI5", "title": "5% za prvu rezervaciju", "discount": 5, "status": "active", "target": "novi kupci"},
        {"code": "PECIVO18", "title": "Pekare posle 18h", "discount": 3, "status": "active", "target": "večernje ponude"},
        {"code": "BLIZU3", "title": "Ponude u krugu 3 km", "discount": 2, "status": "active", "target": "GPS korisnici"},
        {"code": "POVRATAK", "title": "Vrati se ove nedelje", "discount": 4, "status": "draft", "target": "neaktivni korisnici"},
    ]
    state["journeys"] = [
        {"name": "Nova rezervacija", "channel": "SMS + in-app", "trigger": "reservation_created", "message": "Rezervacija je kreirana. Sačuvajte kod i dođite u vreme preuzimanja."},
        {"name": "Podsetnik za preuzimanje", "channel": "SMS", "trigger": "30_min_before_pickup", "message": "Podsetnik: vaša ponuda uskoro čeka kod prodavca."},
        {"name": "Nova ponuda u blizini", "channel": "push", "trigger": "new_offer_near_saved_search", "message": "Pojavila se nova ponuda blizu vas."},
        {"name": "No-show opomena", "channel": "SMS", "trigger": "no_show_risk", "message": "Ako ne možete da preuzmete, otkažite rezervaciju na vreme."},
    ]
    state["experiments"] = [
        {"name": "AI search placeholder", "hypothesis": "Konkretni primeri povećavaju pretrage", "metric": "search_to_reservation", "status": "ready"},
        {"name": "Mapa kao prvi ekran", "hypothesis": "Mapa povećava blizinske rezervacije", "metric": "gps_enabled_rate", "status": "ready"},
        {"name": "Pekare posle 18h", "hypothesis": "Večernji kontekst povećava konverziju", "metric": "reservation_rate_after_18", "status": "ready"},
    ]
    state["operating_cadence"] = [
        "09:00 proveriti ponude bez slike/GPS",
        "12:00 kontaktirati nove prodavce",
        "17:00 aktivirati večernje pekarske ponude",
        "21:30 zatvoriti istekle ponude i poslati dnevni brief",
    ]
    return _write_state(state)


@router.get("/city-dashboard")
def city_dashboard(db: Session = Depends(get_db)):
    visible = ["seller_verified", "near_expiry", "public_discount"]
    rows = db.query(models.Store.city, func.count(models.Product.id), func.count(func.distinct(models.Store.id))).join(models.Product, models.Product.store_id == models.Store.id).filter(models.Product.status.in_(visible)).group_by(models.Store.city).all()
    result = []
    for city, offers, stores in rows:
        readiness = min(100, int((offers / 50) * 55 + (stores / 10) * 35 + 10))
        result.append({
            "city": city or "Nepoznato",
            "offers": offers,
            "stores": stores,
            "readiness": readiness,
            "next_action": "Kontaktirati još prodavaca" if stores < 10 else "Pojačati marketing" if offers >= 50 else "Dodati još ponuda",
        })
    return {"ok": True, "cities": sorted(result, key=lambda x: x["readiness"], reverse=True)}


@router.get("/dynamic-pricing")
def dynamic_pricing(db: Session = Depends(get_db)):
    today = date.today()
    products = _visible_products(db).limit(200).all()
    suggestions = []
    for p in products:
        if not p.discounted_price or not p.original_price:
            continue
        days_left = (p.expiry_date - today).days if p.expiry_date else None
        current_discount = p.discount_percent or _discount(p.original_price, p.discounted_price)
        target_discount = current_discount
        reason = "Cena je u redu."
        if days_left is not None and days_left <= 0 and current_discount < 45:
            target_discount = 50
            reason = "Rok je danas — predlog jačeg popusta."
        elif days_left is not None and days_left <= 1 and current_discount < 35:
            target_discount = 40
            reason = "Rok je sutra/danas — povećati popust."
        elif current_discount < 20:
            target_discount = 25
            reason = "Popust je nizak za motivaciju kupca."
        new_price = round(p.original_price * (1 - target_discount / 100) / 10) * 10
        if target_discount != current_discount:
            suggestions.append({
                "product_id": p.id,
                "product": p.name,
                "store": p.store.name if p.store else None,
                "current_price": p.discounted_price,
                "suggested_price": new_price,
                "current_discount": current_discount,
                "target_discount": target_discount,
                "reason": reason,
            })
    return {"ok": True, "count": len(suggestions), "suggestions": suggestions[:80]}


@router.get("/ai-master-plan")
def ai_master_plan(db: Session = Depends(get_db)):
    status_data = status(db)
    metrics = status_data["metrics"]
    score = status_data["score"]
    plan = []
    if metrics["public_products"] < 250:
        plan.append({"area": "Baza", "priority": "high", "action": "Pokreni seed super baze i dovedi minimum 250 ponuda pre šireg testiranja."})
    if metrics["products_with_image"] < metrics["public_products"]:
        plan.append({"area": "Kvalitet", "priority": "high", "action": "Sakriti ili dopuniti ponude bez slike. Slika je ulazni uslov za poverenje."})
    if metrics["cities_with_offers"] < 10:
        plan.append({"area": "Gradovi", "priority": "medium", "action": "Dodati ponude u još gradova i otvoriti city landing stranice."})
    if metrics["verified_stores"] < 50:
        plan.append({"area": "Prodavci", "priority": "high", "action": "Napraviti dnevni cilj: 10 poziva, 3 demo-a, 1 verifikovan partner."})
    if not _read_state().get("journeys"):
        plan.append({"area": "Retencija", "priority": "medium", "action": "Aktivirati notification journeys za rezervaciju, podsetnik i ponude u blizini."})
    plan.append({"area": "AI", "priority": "strategic", "action": "AI treba da radi kao vodič: pronađi ponudu, objasni plaćanje, vodi kupca do preuzimanja."})
    plan.append({"area": "Go-live", "priority": "strategic", "action": f"Readiness je {score}/100. Ne ići široko dok score ne bude 85+."})
    return {"ok": True, "score": score, "plan": plan}


@router.get("/data-room")
def data_room(db: Session = Depends(get_db)):
    s = status(db)
    return {
        "ok": True,
        "sections": [
            {"title": "Product", "items": ["Mobile-first korisnička aplikacija", "Mapa + GPS", "AI pretraga", "Digitalna karta", "QR plaćanje"]},
            {"title": "Supply", "items": ["Seller panel", "Kamera unos", "PIN login", "Quality gates", "Real/pilot katalog"]},
            {"title": "Demand", "items": ["Loyalty 1-5%", "Referral", "Sačuvane pretrage", "Notifikacije", "Kampanje"]},
            {"title": "Finance", "items": ["25% platform fee", "Seller net", "Payout status", "IPS QR", "Excel export"]},
            {"title": "Metrics", "items": [f"Ponude: {s['metrics']['public_products']}", f"Prodavci: {s['metrics']['verified_stores']}", f"Gradovi: {s['metrics']['cities_with_offers']}", f"Readiness: {s['score']}/100"]},
        ]
    }
