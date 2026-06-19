from datetime import date, datetime
from pydantic import BaseModel, Field


class StoreCreate(BaseModel):
    name: str
    city: str | None = None
    address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    website: str | None = None
    phone: str | None = None
    seller_pin: str | None = Field(default=None, min_length=4, max_length=20)
    verified: bool = False
    seller_type: str = "business"
    agreement_accepted: bool = False
    agreement_version: str | None = None
    agreement_accepted_at: datetime | None = None
    liability_accepted: bool = False
    commission_terms_accepted: bool = False
    blocked: bool = False
    blocked_reason: str | None = None
    blocked_at: datetime | None = None
    loyalty_points: int = 0
    loyalty_tier: str = "start"
    late_payment_count: int = 0


class StorePublicOut(BaseModel):
    id: int
    name: str
    city: str | None = None
    address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    website: str | None = None
    phone: str | None = None
    verified: bool = False
    seller_type: str = "business"
    agreement_accepted: bool = False
    liability_accepted: bool = False
    commission_terms_accepted: bool = False
    blocked: bool = False
    blocked_reason: str | None = None
    loyalty_points: int = 0
    loyalty_tier: str = "start"
    late_payment_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class StoreOut(StorePublicOut):
    seller_pin: str


class ProductCreate(BaseModel):
    store_id: int | None = None
    name: str
    category: str | None = None
    original_price: float | None = None
    discounted_price: float | None = None
    discount_percent: float | None = None
    currency: str = "RSD"
    expiry_date: date | None = None
    expiry_type: str = "unknown"
    quantity: int | None = None
    pickup_window: str | None = None
    description: str | None = None
    image_url: str | None = None
    source_url: str | None = None
    confidence_score: float = Field(default=0.5, ge=0, le=1)
    status: str = "candidate"


class ProductOut(ProductCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductPublicOut(ProductOut):
    store_name: str | None = None
    store_city: str | None = None
    store_address: str | None = None
    store_phone: str | None = None
    store_latitude: float | None = None
    store_longitude: float | None = None
    distance_km: float | None = None
    available_quantity: int | None = None


class ReservationCreate(BaseModel):
    product_id: int
    customer_name: str = Field(min_length=2, max_length=255)
    customer_phone: str = Field(min_length=5, max_length=80)
    customer_email: str | None = None
    quantity: int = Field(default=1, ge=1, le=50)
    note: str | None = None


class PaymentQuoteRequest(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=50)
    customer_phone: str | None = None


class PaymentPayRequest(BaseModel):
    customer_phone: str = Field(min_length=5, max_length=80)
    payment_method: str = "online_card_demo"


class PaymentQuoteOut(BaseModel):
    product_id: int
    quantity: int
    currency: str = "RSD"
    gross_amount: float
    loyalty_discount_percent: float
    loyalty_discount_amount: float
    payable_amount: float
    platform_fee_percent: float
    platform_fee_amount: float
    seller_net_amount: float
    previous_successful_pickups: int = 0
    message: str | None = None


class ReservationOut(BaseModel):
    id: int
    product_id: int
    product_name: str | None = None
    store_name: str | None = None
    customer_name: str
    customer_phone: str
    customer_email: str | None = None
    quantity: int
    status: str
    reservation_code: str
    note: str | None = None
    payment_status: str = "unpaid"
    payment_provider: str | None = None
    payment_method: str | None = None
    payment_reference: str | None = None
    currency: str = "RSD"
    gross_amount: float = 0
    loyalty_discount_percent: float = 0
    loyalty_discount_amount: float = 0
    payable_amount: float = 0
    platform_fee_percent: float = 25
    platform_fee_amount: float = 0
    seller_net_amount: float = 0
    paid_at: datetime | None = None
    seller_payout_status: str = "not_ready"
    seller_payout_reference: str | None = None
    seller_payout_note: str | None = None
    seller_payout_at: datetime | None = None
    seller_invoice_due_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SourceCreate(BaseModel):
    name: str
    url: str
    city: str | None = None
    source_type: str = "web_page"
    crawl_frequency: str = "daily"
    active: bool = True


class SourceOut(SourceCreate):
    id: int
    last_checked_at: datetime | None = None

    class Config:
        from_attributes = True


class CrawlRequest(BaseModel):
    source_id: int | None = None
    url: str | None = None
    store_name: str | None = None
    city: str | None = None


class StoreLocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class SellerStoreLocationUpdate(StoreLocationUpdate):
    store_id: int
    pin: str = Field(min_length=4, max_length=20)


class SellerLoginRequest(BaseModel):
    store_id: int
    pin: str = Field(min_length=4, max_length=20)


class SellerProductCreate(ProductCreate):
    pin: str = Field(min_length=4, max_length=20)


class SellerProductStatusUpdate(BaseModel):
    store_id: int
    pin: str = Field(min_length=4, max_length=20)
    status: str


class SellerAgreementAccept(BaseModel):
    store_id: int
    pin: str = Field(min_length=4, max_length=20)
    seller_type: str = "business"
    agreement_accepted: bool = True
    liability_accepted: bool = True
    commission_terms_accepted: bool = True
    food_photo_required_accepted: bool = True
    invoice_terms_accepted: bool = True


class SellerReservationStatusUpdate(BaseModel):
    store_id: int
    pin: str = Field(min_length=4, max_length=20)
    status: str

class PaymentCheckoutOut(BaseModel):
    reservation_code: str
    provider: str
    provider_ready: bool
    method: str
    checkout_url: str
    reservation_url: str
    reservation_qr_url: str
    payment_qr_url: str | None = None
    provider_redirect_url: str | None = None
    instructions: str
    provider_message: str | None = None
    ips_payload: str | None = None
    amount: float = 0
    currency: str = "RSD"
    provider_amount: float | None = None
    provider_currency: str | None = None
    can_pay_on_pickup: bool = True
    platform_fee_percent: float = 25
    platform_fee_amount: float = 0
    seller_net_amount: float = 0


class FinanceConfirmPaymentRequest(BaseModel):
    reference: str | None = None
    note: str | None = None
    provider: str = "ips_qr"


class FinancePayoutUpdateRequest(BaseModel):
    seller_payout_status: str = Field(pattern="^(not_ready|pending|paid|blocked|commission_due|invoice_sent|commission_paid)$")
    reference: str | None = None
    note: str | None = None
