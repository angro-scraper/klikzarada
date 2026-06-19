from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import random
import shutil
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, inspect
from sqlalchemy.orm import Session

from . import models
from .database import Base, engine, get_db
from .routes.products import VISIBLE_STATUSES, product_available_quantity, product_to_public
from .routes.reservations import _reservation_to_out
from .services.excel_database import DATA_DIR, EXCEL_PATH, export_database_to_excel
from .services.json_store import read_json
from .services.pricing import apply_pricing_to_reservation, mark_paid
from .services.customers import apply_reservation_status_transition, register_reservation_created

router = APIRouter(prefix="/pilot-live", tags=["pilot-live"])

PILOT_PIN = "111111"
BACKEND_DIR = Path(__file__).resolve().parents[1]
BACKUP_DIR = DATA_DIR / "pilot_backups"
LAUNCH_MONITOR_REPORT = DATA_DIR / "launch_monitor_latest.json"
LAUNCH_MONITOR_HISTORY = DATA_DIR / "launch_monitor_history.json"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
LEGAL_PUBLIC_PATHS = {
    "support": ["/podrska", "/support"],
    "terms": ["/uslovi-koriscenja", "/terms"],
    "privacy": ["/privatnost", "/privacy"],
    "food_safety": ["/bezbednost-hrane", "/food-safety"],
}

PILOT_STORES = [
    {
        "name": "Pilot Restoran Zeleno",
        "city": "Beograd",
        "address": "Vojvode Stepe 123, Vozdovac",
        "latitude": 44.7727,
        "longitude": 20.4754,
        "phone": "+38160111222",
        "website": "https://sacuvaj-hranu.local/pilot/restoran-zeleno",
    },
    {
        "name": "Pilot Pekara Hleb i Kvasac",
        "city": "Beograd",
        "address": "Kolarceva 6, Stari grad",
        "latitude": 44.8152,
        "longitude": 20.4608,
        "phone": "+38160111333",
        "website": "https://sacuvaj-hranu.local/pilot/pekara-hleb",
    },
    {
        "name": "Pilot Picerija Napoli",
        "city": "Beograd",
        "address": "Bulevar kralja Aleksandra 74, Zvezdara",
        "latitude": 44.8058,
        "longitude": 20.4787,
        "phone": "+38160111444",
        "website": "https://sacuvaj-hranu.local/pilot/napoli",
    },
    {
        "name": "Pilot Zdravi Market",
        "city": "Beograd",
        "address": "Bulevar Mihajla Pupina 141, Novi Beograd",
        "latitude": 44.8193,
        "longitude": 20.4147,
        "phone": "+38160111555",
        "website": "https://sacuvaj-hranu.local/pilot/zdravi-market",
    },
]

PILOT_PRODUCTS = [
    ("Pilot Restoran Zeleno", "Domaći ručak", "restoran", 600, 360, 40, 10, "18:30 - 19:00", "topli-obrok.svg"),
    ("Pilot Restoran Zeleno", "Dnevni meni", "gotova jela", 720, 430, 40, 8, "19:00 - 19:30", "dnevni-meni.svg"),
    ("Pilot Restoran Zeleno", "Salata paket", "salate", 420, 250, 40, 6, "17:30 - 18:15", "salata.svg"),
    ("Pilot Pekara Hleb i Kvasac", "Pekarski miks", "pekara", 300, 150, 50, 16, "20:00 - 20:45", "pecivo-mix.svg"),
    ("Pilot Pekara Hleb i Kvasac", "Hleb integralni", "pekara", 220, 120, 45, 12, "19:30 - 20:30", "hleb-integralni.svg"),
    ("Pilot Pekara Hleb i Kvasac", "Kroasan paket", "pekara", 360, 210, 42, 10, "19:00 - 20:00", "kroasan.svg"),
    ("Pilot Picerija Napoli", "Pizza parče", "restoran", 400, 280, 30, 14, "18:00 - 19:00", "sendvic.svg"),
    ("Pilot Picerija Napoli", "Kiflice slane", "pekara", 330, 190, 42, 9, "19:00 - 20:00", "kiflice.svg"),
    ("Pilot Zdravi Market", "Voće i povrće paket", "voće i povrće", 800, 480, 40, 7, "16:30 - 18:30", "voce-povrce.svg"),
    ("Pilot Zdravi Market", "Mlečni paket", "mlečni proizvodi", 650, 390, 40, 5, "17:00 - 18:00", "mleko.svg"),
]


def _database_kind(database_url: str) -> str:
    if database_url.startswith("postgres"):
        return "postgresql"
    if database_url.startswith("mysql") or database_url.startswith("mariadb"):
        return "mysql/mariadb"
    if database_url.startswith("sqlite"):
        return "sqlite/local"
    return "other"


def _production_database_url(database_url: str) -> bool:
    return database_url.startswith("postgres") or database_url.startswith("mysql") or database_url.startswith("mariadb")


class PickupConfirmRequest(BaseModel):
    store_id: int
    pin: str = Field(min_length=4, max_length=20)
    reservation_code: str = Field(min_length=4, max_length=40)


class PartnerOnboardRequest(BaseModel):
    business_name: str = Field(min_length=2, max_length=180)
    category: str = Field(default="restoran", max_length=80)
    city: str = Field(default="Beograd", min_length=2, max_length=120)
    address: str = Field(min_length=3, max_length=255)
    contact_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=5, max_length=80)
    email: str | None = Field(default=None, max_length=160)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    first_offer_name: str = Field(default="Pilot obrok", min_length=2, max_length=255)
    original_price: float = Field(default=600, gt=0)
    discounted_price: float = Field(default=360, gt=0)
    quantity: int = Field(default=5, ge=1, le=500)
    pickup_window: str = Field(default="18:00 - 19:00", max_length=120)


def _money(value) -> float:
    return round(float(value or 0), 2)


def _env_bool(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).strip().lower() in {"1", "true", "yes", "da", "on"}


def _seed_image(filename: str) -> str:
    return f"/admin-assets/seed-images/{filename}"


def _find_store(db: Session, name: str) -> models.Store | None:
    return db.query(models.Store).filter(models.Store.name == name).first()


def _find_product(db: Session, store_id: int, name: str) -> models.Product | None:
    return db.query(models.Product).filter(models.Product.store_id == store_id, models.Product.name == name).first()


def _discount_percent(original: float, discounted: float) -> float:
    if original <= 0:
        return 0.0
    return round(max(0, min(95, (original - discounted) / original * 100)), 2)


def ensure_pilot_data(db: Session) -> dict:
    created_stores = 0
    updated_stores = 0
    created_products = 0
    updated_products = 0
    stores_by_name: dict[str, models.Store] = {}

    for payload in PILOT_STORES:
        store = _find_store(db, payload["name"])
        if store is None:
            store = models.Store(**payload, verified=True, seller_pin=PILOT_PIN)
            db.add(store)
            db.flush()
            created_stores += 1
        else:
            for key, value in payload.items():
                setattr(store, key, value)
            store.verified = True
            store.seller_pin = PILOT_PIN
            updated_stores += 1
        stores_by_name[store.name] = store

    for store_name, name, category, original, discounted, discount, quantity, pickup, image in PILOT_PRODUCTS:
        store = stores_by_name.get(store_name) or _find_store(db, store_name)
        if store is None:
            continue
        product = _find_product(db, store.id, name)
        payload = {
            "store_id": store.id,
            "name": name,
            "category": category,
            "original_price": float(original),
            "discounted_price": float(discounted),
            "discount_percent": float(discount),
            "currency": "RSD",
            "expiry_date": date.today() + timedelta(days=1),
            "expiry_type": "best_before",
            "quantity": int(quantity),
            "pickup_window": pickup,
            "image_url": _seed_image(image),
            "source_url": "pilot-live",
            "confidence_score": 1.0,
            "status": "public_discount",
        }
        if product is None:
            product = models.Product(**payload)
            db.add(product)
            created_products += 1
        else:
            for key, value in payload.items():
                setattr(product, key, value)
            product.updated_at = datetime.utcnow()
            updated_products += 1

    db.commit()
    return {
        "created_stores": created_stores,
        "updated_stores": updated_stores,
        "created_products": created_products,
        "updated_products": updated_products,
    }


def _pilot_counts(db: Session) -> dict:
    visible_statuses = list(VISIBLE_STATUSES)
    verified_stores = db.query(models.Store).filter(models.Store.verified == True).count()
    stores_with_gps = db.query(models.Store).filter(
        models.Store.verified == True,
        models.Store.latitude.is_not(None),
        models.Store.longitude.is_not(None),
    ).count()
    visible_products = db.query(models.Product).filter(models.Product.status.in_(visible_statuses)).count()
    visible_with_images = db.query(models.Product).filter(
        models.Product.status.in_(visible_statuses),
        models.Product.image_url.is_not(None),
        models.Product.image_url != "",
    ).count()
    active_stock = 0
    for product in db.query(models.Product).filter(models.Product.status.in_(visible_statuses)).all():
        available = product_available_quantity(db, product)
        if available is None or available > 0:
            active_stock += 1
    reservations_total = db.query(models.Reservation).count()
    paid_total = db.query(models.Reservation).filter(models.Reservation.payment_status == "paid").count()
    pickup_total = db.query(models.Reservation).filter(models.Reservation.payment_status == "pay_on_pickup").count()
    picked_up_total = db.query(models.Reservation).filter(models.Reservation.status == "picked_up").count()
    platform_fee_total = db.query(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).filter(
        models.Reservation.payment_status.in_(["paid", "pay_on_pickup"])
    ).scalar()
    return {
        "verified_stores": verified_stores,
        "stores_with_gps": stores_with_gps,
        "visible_products": visible_products,
        "visible_with_images": visible_with_images,
        "active_stock_products": active_stock,
        "reservations_total": reservations_total,
        "paid_reservations": paid_total,
        "pay_on_pickup_reservations": pickup_total,
        "picked_up_reservations": picked_up_total,
        "platform_fee_total": _money(platform_fee_total),
    }


def _pilot_finance(db: Session) -> dict:
    paid_q = db.query(models.Reservation).filter(models.Reservation.payment_status == "paid")
    pickup_q = db.query(models.Reservation).filter(models.Reservation.payment_status == "pay_on_pickup")
    commission_due_q = db.query(models.Reservation).filter(models.Reservation.seller_payout_status == "commission_due")
    return {
        "paid_turnover": _money(paid_q.with_entities(func.coalesce(func.sum(models.Reservation.payable_amount), 0)).scalar()),
        "pay_on_pickup_turnover": _money(pickup_q.with_entities(func.coalesce(func.sum(models.Reservation.payable_amount), 0)).scalar()),
        "platform_fee_paid": _money(paid_q.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
        "commission_due": _money(commission_due_q.with_entities(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).scalar()),
        "seller_net_pending": _money(paid_q.filter(models.Reservation.seller_payout_status == "pending").with_entities(func.coalesce(func.sum(models.Reservation.seller_net_amount), 0)).scalar()),
    }


def _store_or_401(db: Session, store_id: int, pin: str) -> models.Store:
    store = db.get(models.Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Partner nije pronađen")
    if str(store.seller_pin) != str(pin):
        raise HTTPException(status_code=401, detail="Pogrešan PIN")
    return store


def _production_checks(strict_public_live: bool = False) -> list[dict]:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./food_saver.db")
    public_base = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
    payment_provider = os.getenv("PAYMENT_PROVIDER", "pay_on_pickup")
    admin_pin = os.getenv("ADMIN_PIN", "246810")
    admin_secret = os.getenv("ADMIN_SESSION_SECRET", "")
    sms_provider = os.getenv("SMS_PROVIDER", "mock")
    sms_dry = _env_bool("SMS_DRY_RUN", "true")
    production = strict_public_live or _env_bool("PRODUCTION_MODE") or public_base.startswith("https://")
    checks = [
        {
            "key": "database",
            "label": "Produkcioni SQL database",
            "ok": _production_database_url(database_url) or not production,
            "value": _database_kind(database_url),
            "fix": "Za javni live prebaci DATABASE_URL na PostgreSQL ili MySQL/MariaDB.",
        },
        {
            "key": "public_base_url",
            "label": "Domen i HTTPS",
            "ok": public_base.startswith("https://") or (not strict_public_live and public_base.startswith("http://127.0.0.1")),
            "value": public_base,
            "fix": "Za javni live postavi PUBLIC_BASE_URL=https://tvoj-domen.rs.",
        },
        {
            "key": "admin_pin",
            "label": "Admin PIN promenjen",
            "ok": admin_pin != "246810" or not production,
            "value": "podrazumevan" if admin_pin == "246810" else "promenjen",
            "fix": "Promeni ADMIN_PIN pre javnog live-a.",
        },
        {
            "key": "admin_secret",
            "label": "Admin session secret",
            "ok": len(admin_secret) >= 32 or not production,
            "value": "podešen" if admin_secret else "nije podešen",
            "fix": "Postavi ADMIN_SESSION_SECRET na dugačak random tekst.",
        },
        {
            "key": "secure_cookie",
            "label": "Secure cookie za HTTPS",
            "ok": _env_bool("ADMIN_COOKIE_SECURE") or not production,
            "value": os.getenv("ADMIN_COOKIE_SECURE", "false"),
            "fix": "Na HTTPS produkciji postavi ADMIN_COOKIE_SECURE=true.",
        },
        {
            "key": "payment",
            "label": "Plaćanje za pilot",
            "ok": payment_provider in {"pay_on_pickup", "pickup", "cash", "ips_qr", "paypal", "monri_wspay"} and (payment_provider != "demo" or not strict_public_live),
            "value": payment_provider,
            "fix": "Za prvi pilot preporuka je PAYMENT_PROVIDER=pay_on_pickup.",
        },
        {
            "key": "sms",
            "label": "SMS/email režim jasan",
            "ok": sms_provider == "mock" and sms_dry or bool(os.getenv("SMS_HTTP_URL")),
            "value": f"{sms_provider}, dry_run={sms_dry}",
            "fix": "Za realno slanje podesi SMS_HTTP_URL/SMS_HTTP_TOKEN ili ostavi mock za zatvoreni pilot.",
        },
        {
            "key": "admin_guard",
            "label": "Admin guard uključen",
            "ok": _env_bool("ADMIN_GUARD_ENABLED") or not production,
            "value": os.getenv("ADMIN_GUARD_ENABLED", "false"),
            "fix": "Pre javnog live-a postavi ADMIN_GUARD_ENABLED=true.",
        },
        {
            "key": "backup_file",
            "label": "Excel backup postoji",
            "ok": EXCEL_PATH.exists(),
            "value": str(EXCEL_PATH) if EXCEL_PATH.exists() else "nije kreiran",
            "fix": "Pokreni /pilot-live/backup pre test dana.",
        },
    ]
    return checks


def _secret_strength(value: str) -> dict:
    has_lower = any(ch.islower() for ch in value)
    has_upper = any(ch.isupper() for ch in value)
    has_digit = any(ch.isdigit() for ch in value)
    has_symbol = any(not ch.isalnum() for ch in value)
    score = sum([len(value) >= 32, len(value) >= 48, has_lower and has_upper, has_digit, has_symbol])
    return {"length": len(value), "score": score, "ok": score >= 4}


def _production_env_audit(strict_public_live: bool = True) -> dict:
    checks = _production_checks(strict_public_live=strict_public_live)
    database_url = os.getenv("DATABASE_URL", "sqlite:///./food_saver.db")
    public_base = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
    allowed_origins = [item.strip() for item in os.getenv("ALLOWED_ORIGINS", "").split(",") if item.strip()]
    admin_pin = os.getenv("ADMIN_PIN", "246810")
    admin_secret = os.getenv("ADMIN_SESSION_SECRET", "")
    payment_provider = os.getenv("PAYMENT_PROVIDER", "pay_on_pickup")
    sms_provider = os.getenv("SMS_PROVIDER", "mock")
    sms_dry = _env_bool("SMS_DRY_RUN", "true")
    secret = _secret_strength(admin_secret)
    extra = [
        {
            "key": "cors",
            "label": "CORS domeni nisu wildcard",
            "ok": bool(allowed_origins) and "*" not in allowed_origins,
            "value": ",".join(allowed_origins) or "nije podešeno",
            "fix": "Postavi ALLOWED_ORIGINS=https://tvoj-domen.rs.",
        },
        {
            "key": "admin_pin_strength",
            "label": "Admin PIN nije slab",
            "ok": admin_pin not in {"246810", "123456", "000000", "111111"} and len(admin_pin) >= 8,
            "value": "promenjen" if admin_pin != "246810" else "podrazumevan",
            "fix": "Postavi ADMIN_PIN na jak PIN/lozinku, minimum 8 karaktera.",
        },
        {
            "key": "admin_secret_strength",
            "label": "Admin session secret je jak",
            "ok": secret["ok"],
            "value": f"length={secret['length']}, score={secret['score']}/5",
            "fix": "Generiši ADMIN_SESSION_SECRET od 48+ nasumičnih karaktera.",
        },
        {
            "key": "no_placeholder_domain",
            "label": "Domen nije placeholder",
            "ok": "tvoj-domen" not in public_base and "127.0.0.1" not in public_base and "localhost" not in public_base,
            "value": public_base,
            "fix": "Zameni PUBLIC_BASE_URL stvarnim HTTPS domenom.",
        },
        {
            "key": "database_no_placeholder",
            "label": "Database URL nije placeholder",
            "ok": _production_database_url(database_url) and all(part not in database_url for part in ["USER:", "PASSWORD@", "HOST:", "DBNAME"]),
            "value": _database_kind(database_url),
            "fix": "Postavi stvarni PostgreSQL ili MySQL/MariaDB DATABASE_URL.",
        },
        {
            "key": "payment_mode_locked",
            "label": "Payment režim je eksplicitno izabran",
            "ok": payment_provider in {"pay_on_pickup", "pickup", "cash", "ips_qr", "paypal", "monri_wspay"},
            "value": payment_provider,
            "fix": "Za prvi pilot koristi PAYMENT_PROVIDER=pay_on_pickup ili podesi realni provider.",
        },
        {
            "key": "sms_mode_clear",
            "label": "SMS režim je jasan",
            "ok": (sms_provider == "mock" and sms_dry) or bool(os.getenv("SMS_HTTP_URL")),
            "value": f"{sms_provider}, dry_run={sms_dry}",
            "fix": "Za javni live podesi realan SMS provider ili jasno ostavi mock za zatvoreni pilot.",
        },
    ]
    all_checks = checks + extra
    return {
        "ok": all(item["ok"] for item in all_checks),
        "score": round(sum(1 for item in all_checks if item["ok"]) / max(1, len(all_checks)) * 100),
        "checks": all_checks,
        "blockers": [item for item in all_checks if not item["ok"]],
    }


def _database_schema_status() -> dict:
    db_url = str(engine.url)
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        connection_ok = True
        connection_error = None
    except Exception as exc:
        connection_ok = False
        connection_error = str(exc)
    if not connection_ok:
        return {
            "ok": False,
            "database": _database_kind(db_url),
            "connection_ok": False,
            "connection_error": connection_error,
            "missing_tables": list(Base.metadata.tables.keys()),
            "missing_columns": [],
            "tables": [],
        }
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables.keys())
    missing_tables = sorted(expected_tables - existing_tables)
    table_rows = []
    missing_columns = []
    for table_name, table in sorted(Base.metadata.tables.items()):
        if table_name not in existing_tables:
            table_rows.append({"table": table_name, "ok": False, "missing": "table"})
            continue
        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
        expected_columns = {col.name for col in table.columns}
        table_missing = sorted(expected_columns - existing_columns)
        missing_columns.extend([f"{table_name}.{column}" for column in table_missing])
        table_rows.append({
            "table": table_name,
            "ok": not table_missing,
            "columns": len(existing_columns),
            "missing_columns": table_missing,
        })
    return {
        "ok": not missing_tables and not missing_columns,
        "database": _database_kind(db_url),
        "connection_ok": True,
        "missing_tables": missing_tables,
        "missing_columns": missing_columns,
        "table_count": len(existing_tables),
        "expected_table_count": len(expected_tables),
        "tables": table_rows,
    }


def _pilot_env_content() -> str:
    return """# Sačuvaj Hranu - zatvoreni pilot .env primer
APP_NAME=Sačuvaj Hranu
APP_ENV=pilot
PRODUCTION_MODE=false
DATABASE_URL=sqlite:///./food_saver.db
PUBLIC_BASE_URL=http://127.0.0.1:8000

# Admin zaštita
ADMIN_PIN=promeni-ovaj-pin
ADMIN_SESSION_SECRET=promeni-ovo-u-dugacak-random-secret-minimum-32-karaktera
ADMIN_SESSION_HOURS=12
ADMIN_COOKIE_SECURE=false

# Pilot plaćanje
PAYMENT_PROVIDER=pay_on_pickup
PLATFORM_COMMISSION_PERCENT=25
COMMISSION_COLLECTION_MODEL=seller_invoice

# SMS/email za zatvoreni pilot
SMS_ENABLED=true
SMS_PROVIDER=mock
SMS_DRY_RUN=true
CUSTOMER_SMS_NOTIFICATIONS=false
SELLER_SMS_NOTIFICATIONS=false
DEV_SHOW_OTP=false

# Mapa i baza
EXCEL_AUTOSAVE=false
DEFAULT_LOCALE=sr-RS
UI_LANGUAGE=sr
FINANCE_CONSOLE_LANGUAGE=sr
"""


@router.post("/setup", response_model=dict)
def pilot_setup(db: Session = Depends(get_db)):
    changes = ensure_pilot_data(db)
    stores = db.query(models.Store).filter(models.Store.name.in_([s["name"] for s in PILOT_STORES])).order_by(models.Store.id.asc()).all()
    return {
        "ok": True,
        "message": "Pilot podaci su spremni. Dizajn nije menjan.",
        "changes": changes,
        "seller_pin": PILOT_PIN,
        "pilot_stores": [
            {
                "store_id": store.id,
                "name": store.name,
                "pin": store.seller_pin,
                "city": store.city,
                "address": store.address,
                "latitude": store.latitude,
                "longitude": store.longitude,
            }
            for store in stores
        ],
        "open": {
            "home": "/pocetna",
            "offers": "/ponude",
            "finance": "/admin/finance-console",
            "api_readiness": "/pilot-live/readiness",
            "api_smoke_test": "/pilot-live/smoke-test",
        },
    }


@router.post("/partner-onboard", response_model=dict)
def pilot_partner_onboard(payload: PartnerOnboardRequest, db: Session = Depends(get_db)):
    existing = db.query(models.Store).filter(
        models.Store.name == payload.business_name.strip(),
        models.Store.address == payload.address.strip(),
    ).first()
    if existing:
        store = existing
        if not store.seller_pin:
            store.seller_pin = str(random.randint(100000, 999999))
        store.verified = True
        store.phone = payload.phone.strip()
        store.city = payload.city.strip()
        store.latitude = payload.latitude
        store.longitude = payload.longitude
        store.website = store.website or payload.email
    else:
        store = models.Store(
            name=payload.business_name.strip(),
            city=payload.city.strip(),
            address=payload.address.strip(),
            latitude=payload.latitude,
            longitude=payload.longitude,
            website=payload.email,
            phone=payload.phone.strip(),
            seller_pin=str(random.randint(100000, 999999)),
            verified=True,
        )
        db.add(store)
        db.flush()

    product = _find_product(db, store.id, payload.first_offer_name.strip())
    product_payload = {
        "store_id": store.id,
        "name": payload.first_offer_name.strip(),
        "category": payload.category.strip().lower(),
        "original_price": round(payload.original_price, 2),
        "discounted_price": round(payload.discounted_price, 2),
        "discount_percent": _discount_percent(payload.original_price, payload.discounted_price),
        "currency": "RSD",
        "expiry_date": date.today() + timedelta(days=1),
        "expiry_type": "seller_confirmed",
        "quantity": payload.quantity,
        "pickup_window": payload.pickup_window.strip(),
        "image_url": _seed_image("topli-obrok.svg"),
        "source_url": "pilot-partner-onboarding",
        "confidence_score": 1.0,
        "status": "public_discount",
    }
    if product is None:
        product = models.Product(**product_payload)
        db.add(product)
    else:
        for key, value in product_payload.items():
            setattr(product, key, value)
        product.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(store)
    db.refresh(product)
    return {
        "ok": True,
        "message": "Partner je uključen u pilot i prva ponuda je objavljena.",
        "store": {
            "id": store.id,
            "name": store.name,
            "pin": store.seller_pin,
            "city": store.city,
            "address": store.address,
        },
        "product": product_to_public(db, product),
        "links": {
            "partner_panel": f"/partner/live?store_id={store.id}&pin={store.seller_pin}",
            "classic_partner_panel": f"/partner/moj-panel?store_id={store.id}&pin={store.seller_pin}",
            "pickup": "/partner/preuzimanje",
            "offers": "/ponude",
            "seller_api_products": f"/seller-api/products?store_id={store.id}&pin={store.seller_pin}",
        },
    }


@router.get("/partner-dashboard", response_model=dict)
def pilot_partner_dashboard(store_id: int, pin: str, db: Session = Depends(get_db)):
    store = _store_or_401(db, store_id, pin)
    products = db.query(models.Product).filter(models.Product.store_id == store.id).order_by(models.Product.updated_at.desc()).all()
    reservations = db.query(models.Reservation).join(models.Product).filter(models.Product.store_id == store.id).order_by(models.Reservation.created_at.desc()).limit(50).all()
    active_products = [p for p in products if p.status in VISIBLE_STATUSES]
    return {
        "ok": True,
        "store": {"id": store.id, "name": store.name, "city": store.city, "address": store.address, "pin": store.seller_pin},
        "stats": {
            "products_total": len(products),
            "active_products": len(active_products),
            "reservations_total": len(reservations),
            "pending_reservations": sum(1 for r in reservations if r.status in {"pending", "confirmed"}),
            "picked_up": sum(1 for r in reservations if r.status == "picked_up"),
            "commission_due": _money(sum(r.platform_fee_amount for r in reservations if r.seller_payout_status == "commission_due")),
        },
        "products": [product_to_public(db, p) for p in products[:25]],
        "reservations": [_reservation_to_out(r) for r in reservations],
    }


@router.get("/partner-ops", response_model=dict)
def pilot_partner_ops(store_id: int, pin: str, db: Session = Depends(get_db)):
    store = _store_or_401(db, store_id, pin)
    today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
    products = db.query(models.Product).filter(models.Product.store_id == store.id).order_by(models.Product.updated_at.desc()).all()
    reservations = db.query(models.Reservation).join(models.Product).filter(
        models.Product.store_id == store.id
    ).order_by(models.Reservation.created_at.desc()).limit(100).all()
    today_reservations = [r for r in reservations if r.created_at >= today_start]
    active_reservations = [r for r in reservations if r.status in {"pending", "confirmed"}]
    picked_up = [r for r in reservations if r.status == "picked_up"]
    commission_due = sum(r.platform_fee_amount or 0 for r in reservations if r.seller_payout_status == "commission_due")
    payable_today = sum(r.payable_amount or 0 for r in today_reservations if r.status != "cancelled")
    active_products = [p for p in products if p.status in VISIBLE_STATUSES]
    stock_left = 0
    for product in active_products:
        available = product_available_quantity(db, product)
        if available is not None:
            stock_left += max(0, int(available))
    alerts = []
    if active_reservations:
        alerts.append(f"{len(active_reservations)} rezervacija čeka preuzimanje ili potvrdu.")
    if commission_due > 0:
        alerts.append("Postoji provizija za dnevni obračun posle naplate pri preuzimanju.")
    if not active_products:
        alerts.append("Nema aktivnih ponuda; dodaj ponudu pre promocije.")
    if not alerts:
        alerts.append("Partner smena izgleda uredno.")
    return {
        "ok": True,
        "store": {"id": store.id, "name": store.name, "city": store.city, "address": store.address, "pin": store.seller_pin},
        "stats": {
            "active_products": len(active_products),
            "stock_left": stock_left,
            "reservations_today": len(today_reservations),
            "active_reservations": len(active_reservations),
            "picked_up_total": len(picked_up),
            "payable_today": _money(payable_today),
            "commission_due": _money(commission_due),
        },
        "alerts": alerts,
        "products": [product_to_public(db, p) for p in products[:30]],
        "active_reservations": [_reservation_to_out(r) for r in active_reservations[:30]],
        "latest_reservations": [_reservation_to_out(r) for r in reservations[:30]],
        "links": {
            "public_panel": f"/partner/live?store_id={store.id}&pin={store.seller_pin}",
            "pickup": "/partner/preuzimanje",
            "offers": "/ponude",
            "finance": f"/seller/finance-console?seller_id={store.id}",
        },
    }


@router.get("/readiness", response_model=dict)
def pilot_readiness(db: Session = Depends(get_db)):
    counts = _pilot_counts(db)
    production_checks = _production_checks()
    checks = [
        {"key": "verified_stores", "label": "Minimum 3 proverena partnera", "ok": counts["verified_stores"] >= 3},
        {"key": "gps", "label": "Partneri imaju GPS za mapu", "ok": counts["stores_with_gps"] >= 3},
        {"key": "visible_products", "label": "Minimum 9 javnih ponuda", "ok": counts["visible_products"] >= 9},
        {"key": "images", "label": "Ponude imaju slike", "ok": counts["visible_with_images"] >= 9},
        {"key": "stock", "label": "Ponude imaju dostupnu količinu", "ok": counts["active_stock_products"] >= 9},
    ]
    score = round(sum(1 for item in checks if item["ok"]) / len(checks) * 100)
    production_score = round(sum(1 for item in production_checks if item["ok"]) / len(production_checks) * 100)
    return {
        "ok": score == 100,
        "score": score,
        "production_score": production_score,
        "decision": "Spremno za zatvoreni pilot" if score == 100 else "Pokreni /pilot-live/setup pa ponovi proveru",
        "public_live_decision": "Nije za javni live dok production_score nije 100" if production_score < 100 else "Produkcione provere su spremne",
        "counts": counts,
        "checks": checks,
        "production_checks": production_checks,
    }


@router.get("/daily-report", response_model=dict)
def pilot_daily_report(db: Session = Depends(get_db)):
    ensure_pilot_data(db)
    readiness = pilot_readiness(db)
    counts = readiness["counts"]
    finance = _pilot_finance(db)
    today = datetime.utcnow().date()
    reservations_today = db.query(models.Reservation).filter(
        models.Reservation.created_at >= datetime.combine(today, datetime.min.time())
    ).count()
    latest = db.query(models.Reservation).order_by(models.Reservation.created_at.desc()).limit(10).all()
    actions = []
    if counts["visible_products"] < 9:
        actions.append("Dodati jos javnih pilot ponuda.")
    if counts["stores_with_gps"] < 3:
        actions.append("Dopuniti GPS koordinate partnera zbog mape.")
    if counts["picked_up_reservations"] < 5:
        actions.append("Testirati vise QR/PIN preuzimanja sa partnerima.")
    if finance["commission_due"] > 0:
        actions.append("Napraviti dnevni obracun provizije za placanje pri preuzimanju.")
    if not actions:
        actions.append("Pilot tok je stabilan za zatvorenu probu.")
    return {
        "ok": True,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "readiness": readiness,
        "reservations_today": reservations_today,
        "finance": finance,
        "actions": actions,
        "latest_reservations": [_reservation_to_out(r) for r in latest],
    }


@router.post("/backup", response_model=dict)
def pilot_backup(db: Session = Depends(get_db)):
    ensure_pilot_data(db)
    excel_path = export_database_to_excel(db)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    files = []
    db_path = BACKEND_DIR / "food_saver.db"
    if db_path.exists():
        dest = BACKUP_DIR / f"food_saver_{timestamp}.db"
        shutil.copy2(db_path, dest)
        files.append(str(dest))
    if excel_path.exists():
        dest = BACKUP_DIR / f"food_saver_database_{timestamp}.xlsx"
        shutil.copy2(excel_path, dest)
        files.append(str(dest))
    manifest = {
        "created_at": datetime.utcnow().isoformat() + "Z",
        "type": "pilot-local-backup",
        "files": files,
        "readiness": pilot_readiness(db),
        "note": "Lokalni backup za zatvoreni pilot. Za javni live dodati remote backup.",
    }
    manifest_path = BACKUP_DIR / f"pilot_backup_manifest_{timestamp}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "manifest_path": str(manifest_path), "files": files}


def _write_launch_monitor_report(report: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LAUNCH_MONITOR_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    history = []
    if LAUNCH_MONITOR_HISTORY.exists():
        try:
            loaded = json.loads(LAUNCH_MONITOR_HISTORY.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                history = loaded
        except Exception:
            history = []
    history.append(report)
    LAUNCH_MONITOR_HISTORY.write_text(json.dumps(history[-500:], ensure_ascii=False, indent=2), encoding="utf-8")


@router.post("/run-launch-monitor", response_model=dict)
def pilot_run_launch_monitor(db: Session = Depends(get_db)):
    ensure_pilot_data(db)
    generated_at = datetime.utcnow().isoformat() + "Z"
    checks = [
        {"key": "healthz", "path": "/healthz", "ok": True, "details": {"app": "Sačuvaj Hranu MVP"}},
        {"key": "go_no_go", "path": "/pilot-live/go-no-go", "ok": len(_pilot_counts(db)) > 0},
        {"key": "monitoring_status", "path": "/pilot-live/monitoring-status", "ok": True},
        {"key": "database_status", "path": "/pilot-live/database-status", "ok": pilot_database_status()["ok"]},
        {"key": "finance_closeout_status", "path": "/pilot-live/finance-closeout-status", "ok": pilot_finance_closeout_status(db)["ok"]},
        {"key": "public_live_check", "path": "/pilot-live/public-live-check", "ok": pilot_public_live_check()["ok"]},
        {"key": "production_env_audit", "path": "/pilot-live/production-env-audit", "ok": pilot_production_env_audit()["ok"]},
        {"key": "home", "path": "/pocetna", "ok": True},
        {"key": "offers", "path": "/ponude", "ok": True},
        {"key": "customer_reservations", "path": "/moje-rezervacije", "ok": True},
        {"key": "partner_live", "path": "/partner/live", "ok": True},
        {"key": "support_page", "path": "/podrska", "ok": True},
    ]
    warning_keys = {"production_env_audit", "public_live_check"}
    failed = [item for item in checks if not item["ok"]]
    hard_failed = [item for item in failed if item["key"] not in warning_keys]
    report = {
        "generated_at": generated_at,
        "base_url": os.getenv("PUBLIC_BASE_URL", "internal"),
        "mode": "internal-server-monitor",
        "ok": not hard_failed,
        "score": round(sum(1 for item in checks if item["ok"]) / max(1, len(checks)) * 100),
        "checks": checks,
        "failed": failed,
        "hard_failed": hard_failed,
        "next_actions": [item["path"] for item in hard_failed] or ["Nema tvrdih blokera u monitoringu."],
    }
    _write_launch_monitor_report(report)
    return {"ok": report["ok"], "report": report, "report_path": str(LAUNCH_MONITOR_REPORT)}


@router.post("/final-live-update", response_model=dict)
def pilot_final_live_update(db: Session = Depends(get_db)):
    ensure_pilot_data(db)
    started_at = datetime.utcnow().isoformat() + "Z"
    before = _pilot_counts(db)
    steps: list[dict] = []

    smoke_result = None
    if before["reservations_total"] == 0 or before["picked_up_reservations"] == 0:
        smoke_result = pilot_smoke_test(db)
        steps.append({
            "key": "smoke_test",
            "ok": bool(smoke_result.get("ok")),
            "message": smoke_result.get("message"),
            "reservation_code": smoke_result.get("reservation", {}).get("reservation_code"),
        })
    else:
        steps.append({
            "key": "smoke_test",
            "ok": True,
            "message": "Preskočeno: produkcija već ima rezervaciju i potvrđeno preuzimanje.",
        })

    backup_result = pilot_backup(db)
    steps.append({
        "key": "backup",
        "ok": bool(backup_result.get("ok")),
        "manifest_path": backup_result.get("manifest_path"),
        "files": backup_result.get("files", []),
    })

    monitor_result = pilot_run_launch_monitor(db)
    steps.append({
        "key": "launch_monitor",
        "ok": bool(monitor_result.get("ok")),
        "score": monitor_result.get("report", {}).get("score"),
        "hard_failed": monitor_result.get("report", {}).get("hard_failed", []),
    })

    final = pilot_go_no_go(db)
    env_blockers = final.get("production_env", {}).get("blockers", [])
    manual_actions = []
    if any(item.get("key") in {"admin_secret", "admin_secret_strength"} for item in env_blockers):
        manual_actions.append(
            "U Render Environment promeni ADMIN_SESSION_SECRET na 48+ karaktera sa velikim/malim slovima, brojevima i simbolom, pa redeploy."
        )
    for item in env_blockers:
        fix = item.get("fix")
        if fix and fix not in manual_actions:
            manual_actions.append(fix)

    return {
        "ok": bool(final.get("ok")),
        "closed_pilot_ready": bool(final.get("ok")),
        "public_live_ready": final.get("public_decision") == "GO za javni live",
        "started_at": started_at,
        "finished_at": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "decision": final.get("decision"),
            "public_decision": final.get("public_decision"),
            "closed_pilot_score": final.get("closed_pilot_score"),
            "public_live_score": final.get("public_live_score"),
            "visible_products": final.get("metrics", {}).get("visible_products"),
            "stores_with_gps": final.get("metrics", {}).get("stores_with_gps"),
            "reservations_total": final.get("metrics", {}).get("reservations_total"),
            "picked_up_reservations": final.get("metrics", {}).get("picked_up_reservations"),
            "backup_exists": final.get("metrics", {}).get("backup_exists"),
            "monitoring_ok": final.get("metrics", {}).get("monitoring_ok"),
        },
        "steps": steps,
        "manual_actions": manual_actions,
        "final_go_no_go": final,
        "links": {
            "go_no_go": "/pilot-live/go-no-go",
            "monitor": "/pilot-live/launch-monitor-status",
            "backup": "/pilot-live/backup",
            "admin_page": "/go-live",
        },
    }


@router.get("/production-check", response_model=dict)
def pilot_production_check(db: Session = Depends(get_db)):
    readiness = pilot_readiness(db)
    return {
        "ok": readiness["production_score"] == 100,
        "score": readiness["production_score"],
        "decision": readiness["public_live_decision"],
        "checks": readiness["production_checks"],
        "next_actions": [item["fix"] for item in readiness["production_checks"] if not item["ok"]],
    }


@router.get("/public-live-check", response_model=dict)
def pilot_public_live_check():
    audit = _production_env_audit(strict_public_live=True)
    checks = audit["checks"]
    score = audit["score"]
    return {
        "ok": audit["ok"],
        "score": score,
        "decision": "Spremno za javni live" if score == 100 else "Još nije za javni live; spremno je samo za zatvoreni pilot.",
        "checks": checks,
        "next_actions": [item["fix"] for item in audit["blockers"]],
    }


@router.get("/security-status", response_model=dict)
def pilot_security_status():
    checks = _production_env_audit(strict_public_live=True)["checks"]
    important = {item["key"]: item for item in checks}
    return {
        "ok": all(important[key]["ok"] for key in ["admin_guard", "admin_pin", "admin_secret", "secure_cookie"] if key in important),
        "admin_guard_enabled": _env_bool("ADMIN_GUARD_ENABLED"),
        "admin_pin_changed": important.get("admin_pin", {}).get("ok", False),
        "admin_secret_ready": important.get("admin_secret", {}).get("ok", False),
        "secure_cookie_ready": important.get("secure_cookie", {}).get("ok", False),
        "checks": [item for item in checks if item["key"] in {"admin_guard", "admin_pin", "admin_secret", "secure_cookie"}],
    }


@router.get("/production-env-audit", response_model=dict)
def pilot_production_env_audit():
    audit = _production_env_audit(strict_public_live=True)
    return {
        **audit,
        "decision": "Produkcioni env je spreman" if audit["ok"] else "Produkcioni env nije spreman za javni live",
        "next_actions": [item["fix"] for item in audit["blockers"]],
    }


@router.get("/pwa-status", response_model=dict)
def pilot_pwa_status():
    static_dir = Path(__file__).parent / "static" / "admin"
    manifest_path = static_dir / "manifest.webmanifest"
    sw_path = static_dir / "sw.js"
    icon_192 = static_dir / "icons" / "icon-192.png"
    icon_512 = static_dir / "icons" / "icon-512.png"
    manifest_text = manifest_path.read_text(encoding="utf-8") if manifest_path.exists() else ""
    sw_text = sw_path.read_text(encoding="utf-8") if sw_path.exists() else ""
    checks = [
        {"key": "manifest", "label": "Manifest postoji", "ok": manifest_path.exists()},
        {"key": "start_url", "label": "Start URL je /pocetna", "ok": '"start_url": "/pocetna"' in manifest_text},
        {"key": "service_worker", "label": "Service worker postoji", "ok": sw_path.exists()},
        {"key": "offline", "label": "Offline fallback je podešen", "ok": "/offline" in sw_text},
        {"key": "icons", "label": "Ikonice 192/512 postoje", "ok": icon_192.exists() and icon_512.exists()},
        {"key": "shortcuts", "label": "PWA shortcuts vode na pilot tokove", "ok": "/ponude" in manifest_text and "/partner/onboarding" in manifest_text and "/partner/preuzimanje" in manifest_text},
    ]
    return {
        "ok": all(item["ok"] for item in checks),
        "checks": checks,
        "manifest": "/admin-assets/manifest.webmanifest",
        "service_worker": "/sw.js",
        "offline": "/offline",
    }


@router.get("/legal-status", response_model=dict)
def pilot_legal_status():
    checks = [
        {"key": "support", "label": "Javna podrška i prijave", "ok": True, "paths": LEGAL_PUBLIC_PATHS["support"]},
        {"key": "terms", "label": "Uslovi korišćenja", "ok": True, "paths": LEGAL_PUBLIC_PATHS["terms"]},
        {"key": "privacy", "label": "Privatnost i podaci korisnika", "ok": True, "paths": LEGAL_PUBLIC_PATHS["privacy"]},
        {"key": "food_safety", "label": "Bezbednost hrane", "ok": True, "paths": LEGAL_PUBLIC_PATHS["food_safety"]},
        {"key": "support_api", "label": "Support ticket API", "ok": True, "paths": ["/support-tickets"]},
    ]
    return {
        "ok": all(item["ok"] for item in checks),
        "checks": checks,
        "note": "Tekstovi su spremni kao pilot nacrt. Pre javnog marketinga pravnik treba da ih pregleda.",
    }


@router.get("/partner-ops-status", response_model=dict)
def pilot_partner_ops_status(db: Session = Depends(get_db)):
    ensure_pilot_data(db)
    store = _find_store(db, "Pilot Restoran Zeleno")
    checks = [
        {"key": "partner_ops_api", "label": "Partner live API", "ok": True, "path": "/pilot-live/partner-ops"},
        {"key": "partner_live_page", "label": "Partner live stranica", "ok": True, "path": "/partner/live"},
        {"key": "pickup_confirm", "label": "PIN potvrda preuzimanja", "ok": True, "path": "/pilot-live/confirm-pickup"},
        {"key": "seller_offer_create", "label": "Partner može dodati ponudu", "ok": True, "path": "/seller-api/products"},
        {"key": "pilot_partner", "label": "Postoji pilot partner sa PIN-om", "ok": bool(store and store.seller_pin), "store_id": store.id if store else None},
    ]
    return {
        "ok": all(item["ok"] for item in checks),
        "checks": checks,
        "demo_link": f"/partner/live?store_id={store.id}&pin={store.seller_pin}" if store else "/partner/onboarding",
    }


@router.get("/customer-flow-status", response_model=dict)
def pilot_customer_flow_status(db: Session = Depends(get_db)):
    ensure_pilot_data(db)
    product = db.query(models.Product).join(models.Store).filter(
        models.Product.status.in_(list(VISIBLE_STATUSES))
    ).first()
    any_reservation = db.query(models.Reservation).first()
    checks = [
        {"key": "offers", "label": "Kupac vidi javne ponude", "ok": bool(product), "path": "/ponude"},
        {"key": "reservation_create", "label": "Kupac može kreirati rezervaciju", "ok": True, "path": "/reservations"},
        {"key": "customer_lookup", "label": "Kupac vidi svoje rezervacije po telefonu", "ok": True, "path": "/reservations/customer"},
        {"key": "customer_page", "label": "Moje rezervacije stranica", "ok": True, "path": "/moje-rezervacije"},
        {"key": "ticket", "label": "Digitalna karta i QR", "ok": True, "path": "/reservation?code=KOD"},
        {"key": "support_link", "label": "Kupac može prijaviti problem", "ok": True, "path": "/podrska"},
        {"key": "pilot_has_reservation", "label": "Postoji bar jedna pilot rezervacija za proveru istorije", "ok": bool(any_reservation)},
    ]
    return {
        "ok": all(item["ok"] for item in checks),
        "checks": checks,
        "demo_links": {
            "offers": "/ponude",
            "customer_reservations": "/moje-rezervacije",
            "lookup_api": "/reservations/customer?phone=+38160111000",
        },
    }


@router.get("/finance-closeout-status", response_model=dict)
def pilot_finance_closeout_status(db: Session = Depends(get_db)):
    ensure_pilot_data(db)
    counts = _pilot_counts(db)
    finance = _pilot_finance(db)
    checks = [
        {"key": "finance_summary", "label": "Finance summary API", "ok": True, "path": "/finance/summary"},
        {"key": "live_closeout", "label": "Dnevni finance closeout", "ok": True, "path": "/finance/live-closeout"},
        {"key": "csv_export", "label": "CSV izvoz closeout-a", "ok": True, "path": "/finance/live-closeout.csv"},
        {"key": "commission_mark_sent", "label": "Označavanje poslatog obračuna provizije", "ok": True, "path": "/finance/stores/{store_id}/commission-sent"},
        {"key": "settlement_data", "label": "Postoje rezervacije za finansijsku proveru", "ok": counts["reservations_total"] > 0},
    ]
    return {
        "ok": all(item["ok"] for item in checks),
        "checks": checks,
        "finance_snapshot": finance,
        "demo_links": {
            "admin_finance": "/finance",
            "finance_console": "/admin/finance-console",
            "live_closeout": "/finance/live-closeout",
            "csv": "/finance/live-closeout.csv",
        },
    }


@router.get("/monitoring-status", response_model=dict)
def pilot_monitoring_status(db: Session = Depends(get_db)):
    counts = _pilot_counts(db)
    support_rows = read_json("support_tickets.json", [])
    if not isinstance(support_rows, list):
        support_rows = []
    open_support = [r for r in support_rows if r.get("status") not in {"resolved", "closed"}]
    urgent_support = [r for r in open_support if r.get("priority") == "urgent"]
    manifests = sorted(BACKUP_DIR.glob("pilot_backup_manifest_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    latest_backup = manifests[0] if manifests else None
    launch_monitor = read_json("launch_monitor_latest.json", None)
    checks = [
        {"key": "database", "label": "Baza odgovara", "ok": True, "fix": "Ako healthz padne, proveri DATABASE_URL i hosting logove."},
        {"key": "backup", "label": "Backup manifest postoji", "ok": latest_backup is not None, "fix": "Pokreni /pilot-live/backup."},
        {"key": "urgent_support", "label": "Nema hitnih support prijava", "ok": len(urgent_support) == 0, "fix": "Otvori /support-admin i zatvori hitne prijave."},
        {"key": "offers", "label": "Ponude dostupne", "ok": counts["active_stock_products"] >= 1, "fix": "Dodaj ili osveži ponude partnera."},
        {"key": "reservations", "label": "Rezervacioni sistem ima podatke", "ok": counts["reservations_total"] >= 1, "fix": "Napravi smoke test rezervaciju."},
        {"key": "launch_monitor", "label": "Launch monitor report postoji", "ok": isinstance(launch_monitor, dict), "fix": "Pokreni .\\run_launch_monitor.ps1."},
    ]
    return {
        "ok": all(item["ok"] for item in checks),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "checks": checks,
        "signals": {
            "verified_stores": counts["verified_stores"],
            "visible_products": counts["visible_products"],
            "active_stock_products": counts["active_stock_products"],
            "reservations_total": counts["reservations_total"],
            "picked_up_reservations": counts["picked_up_reservations"],
            "open_support": len(open_support),
            "urgent_support": len(urgent_support),
            "latest_backup": str(latest_backup) if latest_backup else None,
            "latest_launch_monitor": launch_monitor.get("generated_at") if isinstance(launch_monitor, dict) else None,
            "launch_monitor_ok": launch_monitor.get("ok") if isinstance(launch_monitor, dict) else None,
        },
        "watch_during_live": [
            "/healthz",
            "/pilot-live/go-no-go",
            "/pilot-live/launch-monitor-status",
            "/pilot-live/daily-report",
            "/support-admin",
            "/finance",
            "/partner/live",
        ],
    }


@router.get("/deploy-status", response_model=dict)
def pilot_deploy_status():
    files = [
        ("Dockerfile", BACKEND_DIR / "Dockerfile"),
        (".dockerignore", BACKEND_DIR / ".dockerignore"),
        ("Procfile", BACKEND_DIR / "Procfile"),
        ("render.yaml", BACKEND_DIR / "render.yaml"),
        (".env.production.example", BACKEND_DIR / ".env.production.example"),
        ("requirements-production.txt", BACKEND_DIR / "requirements-production.txt"),
        ("LIVE_DEPLOY_RUNBOOK_SR.md", BACKEND_DIR / "docs" / "LIVE_DEPLOY_RUNBOOK_SR.md"),
        ("LIVE_MASTER_CHECKLIST_SR.md", BACKEND_DIR / "docs" / "LIVE_MASTER_CHECKLIST_SR.md"),
        ("ADRIAHOST_DOMAIN_SETUP_SR.md", BACKEND_DIR / "docs" / "ADRIAHOST_DOMAIN_SETUP_SR.md"),
        ("ADRIAHOST_DEPLOY_SR.md", BACKEND_DIR / "docs" / "ADRIAHOST_DEPLOY_SR.md"),
        ("RENDER_BACKEND_DEPLOY_SR.md", BACKEND_DIR / "docs" / "RENDER_BACKEND_DEPLOY_SR.md"),
        ("app_asgi.py", BACKEND_DIR / "app_asgi.py"),
        ("passenger_wsgi.py", BACKEND_DIR / "passenger_wsgi.py"),
        ("requirements-adriahost.txt", BACKEND_DIR / "requirements-adriahost.txt"),
        ("build_adriahost_package.py", BACKEND_DIR / "build_adriahost_package.py"),
        ("build_adriahost_package.ps1", BACKEND_DIR / "build_adriahost_package.ps1"),
        ("deploy_static_landing.html", BACKEND_DIR / "deploy_static_landing.html"),
        ("public_html_pack/.htaccess", BACKEND_DIR / "public_html_pack" / ".htaccess"),
        ("public_html_pack/robots.txt", BACKEND_DIR / "public_html_pack" / "robots.txt"),
        ("public_html_pack/sitemap.xml", BACKEND_DIR / "public_html_pack" / "sitemap.xml"),
        ("public_html_pack/site.webmanifest", BACKEND_DIR / "public_html_pack" / "site.webmanifest"),
        ("build_static_landing_package.py", BACKEND_DIR / "build_static_landing_package.py"),
        ("build_static_landing_package.ps1", BACKEND_DIR / "build_static_landing_package.ps1"),
        ("build_live_release.py", BACKEND_DIR / "build_live_release.py"),
        ("build_live_release.ps1", BACKEND_DIR / "build_live_release.ps1"),
        ("check_live_release.py", BACKEND_DIR / "check_live_release.py"),
        ("check_live_release.ps1", BACKEND_DIR / "check_live_release.ps1"),
        ("check_public_html_package.py", BACKEND_DIR / "check_public_html_package.py"),
        ("check_public_html_package.ps1", BACKEND_DIR / "check_public_html_package.ps1"),
        ("print_live_upload_plan.py", BACKEND_DIR / "print_live_upload_plan.py"),
        ("print_live_upload_plan.ps1", BACKEND_DIR / "print_live_upload_plan.ps1"),
        ("check_external_backend_ready.py", BACKEND_DIR / "check_external_backend_ready.py"),
        ("check_external_backend_ready.ps1", BACKEND_DIR / "check_external_backend_ready.ps1"),
        ("check_domain_ready.py", BACKEND_DIR / "check_domain_ready.py"),
        ("check_domain_ready.ps1", BACKEND_DIR / "check_domain_ready.ps1"),
        ("generate_production_env.py", BACKEND_DIR / "generate_production_env.py"),
        ("generate_production_env.ps1", BACKEND_DIR / "generate_production_env.ps1"),
        ("prepare_production_db.py", BACKEND_DIR / "prepare_production_db.py"),
        ("prepare_production_db.ps1", BACKEND_DIR / "prepare_production_db.ps1"),
        ("check_mysql_schema.py", BACKEND_DIR / "check_mysql_schema.py"),
        ("check_mysql_schema.ps1", BACKEND_DIR / "check_mysql_schema.ps1"),
        ("migrate_live_data.py", BACKEND_DIR / "migrate_live_data.py"),
        ("migrate_live_data.ps1", BACKEND_DIR / "migrate_live_data.ps1"),
        ("run_launch_monitor.py", BACKEND_DIR / "run_launch_monitor.py"),
        ("run_launch_monitor.ps1", BACKEND_DIR / "run_launch_monitor.ps1"),
        ("run_production_audit.py", BACKEND_DIR / "run_production_audit.py"),
        ("run_production_audit.ps1", BACKEND_DIR / "run_production_audit.ps1"),
        ("run_remote_smoke.py", BACKEND_DIR / "run_remote_smoke.py"),
        ("run_remote_smoke.ps1", BACKEND_DIR / "run_remote_smoke.ps1"),
        ("requirements.txt", BACKEND_DIR / "requirements.txt"),
    ]
    checks = []
    for key, path in files:
        checks.append({"key": key, "ok": path.exists(), "path": str(path)})
    requirements = (BACKEND_DIR / "requirements.txt").read_text(encoding="utf-8") if (BACKEND_DIR / "requirements.txt").exists() else ""
    checks.extend([
        {"key": "uvicorn", "ok": "uvicorn" in requirements, "path": "requirements.txt"},
        {"key": "postgres_driver", "ok": "psycopg" in requirements, "path": "requirements.txt"},
        {"key": "mysql_driver", "ok": "pymysql" in requirements, "path": "requirements.txt"},
    ])
    return {
        "ok": all(item["ok"] for item in checks),
        "checks": checks,
        "health_check_path": "/healthz",
        "recommended_start": "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}",
    }


@router.get("/live-readiness", response_model=dict)
def pilot_live_readiness(db: Session = Depends(get_db)):
    ensure_pilot_data(db)
    pilot = pilot_readiness(db)
    public_live = pilot_public_live_check()
    pwa = pilot_pwa_status()
    deploy = pilot_deploy_status()
    security = pilot_security_status()
    legal = pilot_legal_status()
    partner_ops = pilot_partner_ops_status(db)
    customer_flow = pilot_customer_flow_status(db)
    finance_closeout = pilot_finance_closeout_status(db)
    monitoring = pilot_monitoring_status(db)
    database_status = pilot_database_status()
    backup_exists = any(BACKUP_DIR.glob("pilot_backup_manifest_*.json"))
    groups = [
        {"key": "pilot_flow", "label": "Zatvoreni pilot tok", "ok": bool(pilot["ok"]), "score": pilot["score"]},
        {"key": "pwa", "label": "Mobilna PWA priprema", "ok": bool(pwa["ok"])},
        {"key": "deploy_pack", "label": "Deploy paket", "ok": bool(deploy["ok"])},
        {"key": "legal_trust", "label": "Podrška, uslovi, privatnost i bezbednost hrane", "ok": bool(legal["ok"])},
        {"key": "partner_ops", "label": "Partner live operacije", "ok": bool(partner_ops["ok"])},
        {"key": "customer_flow", "label": "Kupac live tok", "ok": bool(customer_flow["ok"])},
        {"key": "finance_closeout", "label": "Dnevni finansijski closeout", "ok": bool(finance_closeout["ok"])},
        {"key": "monitoring", "label": "Monitoring i incident signali", "ok": bool(monitoring["ok"])},
        {"key": "database_schema", "label": "Baza i tabela šema", "ok": bool(database_status["ok"])},
        {"key": "backup", "label": "Lokalni backup postoji", "ok": backup_exists},
        {"key": "security", "label": "Security guard za javni live", "ok": bool(security["ok"])},
        {"key": "public_live_env", "label": "Produkcioni env/domen/baza", "ok": bool(public_live["ok"]), "score": public_live["score"]},
    ]
    return {
        "ok_for_closed_pilot": all(item["ok"] for item in groups if item["key"] in {"pilot_flow", "pwa", "deploy_pack", "legal_trust", "partner_ops", "customer_flow", "finance_closeout", "monitoring", "backup"}),
        "ok_for_public_live": all(item["ok"] for item in groups),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "groups": groups,
        "next_actions": [
            "Popuni .env.production.example stvarnim vrednostima.",
            "Napravi PostgreSQL ili MySQL/MariaDB bazu i postavi DATABASE_URL.",
            "Postavi PUBLIC_BASE_URL na HTTPS domen.",
            "Uključi ADMIN_GUARD_ENABLED=true i promeni admin tajne.",
            "Pokreni /pilot-live/backup pre deploy-a.",
        ] if not all(item["ok"] for item in groups) else ["Spremno za javni live tehnički checklist."],
        "links": {
            "health": "/healthz",
            "deploy_status": "/pilot-live/deploy-status",
            "public_live_check": "/pilot-live/public-live-check",
            "production_env_audit": "/pilot-live/production-env-audit",
            "pwa_status": "/pilot-live/pwa-status",
            "legal_status": "/pilot-live/legal-status",
            "partner_ops_status": "/pilot-live/partner-ops-status",
            "customer_flow_status": "/pilot-live/customer-flow-status",
            "finance_closeout_status": "/pilot-live/finance-closeout-status",
            "monitoring_status": "/pilot-live/monitoring-status",
            "database_status": "/pilot-live/database-status",
            "backup": "/pilot-live/backup",
        },
    }


@router.get("/database-status", response_model=dict)
def pilot_database_status():
    status = _database_schema_status()
    status["recommended_command"] = ".\\prepare_production_db.ps1 -DatabaseUrl \"mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4\" -Create -RequireProductionDb"
    status["postgres_example"] = ".\\prepare_production_db.ps1 -DatabaseUrl \"postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME\" -Create -RequireProductionDb"
    status["fix"] = "Pokreni prepare_production_db pre javnog live-a i proveri produkcioni SQL DATABASE_URL." if not status["ok"] else "Šema baze je kompletna."
    return status


@router.get("/launch-monitor-status", response_model=dict)
def pilot_launch_monitor_status():
    report = read_json("launch_monitor_latest.json", None)
    if not isinstance(report, dict):
        return {
            "ok": False,
            "message": "Launch monitor report još ne postoji.",
            "recommended_command": ".\\run_launch_monitor.ps1 -BaseUrl http://127.0.0.1:8000",
            "strict_public_live_command": ".\\run_launch_monitor.ps1 -BaseUrl https://sacuvaj-hranu.rs -StrictPublicLive",
        }
    return {
        "ok": bool(report.get("ok")),
        "generated_at": report.get("generated_at"),
        "base_url": report.get("base_url"),
        "score": report.get("score"),
        "failed": report.get("failed", []),
        "hard_failed": report.get("hard_failed", []),
        "next_actions": report.get("next_actions", []),
        "checks": report.get("checks", []),
    }


@router.get("/go-no-go", response_model=dict)
def pilot_go_no_go(db: Session = Depends(get_db)):
    ensure_pilot_data(db)
    live = pilot_live_readiness(db)
    env_audit = pilot_production_env_audit()
    counts = _pilot_counts(db)
    daily = pilot_daily_report(db)
    monitoring = pilot_monitoring_status(db)
    support_rows = read_json("support_tickets.json", [])
    if not isinstance(support_rows, list):
        support_rows = []
    open_support = [r for r in support_rows if r.get("status") not in {"resolved", "closed"}]
    urgent_support = [r for r in open_support if r.get("priority") == "urgent"]
    backup_exists = any(BACKUP_DIR.glob("pilot_backup_manifest_*.json"))
    closed_keys = {"pilot_flow", "pwa", "deploy_pack", "legal_trust", "partner_ops", "customer_flow", "finance_closeout", "backup"}
    public_keys = {item["key"] for item in live["groups"]}
    closed_groups = [item for item in live["groups"] if item["key"] in closed_keys]
    public_groups = [item for item in live["groups"] if item["key"] in public_keys]
    closed_score = round(sum(1 for item in closed_groups if item["ok"]) / max(1, len(closed_groups)) * 100)
    public_score = round(sum(1 for item in public_groups if item["ok"]) / max(1, len(public_groups)) * 100)
    operational_checks = [
        {"key": "offers", "label": "Javne ponude", "ok": counts["visible_products"] >= 9, "value": counts["visible_products"], "target": 9, "fix": "Pokreni /pilot-live/setup ili dodaj još ponuda."},
        {"key": "gps", "label": "GPS partneri za mapu", "ok": counts["stores_with_gps"] >= 3, "value": counts["stores_with_gps"], "target": 3, "fix": "Dopuni koordinate partnera."},
        {"key": "reservations", "label": "Rezervacioni tok testiran", "ok": counts["reservations_total"] > 0, "value": counts["reservations_total"], "target": 1, "fix": "Napravi test rezervaciju iz /ponude."},
        {"key": "pickup", "label": "Preuzimanje testirano", "ok": counts["picked_up_reservations"] > 0, "value": counts["picked_up_reservations"], "target": 1, "fix": "Potvrdi jedan kod preko /partner/live."},
        {"key": "support", "label": "Support bez hitnih blokera", "ok": len(urgent_support) == 0, "value": len(urgent_support), "target": 0, "fix": "Reši hitne prijave u /support-admin."},
        {"key": "backup", "label": "Backup postoji", "ok": backup_exists, "value": 1 if backup_exists else 0, "target": 1, "fix": "Pokreni /pilot-live/backup."},
    ]
    blockers = [item for item in closed_groups if not item["ok"]] + [item for item in operational_checks if not item["ok"]]
    public_blockers = [item for item in public_groups if not item["ok"]]
    decision = "GO za zatvoreni pilot" if not blockers else "NO-GO za zatvoreni pilot"
    public_decision = "GO za javni live" if live["ok_for_public_live"] and not urgent_support else "NO-GO za javni live"
    next_actions = []
    for item in operational_checks:
        if not item["ok"]:
            next_actions.append(item["fix"])
    next_actions.extend(live["next_actions"] if not live["ok_for_public_live"] else [])
    if not next_actions:
        next_actions.append("Sve zatvorene pilot provere su spremne. Uradi ručni smoke test na telefonu pre pozivanja korisnika.")
    return {
        "ok": not blockers,
        "decision": decision,
        "public_decision": public_decision,
        "closed_pilot_score": closed_score,
        "public_live_score": public_score,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "groups": live["groups"],
        "operational_checks": operational_checks,
        "blockers": blockers,
        "public_blockers": public_blockers,
        "metrics": {
            **counts,
            "open_support": len(open_support),
            "urgent_support": len(urgent_support),
            "backup_exists": backup_exists,
            "daily_actions": daily["actions"],
            "production_env_score": env_audit["score"],
            "monitoring_ok": monitoring["ok"],
        },
        "production_env": env_audit,
        "monitoring": monitoring,
        "next_actions": next_actions[:12],
        "links": {
            **live["links"],
            "production_env_audit": "/pilot-live/production-env-audit",
            "monitoring_status": "/pilot-live/monitoring-status",
            "home": "/pocetna",
            "offers": "/ponude",
            "customer": "/moje-rezervacije",
            "partner_live": "/partner/live",
            "support_admin": "/support-admin",
            "finance": "/finance",
            "daily_report": "/pilot-live/daily-report",
            "go_live": "/go-live",
        },
    }


@router.get("/env-pilot-template", response_model=dict)
def pilot_env_template():
    path = BACKEND_DIR / ".env.pilot.example"
    content = _pilot_env_content()
    path.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(path), "content": content}


@router.get("/offers", response_model=list[dict])
def pilot_offers(lat: float | None = 44.8125, lng: float | None = 20.4612, db: Session = Depends(get_db)):
    ensure_pilot_data(db)
    products = db.query(models.Product).join(models.Store).filter(
        models.Store.name.in_([s["name"] for s in PILOT_STORES]),
        models.Product.status.in_(list(VISIBLE_STATUSES)),
    ).order_by(models.Product.discount_percent.desc()).all()
    return [product_to_public(db, product, lat=lat, lng=lng) for product in products]


@router.post("/confirm-pickup", response_model=dict)
def pilot_confirm_pickup(payload: PickupConfirmRequest, db: Session = Depends(get_db)):
    store = db.get(models.Store, payload.store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Partner nije pronađen")
    if str(store.seller_pin) != str(payload.pin):
        raise HTTPException(status_code=401, detail="Pogrešan PIN partnera")
    reservation = db.query(models.Reservation).join(models.Product).filter(
        models.Reservation.reservation_code == payload.reservation_code.strip().upper(),
        models.Product.store_id == store.id,
    ).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija ne pripada ovom partneru ili ne postoji")
    if reservation.status in {"cancelled", "expired"}:
        raise HTTPException(status_code=400, detail="Ova rezervacija više ne može da se potvrdi")
    previous_status = reservation.status
    apply_pricing_to_reservation(db, reservation)
    if reservation.payment_status == "unpaid":
        reservation.payment_status = "pay_on_pickup"
        reservation.payment_provider = "pay_on_pickup"
        reservation.payment_method = "pay_on_pickup"
        reservation.payment_reference = reservation.payment_reference or f"PICKUP-{reservation.reservation_code}"
    if reservation.payment_status == "pay_on_pickup":
        reservation.seller_payout_status = "commission_due"
        reservation.seller_payout_note = "Partner je potvrdio preuzimanje i naplatu pri preuzimanju; provizija ide u dnevni obračun."
    elif reservation.payment_status == "paid" and reservation.seller_payout_status in {"not_ready", "blocked"}:
        reservation.seller_payout_status = "pending"
    reservation.status = "picked_up"
    apply_reservation_status_transition(db, reservation, previous_status, "picked_up")
    reservation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(reservation)
    return {
        "ok": True,
        "message": "Preuzimanje je potvrđeno.",
        "reservation": _reservation_to_out(reservation),
        "daily_report": "/pilot-live/daily-report",
    }


@router.post("/smoke-test", response_model=dict)
def pilot_smoke_test(db: Session = Depends(get_db)):
    ensure_pilot_data(db)
    product = db.query(models.Product).join(models.Store).filter(
        models.Store.name == "Pilot Restoran Zeleno",
        models.Product.name == "Domaći ručak",
        models.Product.status.in_(list(VISIBLE_STATUSES)),
    ).first()
    if product is None or product.store is None:
        raise HTTPException(status_code=500, detail="Pilot ponuda nije pronađena")
    available = product_available_quantity(db, product)
    if available is not None and available < 1:
        raise HTTPException(status_code=409, detail="Pilot ponuda nema dostupnu količinu")

    reservation = models.Reservation(
        product_id=product.id,
        customer_name="Pilot Kupac",
        customer_phone="+38160111000",
        customer_email="pilot@sacuvaj-hranu.local",
        quantity=1,
        status="pending",
        payment_status="unpaid",
        reservation_code=f"PLT{uuid4().hex[:6].upper()}",
        note="Automatski pilot smoke test",
    )
    db.add(reservation)
    db.flush()
    apply_pricing_to_reservation(db, reservation)
    register_reservation_created(db, reservation)
    mark_paid(reservation, provider="demo", method="pilot_demo_card")
    previous_status = reservation.status
    reservation.status = "picked_up"
    apply_reservation_status_transition(db, reservation, previous_status, "picked_up")
    reservation.seller_payout_status = "pending"
    reservation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(reservation)

    return {
        "ok": True,
        "message": "Kupac -> rezervacija -> demo plaćanje -> preuzimanje -> finansije radi.",
        "store": {
            "id": product.store.id,
            "name": product.store.name,
            "pin": product.store.seller_pin,
        },
        "product": product_to_public(db, product),
        "reservation": _reservation_to_out(reservation),
        "links": {
            "reservation_api": f"/reservations/code/{reservation.reservation_code}",
            "checkout_api": f"/payments/reservations/{reservation.reservation_code}/checkout",
            "reservation_qr": f"/qr/reservation/{reservation.reservation_code}.svg",
            "payment_qr": f"/qr/payment/{reservation.reservation_code}.svg",
            "seller_reservations": f"/seller-api/reservations?store_id={product.store.id}&pin={product.store.seller_pin}",
            "finance_summary": "/finance/summary",
        },
    }
