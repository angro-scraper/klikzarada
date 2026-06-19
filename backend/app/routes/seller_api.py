from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from .products import product_to_public
from .reservations import _reservation_to_out
from ..services.pricing import mark_refunded_if_paid
from ..services.customers import apply_reservation_status_transition

router = APIRouter(prefix="/seller-api", tags=["seller-api"])
SELLER_PRODUCT_STATUSES = {"seller_verified", "near_expiry", "public_discount", "candidate", "hidden"}
SELLER_RESERVATION_STATUSES = {"pending", "confirmed", "picked_up", "cancelled", "expired"}


def verify_store(db: Session, store_id: int, pin: str) -> models.Store:
    store = db.get(models.Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Prodavac nije pronađen")
    if str(store.seller_pin) != str(pin):
        raise HTTPException(status_code=401, detail="Pogrešan PIN za prodavca")
    return store


@router.post("/login", response_model=schemas.StoreOut)
def seller_login(payload: schemas.SellerLoginRequest, db: Session = Depends(get_db)):
    return verify_store(db, payload.store_id, payload.pin)




@router.patch("/location", response_model=schemas.StorePublicOut)
def seller_update_store_location(payload: schemas.SellerStoreLocationUpdate, db: Session = Depends(get_db)):
    store = verify_store(db, payload.store_id, payload.pin)
    store.latitude = payload.latitude
    store.longitude = payload.longitude
    db.commit()
    db.refresh(store)
    return store


@router.get("/products", response_model=list[schemas.ProductPublicOut])
def seller_products(
    store_id: int,
    pin: str,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    verify_store(db, store_id, pin)
    query = db.query(models.Product).filter(models.Product.store_id == store_id)
    if status:
        query = query.filter(models.Product.status == status)
    else:
        query = query.filter(models.Product.status.notin_(["expired", "hidden"]))
    products = query.order_by(models.Product.updated_at.desc()).limit(250).all()
    return [product_to_public(db, product) for product in products]


@router.post("/products", response_model=schemas.ProductOut)
def seller_create_product(payload: schemas.SellerProductCreate, db: Session = Depends(get_db)):
    if payload.store_id is None:
        raise HTTPException(status_code=400, detail="store_id je obavezan")
    verify_store(db, payload.store_id, payload.pin)
    data = payload.model_dump(exclude={"pin"})
    if data.get("status") not in SELLER_PRODUCT_STATUSES:
        raise HTTPException(status_code=400, detail="Prodavac ne može da postavi ovaj status")
    product = models.Product(**data)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/products/{product_id}/status", response_model=schemas.ProductOut)
def seller_update_product_status(
    product_id: int,
    payload: schemas.SellerProductStatusUpdate,
    db: Session = Depends(get_db),
):
    verify_store(db, payload.store_id, payload.pin)
    if payload.status not in SELLER_PRODUCT_STATUSES:
        raise HTTPException(status_code=400, detail="Prodavac ne može da postavi ovaj status")
    product = db.get(models.Product, product_id)
    if not product or product.store_id != payload.store_id:
        raise HTTPException(status_code=404, detail="Artikal nije pronađen za ovog prodavca")
    product.status = payload.status
    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)
    return product


@router.get("/reservations", response_model=list[schemas.ReservationOut])
def seller_reservations(
    store_id: int,
    pin: str,
    status: str | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    verify_store(db, store_id, pin)
    query = db.query(models.Reservation).join(models.Product).filter(models.Product.store_id == store_id)
    if status:
        query = query.filter(models.Reservation.status == status)
    reservations = query.order_by(models.Reservation.created_at.desc()).limit(limit).all()
    return [_reservation_to_out(r) for r in reservations]


@router.patch("/reservations/{reservation_id}/status", response_model=schemas.ReservationOut)
def seller_update_reservation_status(
    reservation_id: int,
    payload: schemas.SellerReservationStatusUpdate,
    db: Session = Depends(get_db),
):
    verify_store(db, payload.store_id, payload.pin)
    if payload.status not in SELLER_RESERVATION_STATUSES:
        raise HTTPException(status_code=400, detail="Nepoznat status rezervacije")
    reservation = db.get(models.Reservation, reservation_id)
    if not reservation or not reservation.product or reservation.product.store_id != payload.store_id:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena za ovog prodavca")
    previous_status = reservation.status
    reservation.status = payload.status
    if payload.status in {"cancelled", "expired"}:
        mark_refunded_if_paid(reservation)
    if payload.status == "picked_up" and reservation.payment_status == "pay_on_pickup":
        reservation.seller_payout_status = "commission_due"
        reservation.seller_payout_note = "Prodavac je naplatio kupcu pri preuzimanju; platformska provizija je za naplatu od prodavca."
    apply_reservation_status_transition(db, reservation, previous_status, payload.status)
    reservation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(reservation)
    return _reservation_to_out(reservation)


@router.get("/reservations/code/{reservation_code}", response_model=schemas.ReservationOut)
def seller_get_reservation_by_code(
    reservation_code: str,
    store_id: int,
    pin: str,
    db: Session = Depends(get_db),
):
    verify_store(db, store_id, pin)
    reservation = db.query(models.Reservation).join(models.Product).filter(
        models.Reservation.reservation_code == reservation_code.upper(),
        models.Product.store_id == store_id,
    ).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena za ovog prodavca")
    return _reservation_to_out(reservation)
