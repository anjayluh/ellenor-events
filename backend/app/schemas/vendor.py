from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class VendorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    category: str = Field(min_length=2, max_length=80)
    contact: str | None = Field(default=None, max_length=180)
    contact_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=60)
    email: EmailStr | None = None
    status: str = "shortlisted"
    notes: str | None = None
    external_url: str | None = None
    agreed_amount: Decimal = Field(default=Decimal("0"), ge=0)
    amount_paid: Decimal = Field(default=Decimal("0"), ge=0)

    @model_validator(mode="after")
    def validate_amounts(self):
        if self.amount_paid > self.agreed_amount:
            raise ValueError("Amount paid cannot exceed the agreed amount")
        return self


class VendorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    contact: str | None = Field(default=None, max_length=180)
    contact_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=60)
    email: EmailStr | None = None
    status: str | None = None
    notes: str | None = None
    external_url: str | None = None
    agreed_amount: Decimal | None = Field(default=None, ge=0)
    amount_paid: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_amounts(self):
        if self.agreed_amount is not None and self.amount_paid is not None and self.amount_paid > self.agreed_amount:
            raise ValueError("Amount paid cannot exceed the agreed amount")
        return self


class VendorRead(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    category: str
    contact: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str
    notes: str | None = None
    external_url: str | None = None
    agreed_amount: Decimal = Decimal("0")
    amount_paid: Decimal = Decimal("0")
    balance_amount: Decimal = Decimal("0")
    payment_status: str = "not_applicable"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class VendorUsageRead(BaseModel):
    key: str
    used: int
    limit: int | None = None
    remaining: int | None = None
    label: str


class VendorSummary(BaseModel):
    project_id: UUID
    total: int
    confirmed: int
    needs_attention: int
    outstanding_balance: Decimal
    vendor_usage: VendorUsageRead
