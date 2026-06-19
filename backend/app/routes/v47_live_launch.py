import os
import json
import shutil
from datetime import datetime, date
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import SessionLocal
from ..models import Store, Product, Reservation

router = APIRouter(prefix="/live-launch-api", tags=["V47 Live Launch"])

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"
LIVE_DIR = DATA_DIR / "live_launch"
for d in (DATA_DIR, BACKUP_DIR, LIVE_DIR):
    d.mkdir(parents=True, exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _env_bool(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).lower() in {"1", "true", "yes", "da", "on"}


def _public_products(db: Session):
    public_statuses = ["seller_verified", "near_expiry", "public_discount"]
    return db.query(Product).filter(Product.status.in_(public_statuses)).all()


def _metrics(db: Session) -> dict[str, Any]:
    products = _public_products(db)
    stores = db.query(Store).all()
    reservations = db.query(Reservation).all()
    active_stores = {p.store_id for p in products if p.store_id}
    with_image = [p for p in products if p.image_url]
    with_gps = [p for p in products if p.store and p.store.latitude is not None and p.store.longitude is not None]
    cities = sorted({(p.store.city or "Nepoznato") for p in products if p.store})
    paid = [r for r in reservations if (r.payment_status or "").lower() in {"paid", "confirmed", "settled"}]
    return {
        "public_products": len(products),
        "products_with_image": len(with_image),
        "products_with_gps": len(with_gps),
        "stores_total": len(stores),
        "active_stores": len(active_stores),
        "cities_with_offers": len(cities),
        "cities": cities,
        "reservations_total": len(reservations),
        "paid_reservations": len(paid),
        "image_rate": round((len(with_image) / len(products) * 100), 1) if products else 0,
        "gps_rate": round((len(with_gps) / len(products) * 100), 1) if products else 0,
    }


def _env_checks() -> list[dict[str, Any]]:
    provider = os.getenv("PAYMENT_PROVIDER", "demo")
    public_base = os.getenv("PUBLIC_BASE_URL", "")
    merchant_account = os.getenv("MERCHANT_ACCOUNT", "")
    admin_pin = os.getenv("ADMIN_PIN", "246810")
    session_secret = os.getenv("ADMIN_SESSION_SECRET", "")
    production = _env_bool("PRODUCTION_MODE") or public_base.startswith("https://")
    checks = [
        {
            "key": "PUBLIC_BASE_URL",
            "ok": bool(public_base) and (public_base.startswith("https://") or public_base.startswith("http://127.0.0.1")),
            "value": public_base or "nije podešeno",
            "message": "Za izlazak uživo treba HTTPS javna adresa. Lokalno je OK 127.0.0.1.",
        },
        {
            "key": "PAYMENT_PROVIDER",
            "ok": provider in {"ips_qr", "monri_wspay", "demo"},
            "value": provider,
            "message": "Za realno plaćanje preporuka je ips_qr ili gateway adapter.",
        },
        {
            "key": "MERCHANT_ACCOUNT",
            "ok": bool(merchant_account.strip()) if provider == "ips_qr" else True,
            "value": "podešeno" if merchant_account else "nije podešeno",
            "message": "IPS QR mora imati račun primaoca u .env fajlu.",
        },
        {
            "key": "ADMIN_PIN",
            "ok": admin_pin != "246810" or not production,
            "value": "podrazumevan PIN" if admin_pin == "246810" else "promenjen",
            "message": "Pre produkcije promeniti admin PIN.",
        },
        {
            "key": "ADMIN_SESSION_SECRET",
            "ok": bool(session_secret) and session_secret != "change-this-to-a-long-random-secret" or not production,
            "value": "podešeno" if session_secret else "nije podešeno",
            "message": "Za produkciju mora biti dugačak random secret.",
        },
        {
            "key": "ADMIN_COOKIE_SECURE",
            "ok": _env_bool("ADMIN_COOKIE_SECURE") or not production,
            "value": os.getenv("ADMIN_COOKIE_SECURE", "false"),
            "message": "Na HTTPS produkciji cookie treba da bude secure=true.",
        },
    ]
    return checks


def _readiness_score(metrics: dict[str, Any], env_checks: list[dict[str, Any]]) -> tuple[int, list[str]]:
    score = 0
    notes = []
    targets = [
        (metrics["public_products"] >= 50, 20, "Minimum 50 javnih ponuda"),
        (metrics["products_with_image"] >= 50 and metrics["image_rate"] >= 90, 15, "Ponude imaju slike"),
        (metrics["products_with_gps"] >= 40 and metrics["gps_rate"] >= 80, 15, "Ponude imaju GPS"),
        (metrics["active_stores"] >= 10, 15, "Minimum 10 aktivnih prodavaca"),
        (metrics["cities_with_offers"] >= 3, 10, "Ponude u više gradova"),
        (all(c["ok"] for c in env_checks), 15, "Produkcioni .env spreman"),
        (os.path.exists(BACKEND_DIR / "README.md"), 5, "Dokumentacija postoji"),
        (os.path.exists(BASE_DIR / "static" / "admin" / "consumer-app.html"), 5, "Korisnička aplikacija postoji"),
    ]
    for ok, points, label in targets:
        if ok:
            score += points
        else:
            notes.append(label)
    return min(score, 100), notes


@router.get("/status")
def live_status(db: Session = Depends(get_db)):
    metrics = _metrics(db)
    env_checks = _env_checks()
    score, missing = _readiness_score(metrics, env_checks)
    return {
        "version": "V47 Live Deployment Suite",
        "generated_at": datetime.utcnow().isoformat(),
        "readiness_score": score,
        "missing": missing,
        "metrics": metrics,
        "env_checks": env_checks,
        "recommended_next": _recommended_next(score, metrics, env_checks),
    }


def _recommended_next(score: int, metrics: dict[str, Any], checks: list[dict[str, Any]]) -> list[str]:
    recs = []
    if metrics["public_products"] < 50:
        recs.append("Učitaj pilot bazu ili dodaj realne ponude dok ne bude minimum 50 javnih ponuda.")
    if metrics["image_rate"] < 90:
        recs.append("Blokiraj ponude bez slike i obavezno koristi kameru u seller panelu.")
    if metrics["gps_rate"] < 80:
        recs.append("Dopuni GPS koordinate prodavaca da mapa i blizina rade pouzdano.")
    if not all(c["ok"] for c in checks):
        recs.append("Sredi .env production podešavanja pre javnog deploy-a.")
    if score >= 80:
        recs.append("Spremno za zatvoreni pilot: pusti domen/HTTPS, testiraj plaćanje i pozovi prve prodavce.")
    return recs


@router.post("/backup")
def create_backup():
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    db_path = BACKEND_DIR / "food_saver.db"
    excel_path = DATA_DIR / "food_saver_database.xlsx"
    manifest = {
        "created_at": datetime.utcnow().isoformat(),
        "files": [],
        "note": "Lokalni backup za pilot. Za produkciju dodati remote backup.",
    }
    if db_path.exists():
        dest = BACKUP_DIR / f"food_saver_{timestamp}.db"
        shutil.copy2(db_path, dest)
        manifest["files"].append(str(dest))
    if excel_path.exists():
        dest = BACKUP_DIR / f"food_saver_database_{timestamp}.xlsx"
        shutil.copy2(excel_path, dest)
        manifest["files"].append(str(dest))
    manifest_path = BACKUP_DIR / f"backup_manifest_{timestamp}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "manifest": manifest, "manifest_path": str(manifest_path)}


@router.get("/production-env")
def production_env_template():
    content = """# Sačuvaj Hranu — produkcioni .env primer
APP_NAME=Sačuvaj Hranu
PRODUCTION_MODE=true
PUBLIC_BASE_URL=https://tvoj-domen.rs

# Admin
ADMIN_PIN=promeni-ovo
ADMIN_SESSION_SECRET=dugacak-random-secret-minimum-32-karaktera
ADMIN_SESSION_HOURS=12
ADMIN_COOKIE_SECURE=true

# Excel / backup
EXCEL_AUTOSAVE=true

# Plaćanje
PAYMENT_PROVIDER=ips_qr
MERCHANT_NAME=Sačuvaj Hranu DOO
MERCHANT_ADDRESS=Beograd
MERCHANT_ACCOUNT=160-0000000000000-00
MERCHANT_PAYMENT_CODE=189
MERCHANT_PAYMENT_PURPOSE=Sačuvaj Hranu rezervacija {code}
PAYMENT_REFERENCE_PREFIX=SH
PLATFORM_COMMISSION_PERCENT=25
LOYALTY_MIN_PERCENT=1
LOYALTY_MAX_PERCENT=5

# SMS/OTP
SMS_PROVIDER=mock
SMS_DRY_RUN=true
DEV_SHOW_OTP=false

# CORS / domeni
ALLOWED_ORIGINS=https://tvoj-domen.rs
"""
    path = BACKEND_DIR / ".env.production.example"
    path.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(path), "content": content}


@router.get("/sitemap-preview")
def sitemap_preview(db: Session = Depends(get_db)):
    base_url = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    products = _public_products(db)[:200]
    static_paths = ["/app", "/partner", "/support", "/terms", "/privacy", "/food-safety"]
    urls = [f"{base_url}{p}" for p in static_paths]
    cities = sorted({(p.store.city or "").strip() for p in products if p.store and p.store.city})
    categories = sorted({(p.category or "").strip() for p in products if p.category})
    for city in cities[:30]:
        urls.append(f"{base_url}/app?city={city}")
    for cat in categories[:30]:
        urls.append(f"{base_url}/app?category={cat}")
    for p in products[:100]:
        urls.append(f"{base_url}/offer?id={p.id}")
    xml = "<?xml version='1.0' encoding='UTF-8'?>\n<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>\n"
    for url in urls:
        xml += f"  <url><loc>{url}</loc><lastmod>{date.today().isoformat()}</lastmod></url>\n"
    xml += "</urlset>\n"
    (LIVE_DIR / "sitemap_preview.xml").write_text(xml, encoding="utf-8")
    return {"ok": True, "count": len(urls), "urls": urls[:40], "xml_path": str(LIVE_DIR / "sitemap_preview.xml")}


@router.post("/seed-launch-checklist")
def seed_launch_checklist():
    checklist = [
        {"area": "Domen", "task": "Podesiti domen i HTTPS", "status": "todo", "owner": "tech"},
        {"area": "Plaćanje", "task": "Uneti stvarni MERCHANT_ACCOUNT i testirati IPS QR", "status": "todo", "owner": "finance"},
        {"area": "Baza", "task": "Minimum 50 javnih ponuda sa slikama i GPS-om", "status": "todo", "owner": "ops"},
        {"area": "Prodavci", "task": "Verifikovati 10 partnera i podeliti seller PIN", "status": "todo", "owner": "sales"},
        {"area": "Podrška", "task": "Testirati support, refund i no-show tok", "status": "todo", "owner": "support"},
        {"area": "Legal", "task": "Proveriti Terms, Privacy i Food Safety stranice", "status": "todo", "owner": "legal"},
        {"area": "Monitoring", "task": "Uraditi backup i proveriti health endpoint", "status": "todo", "owner": "tech"},
        {"area": "Marketing", "task": "Pripremiti PRVI5 i PECIVO18 kampanje", "status": "todo", "owner": "growth"},
    ]
    path = LIVE_DIR / "launch_checklist.json"
    path.write_text(json.dumps(checklist, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "count": len(checklist), "items": checklist, "path": str(path)}


@router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(func.count(Store.id))
        database_ok = True
    except Exception:
        database_ok = False
    return {
        "ok": database_ok,
        "database": "ok" if database_ok else "error",
        "time": datetime.utcnow().isoformat(),
        "version": "v47",
    }
