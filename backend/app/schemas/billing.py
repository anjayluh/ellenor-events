from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class CheckoutCreate(BaseModel):
    package_price_id: UUID
    customer_account_id: UUID | None = None


class CheckoutRead(BaseModel):
    transaction_id: UUID
    subscription_id: UUID
    customer_account_id: UUID
    package_price_id: UUID
    amount_minor: int
    currency: str
    billing_interval: str
    provider: str
    provider_reference: str
    checkout_url: str
    status: str


class PaymentTransactionRead(BaseModel):
    id: UUID
    customer_account_id: UUID
    subscription_id: UUID | None = None
    package_price_id: UUID | None = None
    amount_minor: int
    currency: str
    provider: str
    provider_reference: str
    provider_transaction_id: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CustomerSubscriptionRead(BaseModel):
    id: UUID
    customer_account_id: UUID
    package_plan_id: UUID
    package_price_id: UUID | None = None
    status: str
    access_source: str
    currency: str
    amount_minor: int
    billing_interval: str
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool
    cancelled_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    provider: str
    package_name: str | None = None
    entitlement_summary: list[dict] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SubscriptionCancelRequest(BaseModel):
    subscription_id: UUID
    cancel_at_period_end: bool = True


class FlutterwaveWebhookRead(BaseModel):
    status: str
    event_id: UUID | None = None
    transaction_id: UUID | None = None
    subscription_id: UUID | None = None


class MarketingAccessTokenCreate(BaseModel):
    code: str
    package_plan_id: UUID
    package_price_id: UUID | None = None
    duration_days: int = Field(gt=0)
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    max_redemptions: int | None = Field(default=None, gt=0)
    assigned_email: EmailStr | None = None
    assigned_user_id: UUID | None = None
    status: str = "ACTIVE"
    internal_notes: str | None = None
    metadata: dict = Field(default_factory=dict)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_token_dates(self):
        if self.status not in {"ACTIVE", "INACTIVE", "EXPIRED"}:
            raise ValueError("Unsupported token status")
        if self.starts_at and self.expires_at and self.expires_at <= self.starts_at:
            raise ValueError("Token expiry must be after start date")
        return self


class MarketingAccessTokenUpdate(BaseModel):
    status: str | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    max_redemptions: int | None = Field(default=None, gt=0)
    internal_notes: str | None = None
    metadata: dict | None = None

    @field_validator("status")
    @classmethod
    def normalize_optional_status(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class MarketingAccessTokenRead(BaseModel):
    id: UUID
    code: str
    package_plan_id: UUID
    package_price_id: UUID | None = None
    duration_days: int
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    max_redemptions: int | None = None
    redemption_count: int
    assigned_email: str | None = None
    assigned_user_id: UUID | None = None
    status: str
    internal_notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MarketingAccessTokenRedeem(BaseModel):
    code: str
    customer_account_id: UUID | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class BillingOverview(BaseModel):
    subscriptions: list[CustomerSubscriptionRead] = Field(default_factory=list)
    payments: list[PaymentTransactionRead] = Field(default_factory=list)
