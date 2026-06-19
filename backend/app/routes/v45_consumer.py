from __future__ import annotations

from datetime import date, timedelta
from random import Random
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db

router = APIRouter(prefix="/v45", tags=["v45-consumer-app"])

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
}

DISTRICTS_BG = [
    ("Vračar", "Kralja Milana 33", 44.8026, 20.4696),
    ("Novi Beograd", "Bulevar Mihajla Pupina 115", 44.8176, 20.4159),
    ("Zemun", "Glavna 27", 44.8450, 20.4102),
    ("Dorćol", "Cara Dušana 44", 44.8214, 20.4622),
    ("Zvezdara", "Bulevar kralja Aleksandra 234", 44.7989, 20.5097),
    ("Banovo brdo", "Požeška 83", 44.7779, 20.4183),
    ("Palilula", "Cvijićeva 78", 44.8150, 20.4878),
    ("Voždovac", "Vojvode Stepe 138", 44.7796, 20.4786),
    ("Karaburma", "Marijane Gregoran 21", 44.8210, 20.5034),
    ("Mirijevo", "Mirijevski bulevar 45", 44.7941, 20.5355),
    ("Bežanijska kosa", "Partizanske avijacije 31", 44.8229, 20.3922),
    ("Borča", "Ratnih vojnih invalida 42", 44.8702, 20.4588),
]

STORE_TEMPLATES = [
    ("Pekara", "pekara"),
    ("Dnevna kuhinja", "restoran"),
    ("Mini market", "market"),
    ("Voće i povrće", "voće i povrće"),
    ("Poslastičarnica", "poslastice"),
    ("Mlečni kutak", "mlečni proizvodi"),
    ("Sendvič bar", "sendviči"),
    ("Zdravi obrok", "salate"),
]

IMAGE_BY_CATEGORY = {
    "pekara": "/admin-assets/seed-images/burek-sir.svg",
    "restoran": "/admin-assets/seed-images/dnevni-meni.svg",
    "gotova jela": "/admin-assets/seed-images/dnevni-meni.svg",
    "market": "/admin-assets/seed-images/paket.svg",
    "mlečni proizvodi": "/admin-assets/seed-images/mleko.svg",
    "voće i povrće": "/admin-assets/seed-images/voce-povrce.svg",
    "poslastice": "/admin-assets/seed-images/kolac.svg",
    "sendviči": "/admin-assets/seed-images/sendvic.svg",
    "salate": "/admin-assets/seed-images/salata.svg",
    "kafa i doručak": "/admin-assets/seed-images/kroasan.svg",
    "kuvana jela": "/admin-assets/seed-images/topli-obrok.svg",
    "zdrava hrana": "/admin-assets/seed-images/salata.svg",
    "korpa iznenađenja": "/admin-assets/seed-images/pecivo-mix.svg",
}

PRODUCT_LIBRARY = [
    ("Pekarski miks posle 18h", "pekara", 420, 249, "best_before", "danas 18-21h"),
    ("Burek sa sirom 1/4", "pekara", 230, 159, "best_before", "danas 17-20h"),
    ("Burek sa mesom 1/4", "pekara", 260, 179, "best_before", "danas 17-20h"),
    ("Kiflice mix 6 kom", "pekara", 360, 219, "best_before", "danas 18-21h"),
    ("Integralni hleb 500g", "pekara", 190, 119, "best_before", "danas 16-20h"),
    ("Kroasan čokolada", "pekara", 210, 139, "best_before", "danas 18-21h"),
    ("Pita sa jabukom", "pekara", 280, 179, "best_before", "danas 18-21h"),
    ("Dnevni meni — porcija", "gotova jela", 680, 449, "use_by", "danas 16-19h"),
    ("Kuvani obrok dana", "kuvana jela", 740, 499, "use_by", "danas 16-19h"),
    ("Pileća salata", "salate", 520, 349, "use_by", "danas 15-18h"),
    ("Cezar salata", "salate", 590, 389, "use_by", "danas 15-18h"),
    ("Sendvič šunka sir", "sendviči", 390, 249, "use_by", "danas 16-20h"),
    ("Sendvič piletina", "sendviči", 450, 299, "use_by", "danas 16-20h"),
    ("Jogurt 1kg", "mlečni proizvodi", 220, 159, "best_before", "sutra 10-20h"),
    ("Mleko 1l", "mlečni proizvodi", 170, 129, "best_before", "sutra 10-20h"),
    ("Mladi sir 250g", "mlečni proizvodi", 340, 229, "best_before", "sutra 10-20h"),
    ("Pakovanje banana 1kg", "voće i povrće", 190, 119, "best_before", "danas 12-20h"),
    ("Paradajz 1kg", "voće i povrće", 260, 169, "best_before", "danas 12-20h"),
    ("Mešana salata za kuvanje", "voće i povrće", 320, 199, "best_before", "danas 12-20h"),
    ("Kolač dana", "poslastice", 350, 229, "best_before", "danas 17-21h"),
    ("Torta parče", "poslastice", 390, 259, "best_before", "danas 17-21h"),
    ("Korpa iznenađenja", "korpa iznenađenja", 700, 399, "best_before", "danas 19-21h"),
    ("Kafa + kroasan", "kafa i doručak", 420, 299, "best_before", "sutra 08-11h"),
    ("Zdravi doručak paket", "zdrava hrana", 560, 369, "use_by", "danas 14-18h"),
]


def _discount(old: float, new: float) -> int:
    if not old:
        return 0
    return round(max(0, (old - new) / old * 100))


def _store_exists(db: Session, name: str, city: str) -> models.Store | None:
    return db.query(models.Store).filter(models.Store.name == name, models.Store.city == city).first()


def _product_exists(db: Session, source_url: str) -> bool:
    return db.query(models.Product.id).filter(models.Product.source_url == source_url).first() is not None


def _make_city_stores(db: Session) -> list[models.Store]:
    rng = Random(45)
    stores: list[models.Store] = []
    for city, (lat, lng) in CITY_COORDS.items():
        if city == "Beograd":
            for idx, (district, address, dlat, dlng) in enumerate(DISTRICTS_BG, start=1):
                for kind, category in STORE_TEMPLATES[:6]:
                    name = f"{kind} {district} — Pilot"
                    existing = _store_exists(db, name, city)
                    if existing:
                        stores.append(existing)
                        continue
                    store = models.Store(
                        name=name,
                        city=city,
                        address=f"{address}, {district}",
                        latitude=dlat + rng.uniform(-0.004, 0.004),
                        longitude=dlng + rng.uniform(-0.004, 0.004),
                        website="https://example.com/pilot-partner",
                        phone=f"060{rng.randint(1000000, 9999999)}",
                        verified=True,
                    )
                    db.add(store)
                    stores.append(store)
        else:
            for index, (kind, category) in enumerate(STORE_TEMPLATES, start=1):
                name = f"{kind} {city} — Pilot {index}"
                existing = _store_exists(db, name, city)
                if existing:
                    stores.append(existing)
                    continue
                store = models.Store(
                    name=name,
                    city=city,
                    address=f"Centar {index}, {city}",
                    latitude=lat + rng.uniform(-0.025, 0.025),
                    longitude=lng + rng.uniform(-0.025, 0.025),
                    website="https://example.com/pilot-partner",
                    phone=f"060{rng.randint(1000000, 9999999)}",
                    verified=True,
                )
                db.add(store)
                stores.append(store)
    db.flush()
    return stores


@router.post("/seed-consumer-database", response_model=dict)
def seed_consumer_database(db: Session = Depends(get_db)):
    """Idempotent seed data for end-to-end consumer testing.

    This creates a broad pilot database with GPS, city coverage, categories, images, prices,
    quantities, expiry dates and pickup windows. It is intentionally marked with seed://v45
    source URLs so it can be identified/cleaned later.
    """
    stores = _make_city_stores(db)
    rng = Random(4500)
    created = 0
    today = date.today()
    for store in stores:
        # Make every city/category search return something without making the DB huge.
        picks = PRODUCT_LIBRARY[:]
        rng.shuffle(picks)
        for n, item in enumerate(picks[:10], start=1):
            name, category, original, discounted, expiry_type, pickup_window = item
            suffix = store.city or "Srbija"
            source_url = f"seed://v45/{store.id}/{n}/{name.lower().replace(' ', '-') }"
            if _product_exists(db, source_url):
                continue
            # Add slight price variety but keep realistic RSD values.
            multiplier = rng.choice([0.9, 1.0, 1.05, 1.1])
            old_price = round(original * multiplier / 10) * 10
            new_price = round(discounted * multiplier / 10) * 10
            exp_days = rng.choice([0, 1, 1, 2, 3])
            status = rng.choice(["seller_verified", "near_expiry", "public_discount"])
            if expiry_type == "use_by" and exp_days <= 1:
                status = "near_expiry"
            product = models.Product(
                store_id=store.id,
                name=f"{name} — {suffix}",
                category=category,
                original_price=float(old_price),
                discounted_price=float(new_price),
                discount_percent=float(_discount(old_price, new_price)),
                currency="RSD",
                expiry_date=today + timedelta(days=exp_days),
                expiry_type=expiry_type,
                quantity=rng.randint(4, 18),
                pickup_window=pickup_window,
                image_url=IMAGE_BY_CATEGORY.get(category, "/admin-assets/seed-images/pecivo-mix.svg"),
                source_url=source_url,
                confidence_score=0.94,
                status=status,
            )
            db.add(product)
            created += 1
    db.commit()
    total_products = db.query(models.Product).filter(models.Product.source_url.like("seed://v45/%")).count()
    total_stores = db.query(models.Store).filter(models.Store.name.like("%— Pilot%")).count()
    return {
        "ok": True,
        "created_products": created,
        "pilot_products_total": total_products,
        "pilot_stores_total": total_stores,
        "message": "Početna baza je spremna: gradovi, GPS lokacije, kategorije, slike, cene, količine, rokovi i vreme preuzimanja.",
    }


@router.get("/consumer-readiness", response_model=dict)
def consumer_readiness(db: Session = Depends(get_db)):
    visible = ["public_discount", "seller_verified", "near_expiry"]
    products_q = db.query(models.Product).filter(models.Product.status.in_(visible))
    stores_q = db.query(models.Store)
    total_products = products_q.count()
    with_images = products_q.filter(models.Product.image_url.is_not(None), models.Product.image_url != "").count()
    with_price = products_q.filter(models.Product.discounted_price.is_not(None)).count()
    with_quantity = products_q.filter(models.Product.quantity.is_not(None), models.Product.quantity > 0).count()
    with_gps = stores_q.filter(models.Store.latitude.is_not(None), models.Store.longitude.is_not(None)).count()
    city_rows = db.query(models.Store.city, func.count(models.Product.id)).join(models.Product, models.Product.store_id == models.Store.id).filter(models.Product.status.in_(visible)).group_by(models.Store.city).all()
    category_rows = db.query(models.Product.category, func.count(models.Product.id)).filter(models.Product.status.in_(visible)).group_by(models.Product.category).all()
    score_parts = [
        min(total_products / 80, 1),
        with_images / total_products if total_products else 0,
        with_price / total_products if total_products else 0,
        with_quantity / total_products if total_products else 0,
        min(with_gps / max(stores_q.count(), 1), 1),
        min(len([c for c, n in city_rows if n]) / 5, 1),
    ]
    readiness_score = round(sum(score_parts) / len(score_parts) * 100)
    return {
        "readiness_score": readiness_score,
        "products_total": total_products,
        "products_with_images": with_images,
        "products_with_price": with_price,
        "products_with_quantity": with_quantity,
        "stores_with_gps": with_gps,
        "cities": [{"city": c or "Nepoznato", "offers": n} for c, n in city_rows],
        "categories": [{"category": c or "ostalo", "offers": n} for c, n in category_rows],
        "needs_seed": total_products < 25 or with_images < max(total_products * 0.7, 1),
        "message": "Spremno za korisničko testiranje" if readiness_score >= 75 else "Potrebno je dopuniti bazu i slike pre šireg testa",
    }
