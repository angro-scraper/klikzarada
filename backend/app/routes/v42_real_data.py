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

router = APIRouter(prefix="/v42-api", tags=["v42-real-ai-data"])

VISIBLE_STATUSES = {"public_discount", "seller_verified", "near_expiry"}
REAL_CATALOG_STATUS = "real_catalog_reference"

REAL_STORES: list[dict[str, Any]] = [
    {
        "name": "Pekara Kirćanski",
        "city": "Beograd",
        "address": "Jurija Gagarina bb, Pijaca Blok 44, Novi Beograd",
        "website": "https://glovoapp.com/sr/rs/belgrade/stores/pekara-kircanski",
        "phone": "potrebna potvrda",
        "verified": False,
        "note": "Javni katalog proizvoda sa Glovo izvora. Partner mora da potvrdi pre live prodaje.",
    },
    {
        "name": "Skroz dobra pekara - Novi Beograd",
        "city": "Beograd",
        "address": "Goce Delčeva 27, Novi Beograd",
        "website": "https://glovoapp.com/sr/rs/belgrade/stores/skroz-dobra-pekara-beg",
        "phone": "potrebna potvrda",
        "verified": False,
        "note": "Javni katalog proizvoda sa Glovo izvora. Partner mora da potvrdi pre live prodaje.",
    },
    {
        "name": "Pekara na Bulevaru",
        "city": "Beograd",
        "address": "Beograd",
        "website": "https://glovoapp.com/en/rs/belgrade/stores/pekaranabulevaru",
        "phone": "potrebna potvrda",
        "verified": False,
        "note": "Javni katalog proizvoda sa Glovo izvora. Partner mora da potvrdi pre live prodaje.",
    },
    {
        "name": "Baba Višnjine kiflice",
        "city": "Beograd",
        "address": "Beograd",
        "website": "https://kiflice.rs/",
        "phone": "potrebna potvrda",
        "verified": False,
        "note": "Javni katalog proizvoda sa zvaničnog sajta. Partner mora da potvrdi pre live prodaje.",
    },
]

# Real reference catalog. These are not automatically near-expiry offers. They are imported as catalog references.
# image_url values are public external images from the source pages where available; for production replace with seller-owned photos.
REAL_PRODUCTS: list[dict[str, Any]] = [
    # Pekara Kirćanski
    {"store": "Pekara Kirćanski", "name": "Burek pica 200g", "category": "pekara", "price": 270, "unit": "kom", "source_url": "https://glovoapp.com/sr/rs/belgrade/stores/pekara-kircanski", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/66919991a7442e92522fd19340ff809f1cb6f5a495e9a90ea7d67f5ef31fddef?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    {"store": "Pekara Kirćanski", "name": "Burek sa mesom 200g", "category": "pekara", "price": 250, "unit": "kom", "source_url": "https://glovoapp.com/sr/rs/belgrade/stores/pekara-kircanski", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/d719f816b9bc0f0cf52b93d89c849aaa1b4f36e23e81820de9d659dad0636316?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    {"store": "Pekara Kirćanski", "name": "Burek sa sirom 200g", "category": "pekara", "price": 190, "unit": "kom", "source_url": "https://glovoapp.com/sr/rs/belgrade/stores/pekara-kircanski", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/d719f816b9bc0f0cf52b93d89c849aaa1b4f36e23e81820de9d659dad0636316?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    {"store": "Pekara Kirćanski", "name": "Pecivo sa slaninom i jajem", "category": "pekara", "price": 270, "unit": "kom", "source_url": "https://glovoapp.com/sr/rs/belgrade/stores/pekara-kircanski", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/497748fa7fb319c06fa295408c77fc4a2fea43134a6d5b5761736ed44b85a555?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    {"store": "Pekara Kirćanski", "name": "Kifla sa Bolognese sosom", "category": "pekara", "price": 170, "unit": "kom", "source_url": "https://glovoapp.com/sr/rs/belgrade/stores/pekara-kircanski", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/515f12d2b04fb83ca8ee317ecf0b8125642355b8b4b3e69398fdedfc882323b5?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    {"store": "Pekara Kirćanski", "name": "Slavski kolač", "category": "pekara", "price": 900, "unit": "kom", "source_url": "https://glovoapp.com/sr/rs/belgrade/stores/pekara-kircanski", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/82ca928c7aec7214b1d03f4b46a8c7f7699e6222cc3898fab572d9ca5be66cfc?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    # Skroz dobra pekara
    {"store": "Skroz dobra pekara - Novi Beograd", "name": "Mrežica pečenica zdenka", "category": "pekara", "price": 220, "unit": "kom", "source_url": "https://glovoapp.com/sr/rs/belgrade/stores/skroz-dobra-pekara-beg", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/d3f8166e1fdfaad294ca920b21d49faf131e5830e123721131b51aeb8c549481?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    {"store": "Skroz dobra pekara - Novi Beograd", "name": "Sarajevska pita sir", "category": "pekara", "price": 210, "unit": "kom", "source_url": "https://glovoapp.com/sr/rs/belgrade/stores/skroz-dobra-pekara-beg", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/d8e213c6e6f4a35e6347e64c995b956b92be2df50ab4a67d78089b7c4fa97845?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    {"store": "Skroz dobra pekara - Novi Beograd", "name": "Viršla maxi", "category": "pekara", "price": 200, "unit": "kom", "source_url": "https://glovoapp.com/sr/rs/belgrade/stores/skroz-dobra-pekara-beg", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/b2a70a269d8586f9bcbd7650e2ab4814d47a6b9fb4b5139a52421e93bf84eb82?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    {"store": "Skroz dobra pekara - Novi Beograd", "name": "Kroasan šunka", "category": "pekara", "price": 150, "unit": "kom", "source_url": "https://glovoapp.com/sr/rs/belgrade/stores/skroz-dobra-pekara-beg", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/8a81d21d27e195d34c66626ee46a5fc37a186d08f5e972bf46a4a30739ac71a2?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    {"store": "Skroz dobra pekara - Novi Beograd", "name": "Kroasan sir", "category": "pekara", "price": 130, "unit": "kom", "source_url": "https://glovoapp.com/sr/rs/belgrade/stores/skroz-dobra-pekara-beg", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/8a81d21d27e195d34c66626ee46a5fc37a186d08f5e972bf46a4a30739ac71a2?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    {"store": "Skroz dobra pekara - Novi Beograd", "name": "Bavarski đevrek", "category": "pekara", "price": 90, "unit": "kom", "source_url": "https://glovoapp.com/sr/rs/belgrade/stores/skroz-dobra-pekara-beg", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/134aced4da177d774d95bd6084326f143331ffbb0ab0cf3ae391e3fa48d6d4f5?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    # Pekara na Bulevaru
    {"store": "Pekara na Bulevaru", "name": "Domaći hleb 500g", "category": "pekara", "price": 130, "unit": "kom", "source_url": "https://glovoapp.com/en/rs/belgrade/stores/pekaranabulevaru", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/c40f6141ce967d514cc84fdca7d16d2f4863b8c572de0706af2a8509d7ea0f68?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    {"store": "Pekara na Bulevaru", "name": "Pita višnja 150g", "category": "pekara", "price": 280, "unit": "kom", "source_url": "https://glovoapp.com/en/rs/belgrade/stores/pekaranabulevaru", "image_url": "https://glovo.dhmedia.io/image/global-menu-service/GV_RS/vendor/291453/product/15921760074/82df9859-2b82-4a1e-97c9-abb220b0442e.jpg?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    {"store": "Pekara na Bulevaru", "name": "Kiflice sir 200g", "category": "pekara", "price": 380, "unit": "kom", "source_url": "https://glovoapp.com/en/rs/belgrade/stores/pekaranabulevaru", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/eeb092181e5db027c6e8f9ad4f6b62138287c2ac8980189d0b92591b67539299?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    {"store": "Pekara na Bulevaru", "name": "Vanilice džem 200g", "category": "poslastice", "price": 380, "unit": "kom", "source_url": "https://glovoapp.com/en/rs/belgrade/stores/pekaranabulevaru", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/20a58b4324301bad2ccdb643c80aecf3f29f85277d71203526b3a88e62fb4f07?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    {"store": "Pekara na Bulevaru", "name": "Domaće perece 200g", "category": "pekara", "price": 380, "unit": "kom", "source_url": "https://glovoapp.com/en/rs/belgrade/stores/pekaranabulevaru", "image_url": "https://glovo.dhmedia.io/image/menus-glovo/products/4fd7c1b67fae6c3de6de0a9f8ddc52c3c334cb1aee1d95d223bca9ddf44435f8?t=W3sicmVzaXplIjp7Im1vZGUiOiJmaXQiLCJ3aWR0aCI6MzIwLCJoZWlnaHQiOjMyMH19LHsid2VicCI6e319XQ%3D%3D"},
    # Baba Višnjine kiflice - official catalog with prices, product images present on source page, image URLs may be blocked by site.
    {"store": "Baba Višnjine kiflice", "name": "Tartuf cheese", "category": "pekara", "price": 1390, "unit": "kg", "source_url": "https://kiflice.rs/", "image_url": "https://kiflice.rs/wp-content/uploads/2024/01/cropped-bvk-logo.png"},
    {"store": "Baba Višnjine kiflice", "name": "Jabuka cimet", "category": "poslastice", "price": 1090, "unit": "kg", "source_url": "https://kiflice.rs/", "image_url": "https://kiflice.rs/wp-content/uploads/2024/01/cropped-bvk-logo.png"},
    {"store": "Baba Višnjine kiflice", "name": "Bavarske kiflice – posno", "category": "pekara", "price": 990, "unit": "kg", "source_url": "https://kiflice.rs/", "image_url": "https://kiflice.rs/wp-content/uploads/2024/01/cropped-bvk-logo.png"},
    {"store": "Baba Višnjine kiflice", "name": "Štapići sa slaninicom", "category": "pekara", "price": 70, "unit": "kom", "source_url": "https://kiflice.rs/", "image_url": "https://kiflice.rs/wp-content/uploads/2024/01/cropped-bvk-logo.png"},
]

AI_CHECKS = [
    {"name": "Real source check", "rule": "source_url mora postojati", "severity": "high"},
    {"name": "Photo gate", "rule": "image_url mora postojati; za live ponudu preporuka je seller-owned photo", "severity": "high"},
    {"name": "Price check", "rule": "original_price ili discounted_price mora biti > 0", "severity": "high"},
    {"name": "Near-expiry truth check", "rule": "status near_expiry samo ako je prodavac potvrdio rok", "severity": "critical"},
    {"name": "Seller verification", "rule": "realni katalog ne znači verifikovan partner", "severity": "critical"},
]

class ContactPatch(BaseModel):
    store_id: int
    status: str = "contacted"
    note: str | None = None


def _upsert_store(db: Session, item: dict[str, Any]) -> tuple[models.Store, bool]:
    store = db.query(models.Store).filter(func.lower(models.Store.name) == item["name"].lower()).first()
    created = False
    if not store:
        store = models.Store(
            name=item["name"],
            city=item.get("city"),
            address=item.get("address"),
            website=item.get("website"),
            phone=item.get("phone"),
            verified=bool(item.get("verified", False)),
        )
        db.add(store)
        db.flush()
        created = True
    else:
        store.city = store.city or item.get("city")
        store.address = store.address or item.get("address")
        store.website = store.website or item.get("website")
        store.phone = store.phone or item.get("phone")
    return store, created


def _product_exists(db: Session, store_id: int, name: str, source_url: str) -> bool:
    return db.query(models.Product).filter(
        models.Product.store_id == store_id,
        func.lower(models.Product.name) == name.lower(),
        models.Product.source_url == source_url,
    ).first() is not None


@router.post("/seed/real-bakery-catalog", dependencies=[Depends(require_admin_session)])
def seed_real_bakery_catalog(db: Session = Depends(get_db)):
    created_stores = 0
    created_products = 0
    updated_sources = 0
    store_map: dict[str, models.Store] = {}
    for item in REAL_STORES:
        store, created = _upsert_store(db, item)
        if created:
            created_stores += 1
        store_map[item["name"]] = store
        if not db.query(models.Source).filter(models.Source.url == item["website"]).first():
            db.add(models.Source(
                name=f"Real catalog · {item['name']}",
                url=item["website"],
                city=item.get("city"),
                source_type="real_catalog_public_reference",
                crawl_frequency="manual_review",
                active=True,
            ))
            updated_sources += 1
    db.flush()

    for item in REAL_PRODUCTS:
        store = store_map.get(item["store"])
        if not store:
            continue
        if _product_exists(db, store.id, item["name"], item["source_url"]):
            continue
        db.add(models.Product(
            store_id=store.id,
            name=item["name"],
            category=item.get("category", "pekara"),
            original_price=float(item["price"]),
            discounted_price=None,
            discount_percent=None,
            currency="RSD",
            expiry_type="unknown",
            quantity=0,
            pickup_window="potrebna potvrda prodavca",
            image_url=item.get("image_url"),
            source_url=item.get("source_url"),
            confidence_score=0.92,
            status=REAL_CATALOG_STATUS,
        ))
        created_products += 1
    db.commit()
    return {
        "created_stores": created_stores,
        "created_products": created_products,
        "sources_added": updated_sources,
        "status": REAL_CATALOG_STATUS,
        "message": "Realni javni katalog je ubačen kao referenca. Nije live near-expiry ponuda dok prodavac ne potvrdi cenu, količinu, rok i sliku.",
    }


@router.get("/dashboard", dependencies=[Depends(require_admin_session)])
def real_data_dashboard(db: Session = Depends(get_db)):
    total = db.query(models.Product).count()
    real_q = db.query(models.Product).filter(models.Product.status == REAL_CATALOG_STATUS)
    real_count = real_q.count()
    with_image = real_q.filter(models.Product.image_url.isnot(None), models.Product.image_url != "").count()
    with_price = real_q.filter((models.Product.original_price > 0) | (models.Product.discounted_price > 0)).count()
    stores = db.query(models.Store).count()
    verified = db.query(models.Store).filter(models.Store.verified == True).count()
    visible = db.query(models.Product).filter(models.Product.status.in_(VISIBLE_STATUSES)).count()
    near_expiry = db.query(models.Product).filter(models.Product.status == "near_expiry").count()
    source_counts = Counter()
    cat_counts = Counter()
    for p in real_q.all():
        source_counts[p.source_url or "bez izvora"] += 1
        cat_counts[p.category or "ostalo"] += 1
    readiness = min(100, round((real_count / 100) * 25 + (with_image / max(1, real_count)) * 25 + (with_price / max(1, real_count)) * 25 + (verified / 10) * 25, 1))
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "total_products": total,
        "real_catalog_products": real_count,
        "real_with_image": with_image,
        "real_with_price": with_price,
        "stores_total": stores,
        "verified_stores": verified,
        "visible_offers": visible,
        "near_expiry_offers": near_expiry,
        "readiness_score": readiness,
        "top_sources": source_counts.most_common(8),
        "top_categories": cat_counts.most_common(8),
    }


@router.get("/products", dependencies=[Depends(require_admin_session)])
def list_real_products(db: Session = Depends(get_db), limit: int = 200):
    rows = db.query(models.Product, models.Store).outerjoin(models.Store, models.Product.store_id == models.Store.id).filter(models.Product.status == REAL_CATALOG_STATUS).order_by(models.Product.created_at.desc()).limit(limit).all()
    return [{
        "id": p.id,
        "store_id": p.store_id,
        "store_name": s.name if s else None,
        "store_city": s.city if s else None,
        "store_verified": bool(s.verified) if s else False,
        "name": p.name,
        "category": p.category,
        "price": p.original_price or p.discounted_price,
        "currency": p.currency,
        "unit": "kom/kg",
        "image_url": p.image_url,
        "source_url": p.source_url,
        "status": p.status,
        "confidence_score": p.confidence_score,
        "quality": _quality_for_product(p, s),
    } for p, s in rows]


def _quality_for_product(p: models.Product, s: models.Store | None) -> dict[str, Any]:
    issues: list[str] = []
    if not p.image_url:
        issues.append("missing_image")
    if not ((p.original_price or 0) > 0 or (p.discounted_price or 0) > 0):
        issues.append("missing_price")
    if not p.source_url:
        issues.append("missing_source")
    if not s or not s.verified:
        issues.append("seller_not_verified")
    if p.status == "near_expiry" and (not p.expiry_date or p.expiry_type == "unknown"):
        issues.append("near_expiry_without_proof")
    return {
        "score": max(0, 100 - len(issues) * 22),
        "issues": issues,
        "public_ready": not issues,
        "recommendation": "kontaktirati prodavca i potvrditi cenu/sliku/rok" if issues else "spremno za live objavu uz potvrdu prodavca",
    }


@router.get("/ai-audit", dependencies=[Depends(require_admin_session)])
def ai_audit(db: Session = Depends(get_db)):
    rows = db.query(models.Product, models.Store).outerjoin(models.Store, models.Product.store_id == models.Store.id).filter(models.Product.status.in_([REAL_CATALOG_STATUS, "candidate", "public_discount", "seller_verified", "near_expiry"])).all()
    issues = Counter()
    examples = defaultdict(list)
    for p, s in rows:
        q = _quality_for_product(p, s)
        for issue in q["issues"]:
            issues[issue] += 1
            if len(examples[issue]) < 5:
                examples[issue].append({"product_id": p.id, "product": p.name, "store": s.name if s else None})
    recommendations = []
    if issues.get("seller_not_verified", 0):
        recommendations.append({"priority": "critical", "title": "Verifikovati prodavce pre javne prodaje", "action": "Kontaktirati realne leadove i prebaciti ih u verified=true tek posle dogovora."})
    if issues.get("missing_image", 0):
        recommendations.append({"priority": "high", "title": "Zatvoriti photo gate", "action": "Seller mora slikati proizvod kroz kameru pre live objave."})
    if issues.get("missing_price", 0):
        recommendations.append({"priority": "high", "title": "Cena mora biti obavezna", "action": "AI i admin ne smeju pustiti ponudu bez cene i količine."})
    if issues.get("near_expiry_without_proof", 0):
        recommendations.append({"priority": "critical", "title": "Rok mora biti potvrđen", "action": "near_expiry status samo uz datum i potvrdu prodavca."})
    if not recommendations:
        recommendations.append({"priority": "ok", "title": "Kvalitet baze je dobar", "action": "Nastaviti sa onboarding-om i live testom."})
    return {"checks": AI_CHECKS, "issues": issues, "examples": examples, "recommendations": recommendations, "audited": len(rows)}


@router.post("/tasks/create-from-real-data", dependencies=[Depends(require_admin_session)])
def create_tasks_from_real_data(db: Session = Depends(get_db)):
    tasks = read_json("v42_real_data_tasks.json", [])
    added = 0
    real_stores = db.query(models.Store).filter(models.Store.website.isnot(None), models.Store.verified == False).all()
    for s in real_stores:
        title = f"Kontaktirati i verifikovati: {s.name}"
        if any(t.get("title") == title for t in tasks):
            continue
        tasks.append({
            "id": f"v42-{s.id}-{int(datetime.utcnow().timestamp())}",
            "title": title,
            "store_id": s.id,
            "store_name": s.name,
            "owner": "sales",
            "priority": "high",
            "status": "open",
            "due_date": (datetime.utcnow() + timedelta(days=3)).date().isoformat(),
            "script": _seller_script(s),
            "created_at": utc_now(),
        })
        added += 1
    write_json("v42_real_data_tasks.json", tasks)
    return {"added": added, "total": len(tasks)}


def _seller_script(s: models.Store) -> str:
    return (
        f"Dobar dan, zovem u vezi Sačuvaj Hranu platforme. Videli smo da {s.name} ima proizvode koji bi mogli biti odlični za večernje ponude i smanjenje bacanja hrane. "
        "Objava ponude ide preko telefona: slikate proizvod, unesete cenu i količinu, a kupac rezerviše/preuzima. "
        "U pilotu cilj je da testiramo 3 dana bez komplikovane integracije. Da li možemo da vam pošaljemo seller link i napravimo prvu probnu ponudu?"
    )


@router.get("/tasks", dependencies=[Depends(require_admin_session)])
def list_tasks():
    return read_json("v42_real_data_tasks.json", [])


@router.post("/contact-status", dependencies=[Depends(require_admin_session)])
def update_contact_status(payload: ContactPatch):
    rows = read_json("v42_real_data_tasks.json", [])
    now = utc_now()
    for row in rows:
        if row.get("store_id") == payload.store_id:
            row["status"] = payload.status
            row["last_note"] = payload.note
            row["updated_at"] = now
    write_json("v42_real_data_tasks.json", rows)
    append_json_row("v42_contact_log.json", {"store_id": payload.store_id, "status": payload.status, "note": payload.note, "created_at": now})
    return {"ok": True}


@router.post("/convert/catalog-to-candidates", dependencies=[Depends(require_admin_session)])
def convert_catalog_to_candidates(db: Session = Depends(get_db), max_items: int = 50):
    rows = db.query(models.Product).filter(models.Product.status == REAL_CATALOG_STATUS).limit(max_items).all()
    changed = 0
    for p in rows:
        p.status = "candidate"
        p.quantity = p.quantity or 1
        p.pickup_window = p.pickup_window or "potrebna potvrda prodavca"
        changed += 1
    db.commit()
    return {"changed": changed, "message": "Katalog je prebačen u candidate, ne u live ponude. Admin/prodavac mora da potvrdi pre objave."}


@router.post("/ai/merchant-next-actions", dependencies=[Depends(require_admin_session)])
def merchant_next_actions(db: Session = Depends(get_db)):
    stores = db.query(models.Store).all()
    actions = []
    for s in stores:
        products = db.query(models.Product).filter(models.Product.store_id == s.id).all()
        if not products:
            continue
        public_ready = sum(1 for p in products if p.image_url and ((p.original_price or 0) > 0 or (p.discounted_price or 0) > 0))
        actions.append({
            "store_id": s.id,
            "store": s.name,
            "verified": s.verified,
            "products": len(products),
            "public_ready_reference_products": public_ready,
            "next_action": "verifikovati prodavca i napraviti prvu seller kamerom potvrđenu ponudu" if not s.verified else "dogovoriti dnevno vreme objave i večernji popust",
            "suggested_discount_window": "18:00-21:00",
            "suggested_discount_percent": 35 if "pekara" in s.name.lower() else 25,
        })
    actions.sort(key=lambda x: (not x["verified"], -x["public_ready_reference_products"]))
    return actions
