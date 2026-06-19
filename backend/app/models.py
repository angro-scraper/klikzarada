from datetime import datetime, date
import random
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    city: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    seller_pin: Mapped[str] = mapped_column(String(20), default=lambda: str(random.randint(100000, 999999)), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="store")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    original_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    discounted_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    discount_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="RSD")
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_type: Mapped[str] = mapped_column(String(40), default="unknown")
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pickup_window: Mapped[str | None] = mapped_column(String(120), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(60), default="candidate", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    store = relationship("Store", back_populates="products")
    reservations = relationship("Reservation", back_populates="product")


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    customer_name: Mapped[str] = mapped_column(String(255))
    customer_phone: Mapped[str] = mapped_column(String(80))
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(60), default="pending", index=True)
    reservation_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_status: Mapped[str] = mapped_column(String(60), default="unpaid", index=True)
    payment_provider: Mapped[str | None] = mapped_column(String(80), default="demo", nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(80), default="online_card_demo", nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(10), default="RSD")
    gross_amount: Mapped[float] = mapped_column(Float, default=0.0)
    loyalty_discount_percent: Mapped[float] = mapped_column(Float, default=0.0)
    loyalty_discount_amount: Mapped[float] = mapped_column(Float, default=0.0)
    payable_amount: Mapped[float] = mapped_column(Float, default=0.0)
    platform_fee_percent: Mapped[float] = mapped_column(Float, default=25.0)
    platform_fee_amount: Mapped[float] = mapped_column(Float, default=0.0)
    seller_net_amount: Mapped[float] = mapped_column(Float, default=0.0)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    seller_payout_status: Mapped[str] = mapped_column(String(60), default="not_ready", index=True)
    seller_payout_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    seller_payout_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    seller_payout_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="reservations")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_type: Mapped[str] = mapped_column(String(80), default="web_page")
    crawl_frequency: Mapped[str] = mapped_column(String(80), default="daily")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(60), default="pending")
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
