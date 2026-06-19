from datetime import date, timedelta
from math import asin, cos, radians, sin, sqrt
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/products", tags=["products"])
ACTIVE_RESERVATION_STATUSES = ["pending", "confirmed"]
VISIBLE_STATUSES = ["public_discount", "seller_verified", "near_expiry"]


SUPPORTED_CITIES = [
    "Beograd", "Novi Sad", "Niš", "Kragujevac", "Subotica", "Zrenjanin", "Pančevo", "Čačak",
    "Kraljevo", "Novi Pazar", "Smederevo", "Leskovac", "Valjevo", "Kruševac", "Vranje",
    "Šabac", "Sombor", "Kikinda", "Užice", "Požarevac", "Pirot", "Zaječar", "Jagodina",
    "Loznica", "Prokuplje", "Sremska Mitrovica", "Ruma", "Inđija", "Stara Pazova", "Aranđelovac",
    "Bor", "Vrbas", "Bačka Palanka", "Apatin", "Kovin", "Obrenovac", "Mladenovac", "Lazarevac",
]

BELGRADE_DISTRICTS = [
    "Stari grad", "Vračar", "Savski venac", "Zvezdara", "Palilula", "Novi Beograd", "Zemun",
    "Čukarica", "Rakovica", "Voždovac", "Grocka", "Surčin", "Obrenovac", "Lazarevac", "Mladenovac",
    "Barajevo", "Sopot", "Banovo brdo", "Dorćol", "Karaburma", "Mirijevo", "Banjica", "Konjarnik",
    "Medaković", "Vidikovac", "Žarkovo", "Ledine", "Bežanijska kosa", "Altina", "Borča", "Kotež",
]

SUPPORTED_CATEGORIES = [
    "pekara", "restoran", "market", "mlečni proizvodi", "voće i povrće", "mesara", "ribarnica",
    "poslastice", "gotova jela", "zdrava hrana", "delikates", "pića", "smrznuta hrana",
    "sendviči", "salate", "kuvana jela", "kafa i doručak", "korpa iznenađenja", "ostalo",
]

POPULAR_SEARCHES = [
    "pekara do 200 din", "hleb blizu mene", "pecivo danas", "najveći popusti",
    "korpa iznenađenja", "gotova jela do 400 din", "voće i povrće", "mlečni proizvodi",
    "ponude sa slikom", "pred istek roka",
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Great-circle distance. Good enough for nearby-city filtering in the MVP.
    earth_radius_km = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return 2 * earth_radius_km * asin(sqrt(a))


def reserved_quantity_for_product(db: Session, product_id: int) -> int:
    reserved = db.query(func.coalesce(func.sum(models.Reservation.quantity), 0)).filter(
        models.Reservation.product_id == product_id,
        models.Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
    ).scalar()
    return int(reserved or 0)


def product_available_quantity(db: Session, product: models.Product) -> int | None:
    if product.quantity is None:
        return None
    return max(product.quantity - reserved_quantity_for_product(db, product.id), 0)


def product_to_public(db: Session, product: models.Product, *, lat: float | None = None, lng: float | None = None) -> dict:
    data = schemas.ProductOut.model_validate(product).model_dump()
    data.update({
        "store_name": product.store.name if product.store else None,
        "store_city": product.store.city if product.store else None,
        "store_address": product.store.address if product.store else None,
        "store_phone": product.store.phone if product.store else None,
        "store_latitude": product.store.latitude if product.store else None,
        "store_longitude": product.store.longitude if product.store else None,
        "distance_km": round(haversine_km(lat, lng, product.store.latitude, product.store.longitude), 2) if lat is not None and lng is not None and product.store and product.store.latitude is not None and product.store.longitude is not None else None,
        "available_quantity": product_available_quantity(db, product),
    })
    return data


def apply_product_filters(
    query,
    *,
    city: str | None = None,
    district: str | None = None,
    category: str | None = None,
    status: str | None = None,
    store_id: int | None = None,
    q: str | None = None,
    min_discount: float | None = None,
    max_price: float | None = None,
    expiring_days: int | None = None,
    has_image: bool | None = None,
    only_active: bool = True,
):
    if store_id:
        query = query.filter(models.Product.store_id == store_id)
    if city:
        query = query.filter(models.Store.city.ilike(f"%{city.strip()}%"))
    if district:
        district_needle = f"%{district.strip()}%"
        query = query.filter(or_(models.Store.city.ilike(district_needle), models.Store.address.ilike(district_needle), models.Store.name.ilike(district_needle)))
    if category:
        query = query.filter(models.Product.category.ilike(category.strip()))
    if status:
        query = query.filter(models.Product.status == status)
    elif only_active:
        query = query.filter(models.Product.status.notin_(["expired", "hidden"]))
    if q:
        needle = f"%{q.strip()}%"
        query = query.filter(or_(
            models.Product.name.ilike(needle),
            models.Product.category.ilike(needle),
            models.Store.name.ilike(needle),
            models.Store.city.ilike(needle),
            models.Store.address.ilike(needle),
        ))
    if min_discount is not None:
        query = query.filter(models.Product.discount_percent.is_not(None), models.Product.discount_percent >= min_discount)
    if max_price is not None:
        query = query.filter(models.Product.discounted_price.is_not(None), models.Product.discounted_price <= max_price)
    if expiring_days is not None:
        end_date = date.today() + timedelta(days=max(expiring_days, 0))
        query = query.filter(models.Product.expiry_date.is_not(None), models.Product.expiry_date <= end_date)
    if has_image is True:
        query = query.filter(models.Product.image_url.is_not(None), models.Product.image_url != "")
    return query


def apply_sort(query, sort: str):
    if sort == "discount_desc":
        return query.order_by(models.Product.discount_percent.desc().nullslast(), models.Product.updated_at.desc())
    if sort == "price_asc":
        return query.order_by(models.Product.discounted_price.asc().nullslast(), models.Product.updated_at.desc())
    if sort == "expiry_asc":
        return query.order_by(models.Product.expiry_date.asc().nullslast(), models.Product.updated_at.desc())
    if sort == "newest":
        return query.order_by(models.Product.created_at.desc())
    return query.order_by(models.Product.updated_at.desc())


@router.post("", response_model=schemas.ProductOut)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    if payload.store_id and not db.get(models.Store, payload.store_id):
        raise HTTPException(status_code=404, detail="Prodavac nije pronađen")
    product = models.Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/facets", response_model=dict)
def product_facets(db: Session = Depends(get_db)):
    statuses = VISIBLE_STATUSES
    city_rows = db.query(models.Store.city).join(models.Product, models.Product.store_id == models.Store.id).filter(
        models.Store.city.is_not(None),
        models.Product.status.in_(statuses),
    ).distinct().order_by(models.Store.city.asc()).all()
    category_rows = db.query(models.Product.category).filter(
        models.Product.category.is_not(None),
        models.Product.status.in_(statuses),
    ).distinct().order_by(models.Product.category.asc()).all()
    db_cities = [row[0] for row in city_rows if row[0]]
    db_categories = [row[0] for row in category_rows if row[0]]
    cities = sorted(set(SUPPORTED_CITIES + db_cities), key=lambda x: x.lower())
    categories = sorted(set(SUPPORTED_CATEGORIES + db_categories), key=lambda x: x.lower())
    return {
        "cities": cities,
        "belgrade_districts": BELGRADE_DISTRICTS,
        "categories": categories,
        "popular_searches": POPULAR_SEARCHES,
        "statuses": statuses,
        "sorts": ["updated", "distance_asc", "discount_desc", "price_asc", "expiry_asc", "newest"],
    }


@router.get("", response_model=list[schemas.ProductPublicOut])
def list_products(
    city: str | None = None,
    district: str | None = None,
    category: str | None = None,
    status: str | None = None,
    store_id: int | None = None,
    q: str | None = None,
    min_discount: float | None = Query(default=None, ge=0, le=100),
    max_price: float | None = Query(default=None, ge=0, le=1000000),
    expiring_days: int | None = Query(default=None, ge=0, le=365),
    has_image: bool | None = None,
    only_active: bool = True,
    only_available: bool = False,
    public_only: bool = False,
    sort: str = "updated",
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float | None = Query(default=None, ge=0.1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(models.Product).outerjoin(models.Store)
    query = apply_product_filters(
        query,
        city=city,
        district=district,
        category=category,
        status=status,
        store_id=store_id,
        q=q,
        min_discount=min_discount,
        max_price=max_price,
        expiring_days=expiring_days,
        has_image=has_image,
        only_active=only_active,
    )
    if public_only:
        query = query.filter(models.Product.status.in_(VISIBLE_STATUSES))
    products = apply_sort(query, sort).limit(250).all()
    result = [product_to_public(db, product, lat=lat, lng=lng) for product in products]
    if lat is not None and lng is not None and radius_km is not None:
        result = [p for p in result if p["distance_km"] is not None and p["distance_km"] <= radius_km]
    if only_available:
        result = [p for p in result if p["available_quantity"] is None or p["available_quantity"] > 0]
    if sort == "distance_asc" and lat is not None and lng is not None:
        result.sort(key=lambda p: p["distance_km"] if p["distance_km"] is not None else 10**9)
    return result


@router.get("/{product_id}", response_model=schemas.ProductPublicOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Artikal nije pronađen")
    return product_to_public(db, product)


@router.patch("/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Artikal nije pronađen")
    if payload.store_id and not db.get(models.Store, payload.store_id):
        raise HTTPException(status_code=404, detail="Prodavac nije pronađen")
    for key, value in payload.model_dump().items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}/status", response_model=schemas.ProductOut)
def update_product_status(product_id: int, status: str, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Artikal nije pronađen")
    product.status = status
    db.commit()
    db.refresh(product)
    return product


@router.post("/expire-old", response_model=dict)
def expire_old_products(db: Session = Depends(get_db)):
    today = date.today()
    products = db.query(models.Product).filter(
        models.Product.expiry_date.is_not(None),
        models.Product.expiry_date < today,
        models.Product.status.notin_(["expired", "hidden"]),
    ).all()
    for product in products:
        product.status = "expired"
    db.commit()
    return {"expired_count": len(products)}
