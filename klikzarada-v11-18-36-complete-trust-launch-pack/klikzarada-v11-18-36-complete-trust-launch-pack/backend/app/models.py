from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(160), nullable=False)
    email = Column(String(160), unique=True, index=True, nullable=False)
    password_hash = Column(String(300), nullable=False)
    role = Column(String(30), default="korisnik")
    status = Column(String(30), default="active")
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    phone = Column(String(80), nullable=True)
    city = Column(String(100), nullable=True)
    age_group = Column(String(40), nullable=True)
    gender = Column(String(40), nullable=True)
    interests = Column(Text, nullable=True)
    device = Column(String(80), nullable=True)
    level = Column(String(40), default="Bronza")
    quality_score = Column(Float, default=100.0)
    balance_rsd = Column(Float, default=0)
    pending_rsd = Column(Float, default=0)
    lifetime_earned_rsd = Column(Float, default=0)
    payment_method = Column(String(80), nullable=True)
    payment_details = Column(Text, nullable=True)
    referral_code = Column(String(40), unique=True, index=True, nullable=True)
    referred_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    company_name = Column(String(180), nullable=True)
    company_pib = Column(String(80), nullable=True)
    company_website = Column(String(300), nullable=True)
    company_activity = Column(String(160), nullable=True)
    company_city = Column(String(100), nullable=True)
    contact_person = Column(String(160), nullable=True)
    advertiser_verified = Column(Boolean, default=False)
    advertiser_budget_rsd = Column(Float, default=0)
    advertiser_reserved_rsd = Column(Float, default=0)
    advertiser_spent_rsd = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    tasks = relationship("Task", back_populates="advertiser")
    submissions = relationship("TaskSubmission", back_populates="user")
    withdrawals = relationship("Withdrawal", back_populates="user")
    transactions = relationship("WalletTransaction", back_populates="user")
    budget_transactions = relationship("AdvertiserBudgetTransaction", back_populates="advertiser")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(220), nullable=False)
    category = Column(String(80), default="Promo")
    task_type = Column(String(80), nullable=False)
    target_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=False)
    instructions = Column(Text, nullable=False)
    proof_required = Column(Text, nullable=False)
    example_proof = Column(Text, nullable=True)
    reward_rsd = Column(Float, nullable=False)
    platform_fee_percent = Column(Float, default=20.0)
    total_slots = Column(Integer, default=100)
    used_slots = Column(Integer, default=0)
    reserved_slots = Column(Integer, default=0)
    estimated_minutes = Column(Integer, default=5)
    deadline_text = Column(String(120), nullable=True)
    target_city = Column(String(100), nullable=True)
    target_age_group = Column(String(40), nullable=True)
    target_interests = Column(Text, nullable=True)
    min_user_level = Column(String(40), default="Bronza")
    proof_file_required = Column(Boolean, default=False)
    featured = Column(Boolean, default=False)
    status = Column(String(30), default="pending")
    moderation_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    advertiser = relationship("User", back_populates="tasks")
    submissions = relationship("TaskSubmission", back_populates="task")

class TaskSubmission(Base):
    __tablename__ = "task_submissions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    proof = Column(Text, nullable=False)
    proof_file = Column(String(500), nullable=True)
    status = Column(String(30), default="pending")
    reward_rsd = Column(Float, nullable=False)
    platform_fee_rsd = Column(Float, default=0)
    advertiser_cost_rsd = Column(Float, default=0)
    review_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="submissions")
    task = relationship("Task", back_populates="submissions")

class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_rsd = Column(Float, nullable=False)
    tx_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="transactions")

class Withdrawal(Base):
    __tablename__ = "withdrawals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_rsd = Column(Float, nullable=False)
    payment_method = Column(String(80), default="bank_transfer")
    payment_details = Column(Text, nullable=False)
    status = Column(String(30), default="pending")
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="withdrawals")

class AdvertiserBudgetTransaction(Base):
    __tablename__ = "advertiser_budget_transactions"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_rsd = Column(Float, nullable=False)
    tx_type = Column(String(60), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    advertiser = relationship("User", back_populates="budget_transactions")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(120), nullable=False)
    entity_type = Column(String(80), nullable=False)
    entity_id = Column(Integer, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    role_target = Column(String(40), nullable=True)  # korisnik, oglasivac, admin, all
    title = Column(String(220), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(30), default="unread")  # unread, read
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(220), nullable=False)
    category = Column(String(80), default="Opšte")
    priority = Column(String(40), default="normal")
    status = Column(String(40), default="open")  # open, waiting, closed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    messages = relationship("SupportMessage", back_populates="ticket")

class SupportMessage(Base):
    __tablename__ = "support_messages"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("SupportTicket", back_populates="messages")
    sender = relationship("User")

class CampaignTemplate(Base):
    __tablename__ = "campaign_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(180), nullable=False)
    category = Column(String(80), nullable=False)
    task_type = Column(String(80), nullable=False)
    description = Column(Text, nullable=False)
    instructions = Column(Text, nullable=False)
    proof_required = Column(Text, nullable=False)
    suggested_reward_rsd = Column(Float, default=60)
    suggested_slots = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PromoCode(Base):
    __tablename__ = "promo_codes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(60), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    discount_percent = Column(Float, default=0)
    bonus_budget_rsd = Column(Float, default=0)
    max_uses = Column(Integer, default=100)
    used_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PromoCodeUse(Base):
    __tablename__ = "promo_code_uses"
    id = Column(Integer, primary_key=True, index=True)
    promo_code_id = Column(Integer, ForeignKey("promo_codes.id"), nullable=False)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    promo = relationship("PromoCode")
    advertiser = relationship("User")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invoice_no = Column(String(80), unique=True, index=True, nullable=False)
    invoice_type = Column(String(50), default="predracun")  # predracun, faktura, izvestaj
    amount_rsd = Column(Float, nullable=False)
    status = Column(String(40), default="draft")  # draft, issued, paid, cancelled
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    issued_at = Column(DateTime, nullable=True)

    advertiser = relationship("User")



# -----------------------------
# V5 SCALE & AUTOMATION MODELS
# -----------------------------

class AdvertiserPlan(Base):
    __tablename__ = "advertiser_plans"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    monthly_fee_rsd = Column(Float, default=0)
    platform_fee_percent = Column(Float, default=20)
    max_active_campaigns = Column(Integer, default=3)
    features = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdvertiserSubscription(Base):
    __tablename__ = "advertiser_subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("advertiser_plans.id"), nullable=False)
    status = Column(String(40), default="active")
    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    advertiser = relationship("User")
    plan = relationship("AdvertiserPlan")


class AudienceSegment(Base):
    __tablename__ = "audience_segments"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(160), nullable=False)
    city = Column(String(120), nullable=True)
    age_group = Column(String(80), nullable=True)
    interests = Column(Text, nullable=True)
    min_user_level = Column(String(40), default="Bronza")
    min_quality_score = Column(Float, default=80)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    advertiser = relationship("User")


class Dispute(Base):
    __tablename__ = "disputes"
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("task_submissions.id"), nullable=False)
    opened_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(40), default="open")  # open, accepted, rejected, closed
    admin_decision = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    submission = relationship("TaskSubmission")
    opened_by = relationship("User")


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge = Column(String(120), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(120), nullable=False)
    token = Column(String(120), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    advertiser = relationship("User")


class AutomationRule(Base):
    __tablename__ = "automation_rules"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    scope = Column(String(40), default="advertiser")  # advertiser, admin
    name = Column(String(160), nullable=False)
    trigger_text = Column(Text, nullable=False)
    action_text = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")


class SavedReport(Base):
    __tablename__ = "saved_reports"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(160), nullable=False)
    report_type = Column(String(80), default="campaigns")
    query_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")



# -----------------------------
# V6 ENTERPRISE & PRODUCTION MODELS
# -----------------------------

class FeatureFlag(Base):
    __tablename__ = "feature_flags"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(120), unique=True, index=True, nullable=False)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemSetting(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(120), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class SecurityEvent(Base):
    __tablename__ = "security_events"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String(120), nullable=False)
    severity = Column(String(40), default="low")  # low, medium, high, critical
    ip_address = Column(String(120), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class KycDocument(Base):
    __tablename__ = "kyc_documents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doc_type = Column(String(80), default="identity")
    file_path = Column(String(500), nullable=True)
    status = Column(String(40), default="pending")  # pending, approved, rejected
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    user = relationship("User")


class DataExportRequest(Base):
    __tablename__ = "data_export_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    export_format = Column(String(40), default="csv")
    status = Column(String(40), default="pending")  # pending, ready, rejected
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    user = relationship("User")


class SalesLead(Base):
    __tablename__ = "sales_leads"
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(180), nullable=False)
    contact_name = Column(String(160), nullable=True)
    email = Column(String(160), nullable=True)
    phone = Column(String(120), nullable=True)
    source = Column(String(120), default="manual")
    status = Column(String(60), default="new")  # new, contacted, demo, proposal, won, lost
    potential_budget_rsd = Column(Float, default=0)
    notes = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(160), nullable=False)
    url = Column(String(500), nullable=False)
    events = Column(Text, default="submission.approved,submission.rejected,campaign.status_changed")
    secret = Column(String(160), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    advertiser = relationship("User")


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("webhook_endpoints.id"), nullable=False)
    event_type = Column(String(120), nullable=False)
    payload = Column(Text, nullable=False)
    status = Column(String(60), default="queued")  # queued, sent, failed
    response_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    endpoint = relationship("WebhookEndpoint")


class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    full_name = Column(String(160), nullable=False)
    email = Column(String(160), nullable=False)
    role = Column(String(80), default="viewer")  # owner, manager, finance, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    advertiser = relationship("User")


class OnboardingItem(Base):
    __tablename__ = "onboarding_items"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scope = Column(String(60), default="advertiser")
    title = Column(String(180), nullable=False)
    status = Column(String(40), default="open")  # open, done
    sort_order = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")



# -----------------------------
# V7 AI MARKETPLACE & ANALYTICS MODELS
# -----------------------------

class AIReviewRule(Base):
    __tablename__ = "ai_review_rules"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(String(80), default="proof_quality")  # proof_quality, fraud, campaign_quality
    severity = Column(String(40), default="medium")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AIReviewResult(Base):
    __tablename__ = "ai_review_results"
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("task_submissions.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    score = Column(Float, default=0)
    risk_level = Column(String(40), default="low")
    suggestion = Column(Text, nullable=True)
    reasons = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("TaskSubmission")
    task = relationship("Task")


class TaskRecommendation(Base):
    __tablename__ = "task_recommendations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    score = Column(Float, default=0)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    task = relationship("Task")


class MarketplaceCategory(Base):
    __tablename__ = "marketplace_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MarketplaceOffer(Base):
    __tablename__ = "marketplace_offers"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("marketplace_categories.id"), nullable=True)
    title = Column(String(220), nullable=False)
    description = Column(Text, nullable=False)
    price_rsd = Column(Float, default=0)
    delivery_days = Column(Integer, default=3)
    status = Column(String(40), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("MarketplaceCategory")


class MarketplaceOrder(Base):
    __tablename__ = "marketplace_orders"
    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("marketplace_offers.id"), nullable=False)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(40), default="pending")  # pending, in_progress, delivered, cancelled
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)

    offer = relationship("MarketplaceOffer")
    advertiser = relationship("User")


class PayoutBatch(Base):
    __tablename__ = "payout_batches"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(180), nullable=False)
    status = Column(String(40), default="draft")  # draft, ready, paid, cancelled
    total_amount_rsd = Column(Float, default=0)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    created_by = relationship("User")


class PayoutBatchItem(Base):
    __tablename__ = "payout_batch_items"
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("payout_batches.id"), nullable=False)
    withdrawal_id = Column(Integer, ForeignKey("withdrawals.id"), nullable=False)
    amount_rsd = Column(Float, default=0)
    status = Column(String(40), default="included")

    batch = relationship("PayoutBatch")
    withdrawal = relationship("Withdrawal")


class FraudCase(Base):
    __tablename__ = "fraud_cases"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(180), nullable=False)
    severity = Column(String(40), default="medium")
    status = Column(String(40), default="open")  # open, investigating, resolved, dismissed
    description = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    user = relationship("User")


class ContentPage(Base):
    __tablename__ = "content_pages"
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(160), unique=True, index=True, nullable=False)
    title = Column(String(220), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(40), default="draft")  # draft, published
    seo_title = Column(String(220), nullable=True)
    seo_description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class EmailTemplate(Base):
    __tablename__ = "email_templates"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(160), unique=True, nullable=False)
    subject = Column(String(220), nullable=False)
    body = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class GrowthExperiment(Base):
    __tablename__ = "growth_experiments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(180), nullable=False)
    hypothesis = Column(Text, nullable=True)
    metric = Column(String(120), nullable=True)
    status = Column(String(40), default="planned")  # planned, running, won, lost, stopped
    result_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(120), nullable=False)
    users_count = Column(Integer, default=0)
    advertisers_count = Column(Integer, default=0)
    active_tasks = Column(Integer, default=0)
    approved_submissions = Column(Integer, default=0)
    platform_revenue_rsd = Column(Float, default=0)
    rewards_rsd = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class CampaignFunnelEvent(Base):
    __tablename__ = "campaign_funnel_events"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    event_type = Column(String(120), nullable=False)
    value = Column(Float, default=0)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    advertiser = relationship("User")
    task = relationship("Task")


class InternalMessage(Base):
    __tablename__ = "internal_messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    subject = Column(String(220), nullable=False)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sender = relationship("User", foreign_keys=[sender_id])
    recipient = relationship("User", foreign_keys=[recipient_id])


class SavedView(Base):
    __tablename__ = "saved_views"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(160), nullable=False)
    view_type = Column(String(80), default="admin_table")
    url = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")



# -----------------------------
# V8 COMMAND CENTER MODELS
# -----------------------------

class PaymentIntentV8(Base):
    __tablename__ = "payment_intents_v8"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_rsd = Column(Float, nullable=False)
    reference = Column(String(120), unique=True, index=True, nullable=False)
    method = Column(String(80), default="manual")
    status = Column(String(40), default="pending")  # pending, confirmed, rejected
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)

    advertiser = relationship("User")


class CommandItemV8(Base):
    __tablename__ = "command_items_v8"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(220), nullable=False)
    area = Column(String(80), default="ops")  # ops, finance, security, growth, support
    priority = Column(String(40), default="medium")
    status = Column(String(40), default="open")  # open, doing, done, ignored
    link = Column(String(500), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class HelpArticleV8(Base):
    __tablename__ = "help_articles_v8"
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(160), unique=True, index=True, nullable=False)
    title = Column(String(220), nullable=False)
    body = Column(Text, nullable=False)
    audience = Column(String(40), default="all")
    status = Column(String(40), default="published")
    updated_at = Column(DateTime, default=datetime.utcnow)


class AnnouncementBannerV8(Base):
    __tablename__ = "announcement_banners_v8"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(180), nullable=False)
    body = Column(Text, nullable=False)
    audience = Column(String(40), default="all")
    severity = Column(String(40), default="info")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class StatusIncidentV8(Base):
    __tablename__ = "status_incidents_v8"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(220), nullable=False)
    status = Column(String(60), default="investigating")
    impact = Column(String(60), default="minor")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class ReleaseChecklistV8(Base):
    __tablename__ = "release_checklist_v8"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(220), nullable=False)
    status = Column(String(40), default="open")
    owner = Column(String(120), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)


class EmailOutboxV8(Base):
    __tablename__ = "email_outbox_v8"
    id = Column(Integer, primary_key=True, index=True)
    recipient_email = Column(String(180), nullable=False)
    subject = Column(String(220), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(40), default="queued")
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)


class JobItemV8(Base):
    __tablename__ = "job_items_v8"
    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(String(120), nullable=False)
    payload = Column(Text, nullable=True)
    status = Column(String(40), default="queued")
    attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)



# -----------------------------
# V9 LAUNCH & REVENUE OS MODELS
# -----------------------------

class LaunchCampaignV9(Base):
    __tablename__ = "v9_launch_campaigns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(180), nullable=False)
    channel = Column(String(80), default="manual")  # facebook, linkedin, email, groups, agencies
    goal = Column(Text, nullable=True)
    budget_rsd = Column(Float, default=0)
    status = Column(String(40), default="planned")  # planned, running, paused, done
    start_date = Column(String(40), nullable=True)
    end_date = Column(String(40), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class LaunchTaskV9(Base):
    __tablename__ = "v9_launch_tasks"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("v9_launch_campaigns.id"), nullable=True)
    title = Column(String(220), nullable=False)
    owner = Column(String(120), default="admin")
    priority = Column(String(40), default="medium")
    status = Column(String(40), default="open")  # open, doing, done, blocked
    due_date = Column(String(40), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("LaunchCampaignV9")


class AffiliatePartnerV9(Base):
    __tablename__ = "v9_affiliate_partners"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(180), nullable=False)
    partner_type = Column(String(80), default="creator")  # creator, agency, student, publisher, consultant
    email = Column(String(160), nullable=True)
    phone = Column(String(100), nullable=True)
    code = Column(String(80), unique=True, index=True, nullable=False)
    commission_percent = Column(Float, default=10)
    status = Column(String(40), default="active")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AffiliateDealV9(Base):
    __tablename__ = "v9_affiliate_deals"
    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("v9_affiliate_partners.id"), nullable=False)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount_rsd = Column(Float, default=0)
    commission_rsd = Column(Float, default=0)
    status = Column(String(40), default="pending")  # pending, approved, paid, rejected
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    partner = relationship("AffiliatePartnerV9")
    advertiser = relationship("User")


class SalesScriptV9(Base):
    __tablename__ = "v9_sales_scripts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(180), nullable=False)
    target = Column(String(80), default="advertiser")  # advertiser, partner, group_admin
    script_text = Column(Text, nullable=False)
    status = Column(String(40), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class OutreachContactV9(Base):
    __tablename__ = "v9_outreach_contacts"
    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(180), nullable=False)
    contact_name = Column(String(160), nullable=True)
    channel = Column(String(80), default="manual")
    email = Column(String(160), nullable=True)
    phone = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    status = Column(String(40), default="new")  # new, contacted, interested, demo, won, lost
    potential_value_rsd = Column(Float, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class OutreachActivityV9(Base):
    __tablename__ = "v9_outreach_activities"
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("v9_outreach_contacts.id"), nullable=False)
    activity_type = Column(String(80), default="note")  # call, email, message, meeting, note
    result = Column(String(80), default="open")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("OutreachContactV9")


class RevenueForecastV9(Base):
    __tablename__ = "v9_revenue_forecasts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(180), nullable=False)
    scenario = Column(String(80), default="base")  # conservative, base, aggressive
    period = Column(String(80), default="monthly")
    created_at = Column(DateTime, default=datetime.utcnow)


class RevenueForecastLineV9(Base):
    __tablename__ = "v9_revenue_forecast_lines"
    id = Column(Integer, primary_key=True, index=True)
    forecast_id = Column(Integer, ForeignKey("v9_revenue_forecasts.id"), nullable=False)
    label = Column(String(180), nullable=False)
    advertisers_count = Column(Integer, default=0)
    avg_budget_rsd = Column(Float, default=0)
    platform_fee_percent = Column(Float, default=20)
    estimated_revenue_rsd = Column(Float, default=0)
    note = Column(Text, nullable=True)

    forecast = relationship("RevenueForecastV9")


class BackupSnapshotV9(Base):
    __tablename__ = "v9_backup_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(180), nullable=False)
    snapshot_type = Column(String(80), default="manual")  # manual, pre_release, daily
    status = Column(String(40), default="created")
    file_hint = Column(String(500), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GoLiveCheckV9(Base):
    __tablename__ = "v9_golive_checks"
    id = Column(Integer, primary_key=True, index=True)
    area = Column(String(80), default="ops")
    title = Column(String(220), nullable=False)
    status = Column(String(40), default="open")  # open, done, blocked
    importance = Column(String(40), default="high")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CompetitorNoteV9(Base):
    __tablename__ = "v9_competitor_notes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(180), nullable=False)
    url = Column(String(500), nullable=True)
    strengths = Column(Text, nullable=True)
    weaknesses = Column(Text, nullable=True)
    our_angle = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RoadmapItemV9(Base):
    __tablename__ = "v9_roadmap_items"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(220), nullable=False)
    phase = Column(String(80), default="next")
    priority = Column(String(40), default="medium")
    status = Column(String(40), default="planned")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CustomerSuccessNoteV9(Base):
    __tablename__ = "v9_customer_success_notes"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(220), nullable=False)
    note = Column(Text, nullable=False)
    health = Column(String(40), default="green")  # green, yellow, red
    next_action = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    advertiser = relationship("User")


class PricingExperimentV9(Base):
    __tablename__ = "v9_pricing_experiments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(180), nullable=False)
    commission_percent = Column(Float, default=20)
    monthly_fee_rsd = Column(Float, default=0)
    target_segment = Column(String(120), default="all")
    status = Column(String(40), default="planned")
    result_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PressKitAssetV9(Base):
    __tablename__ = "v9_press_kit_assets"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(180), nullable=False)
    asset_type = Column(String(80), default="text")  # text, logo, screenshot, pdf
    body = Column(Text, nullable=True)
    file_url = Column(String(500), nullable=True)
    status = Column(String(40), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)



# -----------------------------
# V10 AUTOMATION, DATA STUDIO & CLIENT PORTAL MODELS
# -----------------------------

class WorkflowTemplateV10(Base):
    __tablename__ = "v10_workflow_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(180), nullable=False)
    trigger_type = Column(String(100), default="manual")
    description = Column(Text, nullable=True)
    status = Column(String(40), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkflowRunV10(Base):
    __tablename__ = "v10_workflow_runs"
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("v10_workflow_templates.id"), nullable=False)
    status = Column(String(40), default="queued")  # queued, running, done, failed
    context = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    template = relationship("WorkflowTemplateV10")


class WorkflowStepRunV10(Base):
    __tablename__ = "v10_workflow_step_runs"
    id = Column(Integer, primary_key=True, index=True)
    workflow_run_id = Column(Integer, ForeignKey("v10_workflow_runs.id"), nullable=False)
    step_name = Column(String(180), nullable=False)
    status = Column(String(40), default="queued")
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workflow_run = relationship("WorkflowRunV10")


class SurveyV10(Base):
    __tablename__ = "v10_surveys"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(220), nullable=False)
    description = Column(Text, nullable=True)
    reward_rsd = Column(Float, default=0)
    status = Column(String(40), default="draft")  # draft, active, closed
    created_at = Column(DateTime, default=datetime.utcnow)

    advertiser = relationship("User")


class SurveyQuestionV10(Base):
    __tablename__ = "v10_survey_questions"
    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("v10_surveys.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(80), default="text")  # text, single_choice, rating
    options_text = Column(Text, nullable=True)
    sort_order = Column(Integer, default=100)

    survey = relationship("SurveyV10")


class SurveyResponseV10(Base):
    __tablename__ = "v10_survey_responses"
    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("v10_surveys.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    answers_text = Column(Text, nullable=False)
    status = Column(String(40), default="submitted")
    created_at = Column(DateTime, default=datetime.utcnow)

    survey = relationship("SurveyV10")
    user = relationship("User")


class UTMCampaignV10(Base):
    __tablename__ = "v10_utm_campaigns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(180), nullable=False)
    source = Column(String(120), default="manual")
    medium = Column(String(120), default="referral")
    campaign = Column(String(180), nullable=False)
    target_url = Column(String(500), nullable=True)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    spend_rsd = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConversionGoalV10(Base):
    __tablename__ = "v10_conversion_goals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(180), nullable=False)
    goal_type = Column(String(100), default="registration")
    value_rsd = Column(Float, default=0)
    status = Column(String(40), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class ConversionEventV10(Base):
    __tablename__ = "v10_conversion_events"
    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("v10_conversion_goals.id"), nullable=False)
    utm_campaign_id = Column(Integer, ForeignKey("v10_utm_campaigns.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    value_rsd = Column(Float, default=0)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    goal = relationship("ConversionGoalV10")
    utm_campaign = relationship("UTMCampaignV10")
    user = relationship("User")


class ClientPortalProjectV10(Base):
    __tablename__ = "v10_client_portal_projects"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(220), nullable=False)
    status = Column(String(40), default="active")
    budget_rsd = Column(Float, default=0)
    health = Column(String(40), default="green")
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    advertiser = relationship("User")


class ClientPortalUpdateV10(Base):
    __tablename__ = "v10_client_portal_updates"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("v10_client_portal_projects.id"), nullable=False)
    title = Column(String(220), nullable=False)
    body = Column(Text, nullable=False)
    visibility = Column(String(40), default="client")  # internal, client
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("ClientPortalProjectV10")


class ContractV10(Base):
    __tablename__ = "v10_contracts"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(220), nullable=False)
    contract_type = Column(String(100), default="campaign")
    amount_rsd = Column(Float, default=0)
    status = Column(String(40), default="draft")  # draft, sent, signed, cancelled
    terms_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    advertiser = relationship("User")


class ContractMilestoneV10(Base):
    __tablename__ = "v10_contract_milestones"
    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("v10_contracts.id"), nullable=False)
    title = Column(String(220), nullable=False)
    amount_rsd = Column(Float, default=0)
    status = Column(String(40), default="open")
    due_date = Column(String(40), nullable=True)

    contract = relationship("ContractV10")


class DataStudioDashboardV10(Base):
    __tablename__ = "v10_data_studio_dashboards"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(220), nullable=False)
    audience = Column(String(40), default="admin")
    status = Column(String(40), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")


class DataStudioWidgetV10(Base):
    __tablename__ = "v10_data_studio_widgets"
    id = Column(Integer, primary_key=True, index=True)
    dashboard_id = Column(Integer, ForeignKey("v10_data_studio_dashboards.id"), nullable=False)
    title = Column(String(180), nullable=False)
    widget_type = Column(String(80), default="metric")
    metric_key = Column(String(120), nullable=True)
    config_text = Column(Text, nullable=True)
    sort_order = Column(Integer, default=100)

    dashboard = relationship("DataStudioDashboardV10")


class ModerationQueueV10(Base):
    __tablename__ = "v10_moderation_queue"
    id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String(80), nullable=False)
    item_id = Column(Integer, nullable=True)
    priority = Column(String(40), default="medium")
    status = Column(String(40), default="open")
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SmartSegmentRuleV10(Base):
    __tablename__ = "v10_smart_segment_rules"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(180), nullable=False)
    rule_text = Column(Text, nullable=False)
    estimated_users = Column(Integer, default=0)
    status = Column(String(40), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class QualityRuleV10(Base):
    __tablename__ = "v10_quality_rules"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(180), nullable=False)
    applies_to = Column(String(80), default="submission")
    threshold = Column(Float, default=0)
    action = Column(String(120), default="manual_review")
    status = Column(String(40), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class ApiUsageLogV10(Base):
    __tablename__ = "v10_api_usage_logs"
    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, nullable=True)
    endpoint = Column(String(220), nullable=False)
    status_code = Column(Integer, default=200)
    latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class RevenueGoalV10(Base):
    __tablename__ = "v10_revenue_goals"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(180), nullable=False)
    target_rsd = Column(Float, default=0)
    current_rsd = Column(Float, default=0)
    period = Column(String(80), default="monthly")
    status = Column(String(40), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class ExperimentVariantV10(Base):
    __tablename__ = "v10_experiment_variants"
    id = Column(Integer, primary_key=True, index=True)
    experiment_name = Column(String(180), nullable=False)
    variant_name = Column(String(120), nullable=False)
    traffic_percent = Column(Float, default=50)
    conversions = Column(Integer, default=0)
    revenue_rsd = Column(Float, default=0)
    status = Column(String(40), default="running")


class PartnerPayoutV10(Base):
    __tablename__ = "v10_partner_payouts"
    id = Column(Integer, primary_key=True, index=True)
    partner_name = Column(String(180), nullable=False)
    amount_rsd = Column(Float, default=0)
    status = Column(String(40), default="pending")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class OpsPlaybookV10(Base):
    __tablename__ = "v10_ops_playbooks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(220), nullable=False)
    trigger_text = Column(Text, nullable=True)
    steps_text = Column(Text, nullable=False)
    status = Column(String(40), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)



# -----------------------------
# V11 REAL LAUNCH PACK MODELS
# -----------------------------

class EmailVerificationTokenV11(Base):
    __tablename__ = "v11_email_verification_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(160), unique=True, index=True, nullable=False)
    status = Column(String(40), default="pending")  # pending, used, expired
    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)

    user = relationship("User")


class PasswordResetTokenV11(Base):
    __tablename__ = "v11_password_reset_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(160), unique=True, index=True, nullable=False)
    status = Column(String(40), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)

    user = relationship("User")


class LoginAttemptV11(Base):
    __tablename__ = "v11_login_attempts"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(180), nullable=True)
    success = Column(Boolean, default=False)
    ip_address = Column(String(120), nullable=True)
    user_agent = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminTwoFactorCodeV11(Base):
    __tablename__ = "v11_admin_two_factor_codes"
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(String(20), nullable=False)
    status = Column(String(40), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)

    admin = relationship("User")


class UserDeviceSessionV11(Base):
    __tablename__ = "v11_user_device_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_label = Column(String(160), nullable=True)
    ip_address = Column(String(120), nullable=True)
    user_agent = Column(Text, nullable=True)
    status = Column(String(40), default="active")
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class PayoutMethodV11(Base):
    __tablename__ = "v11_payout_methods"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    method_type = Column(String(80), default="bank")  # bank, paypal, manual
    account_holder = Column(String(180), nullable=True)
    account_data = Column(Text, nullable=False)
    status = Column(String(40), default="pending")  # pending, verified, rejected
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class PayoutHoldV11(Base):
    __tablename__ = "v11_payout_holds"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_rsd = Column(Float, default=0)
    reason = Column(Text, nullable=True)
    status = Column(String(40), default="active")  # active, released, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class PayoutExportV11(Base):
    __tablename__ = "v11_payout_exports"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(180), nullable=False)
    status = Column(String(40), default="created")
    csv_path = Column(String(500), nullable=True)
    total_amount_rsd = Column(Float, default=0)
    rows_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProofFileReviewV11(Base):
    __tablename__ = "v11_proof_file_reviews"
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("task_submissions.id"), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_hash = Column(String(160), nullable=True)
    status = Column(String(40), default="pending")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("TaskSubmission")


class AdvertiserBudgetAlertV11(Base):
    __tablename__ = "v11_advertiser_budget_alerts"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    threshold_rsd = Column(Float, default=5000)
    status = Column(String(40), default="active")
    last_triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    advertiser = relationship("User")


class CampaignStatusLogV11(Base):
    __tablename__ = "v11_campaign_status_logs"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    old_status = Column(String(40), nullable=True)
    new_status = Column(String(40), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task")


class FraudSignalV11(Base):
    __tablename__ = "v11_fraud_signals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    signal_type = Column(String(120), nullable=False)
    risk_score = Column(Float, default=0)
    status = Column(String(40), default="open")  # open, reviewed, dismissed
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class LegalPageV11(Base):
    __tablename__ = "v11_legal_pages"
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(160), unique=True, index=True, nullable=False)
    title = Column(String(220), nullable=False)
    body = Column(Text, nullable=False)
    version = Column(String(40), default="1.0")
    status = Column(String(40), default="published")
    updated_at = Column(DateTime, default=datetime.utcnow)


class UserConsentV11(Base):
    __tablename__ = "v11_user_consents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    consent_type = Column(String(120), nullable=False)
    version = Column(String(40), default="1.0")
    ip_address = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class ForbiddenTaskRuleV11(Base):
    __tablename__ = "v11_forbidden_task_rules"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(180), nullable=False)
    pattern = Column(String(220), nullable=False)
    severity = Column(String(40), default="high")
    action = Column(String(120), default="reject_campaign")
    status = Column(String(40), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class MarketingLandingPageV11(Base):
    __tablename__ = "v11_marketing_landing_pages"
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(160), unique=True, index=True, nullable=False)
    title = Column(String(220), nullable=False)
    headline = Column(String(260), nullable=False)
    body = Column(Text, nullable=False)
    cta_text = Column(String(120), default="Registracija")
    cta_url = Column(String(500), default="/registracija")
    status = Column(String(40), default="published")
    created_at = Column(DateTime, default=datetime.utcnow)


class ProductionConfigCheckV11(Base):
    __tablename__ = "v11_production_config_checks"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(160), unique=True, nullable=False)
    title = Column(String(220), nullable=False)
    status = Column(String(40), default="open")  # open, done, blocked
    importance = Column(String(40), default="high")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SmokeTestRunV11(Base):
    __tablename__ = "v11_smoke_test_runs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(180), nullable=False)
    status = Column(String(40), default="passed")
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SmokeTestItemV11(Base):
    __tablename__ = "v11_smoke_test_items"
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("v11_smoke_test_runs.id"), nullable=False)
    route = Column(String(220), nullable=False)
    expected_status = Column(Integer, default=200)
    actual_status = Column(Integer, default=200)
    status = Column(String(40), default="passed")
    note = Column(Text, nullable=True)

    run = relationship("SmokeTestRunV11")


class BackupRunV11(Base):
    __tablename__ = "v11_backup_runs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(180), nullable=False)
    backup_type = Column(String(80), default="manual")
    status = Column(String(40), default="created")
    file_hint = Column(String(500), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DeployTargetV11(Base):
    __tablename__ = "v11_deploy_targets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False)
    provider = Column(String(100), default="Render")
    status = Column(String(40), default="draft")
    url = Column(String(500), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminDailyDeskNoteV11(Base):
    __tablename__ = "v11_admin_daily_desk_notes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(220), nullable=False)
    priority = Column(String(40), default="medium")
    status = Column(String(40), default="open")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class LaunchReadinessScoreV11(Base):
    __tablename__ = "v11_launch_readiness_scores"
    id = Column(Integer, primary_key=True, index=True)
    score = Column(Float, default=0)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemErrorLogV11(Base):
    __tablename__ = "v11_system_error_logs"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(40), default="error")
    source = Column(String(120), default="app")
    message = Column(Text, nullable=False)
    status = Column(String(40), default="open")
    created_at = Column(DateTime, default=datetime.utcnow)



# -----------------------------
# V11.1 UI, ADS & PRICING MODELS
# -----------------------------

class MonetizationPricingV111(Base):
    __tablename__ = "v111_monetization_pricing"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(120), unique=True, index=True, nullable=False)
    title = Column(String(180), nullable=False)
    value_rsd = Column(Float, default=0)
    value_percent = Column(Float, default=0)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class HomeBannerSlotV111(Base):
    __tablename__ = "v111_home_banner_slots"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(80), unique=True, index=True, nullable=False)
    title = Column(String(160), nullable=False)
    placement = Column(String(80), default="home_top")
    width_label = Column(String(80), default="wide")
    price_rsd = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PaidAdBannerV111(Base):
    __tablename__ = "v111_paid_ad_banners"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("v111_home_banner_slots.id"), nullable=True)
    title = Column(String(180), nullable=False)
    body = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    target_url = Column(String(500), nullable=True)
    price_rsd = Column(Float, default=0)
    view_cost_rsd = Column(Float, default=0)
    viewer_reward_rsd = Column(Float, default=0)
    days_count = Column(Integer, default=7)
    status = Column(String(40), default="pending")  # pending, active, rejected, expired
    admin_note = Column(Text, nullable=True)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    views_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    advertiser = relationship("User")
    slot = relationship("HomeBannerSlotV111")


class PaidAdViewV111(Base):
    __tablename__ = "v111_paid_ad_views"
    id = Column(Integer, primary_key=True, index=True)
    banner_id = Column(Integer, ForeignKey("v111_paid_ad_banners.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cost_rsd = Column(Float, default=0)
    reward_rsd = Column(Float, default=0)
    platform_fee_rsd = Column(Float, default=0)
    ip_address = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    banner = relationship("PaidAdBannerV111", foreign_keys=[banner_id])
    user = relationship("User", foreign_keys=[user_id])
    advertiser = relationship("User", foreign_keys=[advertiser_id])


class PaidPromotionRequestV111(Base):
    __tablename__ = "v111_paid_promotion_requests"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    promotion_type = Column(String(80), default="top_position")  # top_position, featured, highlighted
    title = Column(String(180), nullable=False)
    price_rsd = Column(Float, default=0)
    days_count = Column(Integer, default=3)
    status = Column(String(40), default="pending")  # pending, active, rejected, expired
    admin_note = Column(Text, nullable=True)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    advertiser = relationship("User")
    task = relationship("Task")


class PanelShortcutV111(Base):
    __tablename__ = "v111_panel_shortcuts"
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(40), default="admin")
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String(500), nullable=False)
    group_name = Column(String(100), default="general")
    sort_order = Column(Integer, default=100)
    is_visible = Column(Boolean, default=True)


# ---------------------------------------------------
# V11.14 Auto Approval & Budget Engine
# ---------------------------------------------------

class AutoEngineLogV114(Base):
    __tablename__ = "auto_engine_logs_v114"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(120), nullable=False)
    actor_role = Column(String(50), default="system")
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    submission_id = Column(Integer, ForeignKey("task_submissions.id"), nullable=True)
    amount_rsd = Column(Float, default=0.0)
    status = Column(String(50), default="done")
    message = Column(Text, default="")
    meta_json = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    actor = relationship("User", foreign_keys=[actor_user_id])
    task = relationship("Task")
    submission = relationship("TaskSubmission")


class AutoNotificationQueueV114(Base):
    __tablename__ = "auto_notification_queue_v114"
    id = Column(Integer, primary_key=True, index=True)
    channel = Column(String(30), nullable=False)  # email, sms, internal
    recipient = Column(String(255), default="")
    subject = Column(String(255), default="")
    body = Column(Text, default="")
    status = Column(String(50), default="queued")
    related_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    related_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)

    user = relationship("User")
    task = relationship("Task")


class TaskViewSessionV114(Base):
    __tablename__ = "task_view_sessions_v114"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    required_seconds = Column(Integer, default=120)
    active_seconds = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    status = Column(String(50), default="started")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User")
    task = relationship("Task")


# ---------------------------------------------------
# V11.15 Smart Automation & User Motivation
# ---------------------------------------------------

class TaskReservationV115(Base):
    __tablename__ = "task_reservations_v115"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    status = Column(String(50), default="active")  # active, completed, expired, cancelled
    reserved_until = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User")
    task = relationship("Task")


class UserScoreV115(Base):
    __tablename__ = "user_scores_v115"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    quality_score = Column(Float, default=50.0)
    risk_score = Column(Float, default=0.0)
    level_name = Column(String(80), default="Novi član")
    status_name = Column(String(80), default="Nov")
    streak_days = Column(Integer, default=0)
    daily_points = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    last_activity_date = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class UserBadgeV115(Base):
    __tablename__ = "user_badges_v115"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_key = Column(String(120), nullable=False)
    title = Column(String(160), nullable=False)
    description = Column(Text, default="")
    icon = Column(String(20), default="🏅")
    awarded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class DailyRewardV115(Base):
    __tablename__ = "daily_rewards_v115"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reward_date = Column(String(20), nullable=False)
    points = Column(Integer, default=0)
    amount_rsd = Column(Float, default=0.0)
    status = Column(String(50), default="claimed")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class UserMissionV115(Base):
    __tablename__ = "user_missions_v115"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    mission_key = Column(String(120), nullable=False)
    title = Column(String(180), nullable=False)
    description = Column(Text, default="")
    target_count = Column(Integer, default=1)
    current_count = Column(Integer, default=0)
    reward_points = Column(Integer, default=0)
    reward_rsd = Column(Float, default=0.0)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User")


class AdvertiserSuggestionV115(Base):
    __tablename__ = "advertiser_suggestions_v115"
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    suggestion_type = Column(String(120), nullable=False)
    title = Column(String(180), nullable=False)
    description = Column(Text, default="")
    expected_impact = Column(String(120), default="")
    status = Column(String(50), default="open")
    created_at = Column(DateTime, default=datetime.utcnow)

    advertiser = relationship("User")
    task = relationship("Task")


class AdminDailyReportV115(Base):
    __tablename__ = "admin_daily_reports_v115"
    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(String(20), unique=True, nullable=False)
    new_users = Column(Integer, default=0)
    new_advertisers = Column(Integer, default=0)
    approved_submissions = Column(Integer, default=0)
    rejected_submissions = Column(Integer, default=0)
    pending_submissions = Column(Integer, default=0)
    platform_revenue_rsd = Column(Float, default=0.0)
    advertiser_spent_rsd = Column(Float, default=0.0)
    risk_users = Column(Integer, default=0)
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------
# V11.17 Admin Analytics & Separate CRM Databases
# ---------------------------------------------------

class PlatformVisitV117(Base):
    __tablename__ = "platform_visits_v117"
    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(String(120), index=True, default="")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    role = Column(String(50), default="guest")
    path = Column(String(500), index=True, default="")
    method = Column(String(20), default="GET")
    status_code = Column(Integer, default=200)
    referrer = Column(String(700), default="")
    user_agent = Column(Text, default="")
    ip_hash = Column(String(120), default="")
    duration_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class UserDirectoryV117(Base):
    __tablename__ = "user_directory_v117"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String(255), default="")
    email = Column(String(255), index=True, default="")
    phone = Column(String(80), default="")
    city = Column(String(120), default="")
    status_name = Column(String(80), default="")
    level_name = Column(String(80), default="")
    balance_rsd = Column(Float, default=0.0)
    pending_rsd = Column(Float, default=0.0)
    lifetime_earned_rsd = Column(Float, default=0.0)
    approved_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)
    pending_count = Column(Integer, default=0)
    referral_code = Column(String(80), default="")
    created_at_original = Column(DateTime, nullable=True)
    synced_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class AdvertiserDirectoryV117(Base):
    __tablename__ = "advertiser_directory_v117"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String(255), default="")
    company_name = Column(String(255), default="")
    email = Column(String(255), index=True, default="")
    phone = Column(String(80), default="")
    city = Column(String(120), default="")
    website = Column(String(255), default="")
    pib = Column(String(80), default="")
    budget_available_rsd = Column(Float, default=0.0)
    budget_reserved_rsd = Column(Float, default=0.0)
    budget_spent_rsd = Column(Float, default=0.0)
    campaigns_total = Column(Integer, default=0)
    campaigns_active = Column(Integer, default=0)
    campaigns_pending = Column(Integer, default=0)
    submissions_total = Column(Integer, default=0)
    created_at_original = Column(DateTime, nullable=True)
    synced_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
