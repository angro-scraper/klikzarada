from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class SellerCommissionLedger(Base):
    __tablename__ = "seller_commission_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    order_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    invoice_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(80), default="COMMISSION")
    direction: Mapped[str] = mapped_column(String(20), default="DEBIT", index=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="RSD")
    commission_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SellerInvoice(Base):
    __tablename__ = "seller_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    invoice_number: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(60), default="DRAFT", index=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    subtotal_amount: Mapped[float] = mapped_column(Float, default=0.0)
    adjustment_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    amount_paid: Mapped[float] = mapped_column(Float, default=0.0)
    amount_due: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="RSD")
    issued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dispute_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SellerInvoiceLine(Base):
    __tablename__ = "seller_invoice_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("seller_invoices.id"), index=True)
    ledger_entry_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    order_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    line_type: Mapped[str] = mapped_column(String(80), default="COMMISSION")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="RSD")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SellerInvoicePaymentRequest(Base):
    __tablename__ = "seller_invoice_payment_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    seller_invoice_id: Mapped[int] = mapped_column(ForeignKey("seller_invoices.id"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80), default="BANK_TRANSFER")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="RSD")
    status: Mapped[str] = mapped_column(String(60), default="PENDING", index=True)
    provider_reference: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SellerInvoicePayment(Base):
    __tablename__ = "seller_invoice_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    seller_invoice_id: Mapped[int] = mapped_column(ForeignKey("seller_invoices.id"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80), default="BANK_TRANSFER")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="RSD")
    status: Mapped[str] = mapped_column(String(60), default="CONFIRMED", index=True)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProviderWebhookEvent(Base):
    __tablename__ = "provider_webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    event_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_event_id: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(60), default="RECEIVED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FinanceReconciliationException(Base):
    __tablename__ = "finance_reconciliation_exceptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    seller_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    invoice_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(120), default="GENERAL")
    status: Mapped[str] = mapped_column(String(60), default="OPEN", index=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="RSD")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class FinanceAuditLog(Base):
    __tablename__ = "finance_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_admin_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(160), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    before_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
