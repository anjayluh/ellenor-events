from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ENTITLEMENT_VALUE_TYPES = {"BOOLEAN", "QUANTITY", "UNLIMITED"}
ENTITLEMENT_SCOPES = {"ACCOUNT", "EVENT"}
ENTITLEMENT_STATUSES = {"ACTIVE", "INACTIVE"}
PACKAGE_STATUSES = {"DRAFT", "ACTIVE", "INACTIVE", "ARCHIVED"}
BILLING_INTERVALS = {"ONE_TIME", "MONTHLY", "YEARLY"}
SUPPORTED_CURRENCIES = {"UGX"}


class EntitlementDefinitionRead(BaseModel):
    id: UUID
    key: str
    name: str
    description: str
    value_type: str
    scope: str
    is_usage_tracked: bool
    status: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PackagePriceCreate(BaseModel):
    currency: str = "UGX"
    amount_minor: int = Field(ge=0)
    billing_interval: str = "ONE_TIME"
    status: str = "DRAFT"
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @field_validator("currency", "billing_interval", "status")
    @classmethod
    def normalize_uppercase(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_price(self):
        if self.currency not in SUPPORTED_CURRENCIES:
            raise ValueError("Unsupported currency")
        if self.billing_interval not in BILLING_INTERVALS:
            raise ValueError("Unsupported billing interval")
        if self.status not in PACKAGE_STATUSES:
            raise ValueError("Unsupported price status")
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("Price end date must be after start date")
        return self


class PackagePriceUpdate(BaseModel):
    currency: str | None = None
    amount_minor: int | None = Field(default=None, ge=0)
    billing_interval: str | None = None
    status: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @field_validator("currency", "billing_interval", "status")
    @classmethod
    def normalize_optional_uppercase(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @model_validator(mode="after")
    def validate_price_update(self):
        if self.currency and self.currency not in SUPPORTED_CURRENCIES:
            raise ValueError("Unsupported currency")
        if self.billing_interval and self.billing_interval not in BILLING_INTERVALS:
            raise ValueError("Unsupported billing interval")
        if self.status and self.status not in PACKAGE_STATUSES:
            raise ValueError("Unsupported price status")
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("Price end date must be after start date")
        return self


class PackagePriceRead(BaseModel):
    id: UUID
    package_plan_id: UUID
    currency: str
    amount_minor: int
    billing_interval: str
    status: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PackageEntitlementGrantCreate(BaseModel):
    entitlement_key: str
    scope: str
    value_type: str
    quantity: int | None = Field(default=None, ge=0)
    duration_days: int | None = Field(default=None, gt=0)
    metadata: dict = Field(default_factory=dict)

    @field_validator("entitlement_key")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("scope", "value_type")
    @classmethod
    def normalize_grant_uppercase(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_grant_shape(self):
        if self.scope not in ENTITLEMENT_SCOPES:
            raise ValueError("Unsupported entitlement scope")
        if self.value_type not in ENTITLEMENT_VALUE_TYPES:
            raise ValueError("Unsupported entitlement value type")
        if self.value_type == "QUANTITY" and not self.quantity:
            raise ValueError("Quantity entitlements require a positive quantity")
        if self.value_type in {"BOOLEAN", "UNLIMITED"} and self.quantity is not None:
            raise ValueError("Boolean and unlimited entitlements cannot have a quantity")
        return self


class PackageEntitlementGrantUpdate(BaseModel):
    scope: str | None = None
    value_type: str | None = None
    quantity: int | None = Field(default=None, ge=0)
    duration_days: int | None = Field(default=None, gt=0)
    metadata: dict | None = None

    @field_validator("scope", "value_type")
    @classmethod
    def normalize_optional_grant_uppercase(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class PackageEntitlementGrantRead(BaseModel):
    id: UUID
    package_plan_id: UUID
    entitlement_key: str
    scope: str
    value_type: str
    quantity: int | None = None
    duration_days: int | None = None
    metadata: dict
    created_at: datetime
    updated_at: datetime | None = None


class PackagePlanCreate(BaseModel):
    code: str
    name: str
    description: str
    status: str = "DRAFT"
    is_public: bool = False
    is_add_on: bool = False
    display_order: int = 0
    metadata: dict = Field(default_factory=dict)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().lower().replace(" ", "-")

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_plan(self):
        if self.status not in PACKAGE_STATUSES:
            raise ValueError("Unsupported package status")
        return self


class PackagePlanUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    status: str | None = None
    is_public: bool | None = None
    is_add_on: bool | None = None
    display_order: int | None = None
    metadata: dict | None = None

    @field_validator("code")
    @classmethod
    def normalize_optional_code(cls, value: str | None) -> str | None:
        return value.strip().lower().replace(" ", "-") if value else value

    @field_validator("status")
    @classmethod
    def normalize_optional_status(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @model_validator(mode="after")
    def validate_plan_update(self):
        if self.status and self.status not in PACKAGE_STATUSES:
            raise ValueError("Unsupported package status")
        return self


class PackagePlanRead(BaseModel):
    id: UUID
    code: str
    name: str
    description: str
    status: str
    is_public: bool
    is_add_on: bool
    display_order: int
    metadata: dict
    prices: list[PackagePriceRead] = Field(default_factory=list)
    entitlement_grants: list[PackageEntitlementGrantRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime | None = None


class PublicPackageRead(BaseModel):
    id: UUID
    code: str
    name: str
    description: str
    is_add_on: bool
    display_order: int
    prices: list[PackagePriceRead] = Field(default_factory=list)
    entitlement_grants: list[PackageEntitlementGrantRead] = Field(default_factory=list)
