from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BillingCustomer(Base):
    __tablename__ = "billing_customers"
    __table_args__ = (
        UniqueConstraint("customer_account_id", name="uq_billing_customer_account"),
        UniqueConstraint("provider", "provider_customer_id", name="uq_billing_customer_provider_ref"),
        CheckConstraint("status in ('ACTIVE','INACTIVE')", name="ck_billing_customer_status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customer_accounts.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String, default="flutterwave", index=True)
    provider_customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="ACTIVE", index=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CustomerSubscription(Base):
    __tablename__ = "customer_subscriptions"
    __table_args__ = (
        UniqueConstraint("provider", "provider_subscription_id", name="uq_customer_subscription_provider_ref"),
        CheckConstraint("status in ('INCOMPLETE','ACTIVE','PAST_DUE','CANCELLED','EXPIRED','FAILED')", name="ck_customer_subscription_status"),
        CheckConstraint("access_source in ('PAID','MARKETING')", name="ck_customer_subscription_access_source"),
        CheckConstraint("billing_interval in ('ONE_TIME','MONTHLY','YEARLY')", name="ck_customer_subscription_billing_interval"),
        CheckConstraint("currency in ('UGX')", name="ck_customer_subscription_currency"),
        CheckConstraint("amount_minor >= 0", name="ck_customer_subscription_amount"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customer_accounts.id", ondelete="CASCADE"), index=True)
    package_plan_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("package_plans.id"), index=True)
    package_price_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("package_prices.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String, default="INCOMPLETE", index=True)
    access_source: Mapped[str] = mapped_column(String, default="PAID", index=True)
    currency: Mapped[str] = mapped_column(String, default="UGX")
    amount_minor: Mapped[int] = mapped_column(Integer, default=0)
    billing_interval: Mapped[str] = mapped_column(String, default="MONTHLY")
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider: Mapped[str] = mapped_column(String, default="flutterwave", index=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    __table_args__ = (
        UniqueConstraint("provider", "provider_reference", name="uq_payment_transaction_provider_reference"),
        UniqueConstraint("provider", "provider_transaction_id", name="uq_payment_transaction_provider_transaction"),
        CheckConstraint("status in ('INITIATED','PENDING','SUCCESSFUL','FAILED','CANCELLED','REFUNDED')", name="ck_payment_transaction_status"),
        CheckConstraint("currency in ('UGX')", name="ck_payment_transaction_currency"),
        CheckConstraint("amount_minor >= 0", name="ck_payment_transaction_amount"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customer_accounts.id", ondelete="CASCADE"), index=True)
    subscription_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customer_subscriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    package_price_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("package_prices.id"), nullable=True, index=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String, default="UGX")
    provider: Mapped[str] = mapped_column(String, default="flutterwave", index=True)
    provider_transaction_id: Mapped[str | None] = mapped_column(String, nullable=True)
    provider_reference: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, default="INITIATED", index=True)
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_payment_event_provider_event"),
        CheckConstraint("status in ('RECEIVED','PROCESSED','IGNORED','FAILED')", name="ck_payment_event_status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String, default="flutterwave", index=True)
    provider_event_id: Mapped[str] = mapped_column(String, index=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    provider_reference: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    provider_transaction_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default="RECEIVED", index=True)
    payload_json: Mapped[dict] = mapped_column("payload", JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketingAccessToken(Base):
    __tablename__ = "marketing_access_tokens"
    __table_args__ = (
        UniqueConstraint("code", name="uq_marketing_access_token_code"),
        CheckConstraint("status in ('ACTIVE','INACTIVE','EXPIRED')", name="ck_marketing_access_token_status"),
        CheckConstraint("duration_days > 0", name="ck_marketing_access_token_duration"),
        CheckConstraint("max_redemptions is null or max_redemptions > 0", name="ck_marketing_access_token_max_redemptions"),
        CheckConstraint("redemption_count >= 0", name="ck_marketing_access_token_redemption_count"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String, index=True)
    package_plan_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("package_plans.id"), index=True)
    package_price_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("package_prices.id"), nullable=True, index=True)
    duration_days: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_redemptions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    redemption_count: Mapped[int] = mapped_column(Integer, default=0)
    assigned_email: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    assigned_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String, default="ACTIVE", index=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MarketingAccessTokenRedemption(Base):
    __tablename__ = "marketing_access_token_redemptions"
    __table_args__ = (
        UniqueConstraint("access_token_id", "customer_account_id", name="uq_marketing_token_account_redemption"),
        UniqueConstraint("access_token_id", "user_id", name="uq_marketing_token_user_redemption"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    access_token_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("marketing_access_tokens.id", ondelete="CASCADE"), index=True)
    customer_account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customer_accounts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    subscription_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customer_subscriptions.id", ondelete="CASCADE"), index=True)
    redeemed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
