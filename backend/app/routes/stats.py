from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models
from ..database import get_db

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=dict)
def get_stats(db: Session = Depends(get_db)):
    total_products = db.query(models.Product).count()
    total_stores = db.query(models.Store).count()
    total_sources = db.query(models.Source).count()
    hidden = db.query(models.Product).filter(models.Product.status == "hidden").count()
    near_expiry = db.query(models.Product).filter(models.Product.status == "near_expiry").count()
    public_discount = db.query(models.Product).filter(models.Product.status == "public_discount").count()
    candidates = db.query(models.Product).filter(models.Product.status.in_(["candidate", "needs_review"])).count()
    expired_by_date = db.query(models.Product).filter(
        models.Product.expiry_date.is_not(None),
        models.Product.expiry_date < date.today(),
        models.Product.status.notin_(["expired", "hidden"]),
    ).count()

    reservations_total = db.query(models.Reservation).count()
    reservations_pending = db.query(models.Reservation).filter(models.Reservation.status == "pending").count()
    reservations_confirmed = db.query(models.Reservation).filter(models.Reservation.status == "confirmed").count()
    reservations_picked_up = db.query(models.Reservation).filter(models.Reservation.status == "picked_up").count()
    reservations_paid = db.query(models.Reservation).filter(models.Reservation.payment_status == "paid").count()
    revenue_paid = db.query(func.coalesce(func.sum(models.Reservation.payable_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    platform_fee_paid = db.query(func.coalesce(func.sum(models.Reservation.platform_fee_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0
    seller_net_paid = db.query(func.coalesce(func.sum(models.Reservation.seller_net_amount), 0)).filter(models.Reservation.payment_status == "paid").scalar() or 0

    avg_discount = db.query(func.avg(models.Product.discount_percent)).filter(
        models.Product.discount_percent.is_not(None)
    ).scalar()

    return {
        "products_total": total_products,
        "stores_total": total_stores,
        "sources_total": total_sources,
        "hidden_total": hidden,
        "near_expiry_total": near_expiry,
        "public_discount_total": public_discount,
        "needs_review_total": candidates,
        "expired_waiting_total": expired_by_date,
        "average_discount_percent": round(float(avg_discount), 2) if avg_discount is not None else None,
        "reservations_total": reservations_total,
        "reservations_pending_total": reservations_pending,
        "reservations_confirmed_total": reservations_confirmed,
        "reservations_picked_up_total": reservations_picked_up,
        "reservations_paid_total": reservations_paid,
        "paid_gross_total": round(float(revenue_paid), 2),
        "platform_fee_total": round(float(platform_fee_paid), 2),
        "seller_net_total": round(float(seller_net_paid), 2),
    }
