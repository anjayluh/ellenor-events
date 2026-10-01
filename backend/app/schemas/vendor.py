from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


VENDOR_CATEGORIES = {
    "VENUE",
    "CATERING",
    "DECOR",
    "PHOTOGRAPHY",
    "VIDEOGRAPHY",
    "MC",
    "DJ_ENTERTAINMENT",
    "PA_SOUND",
    "MAKEUP_BEAUTY",
    "TRANSPORT",
    "CAKE",
    "ATTIRE",
    "FLORIST",
    "STATIONERY",
    "ACCOMMODATION",
    "SECURITY",
    "OTHER",
}
VENDOR_STATUSES = {"PROSPECT", "SHORTLISTED", "CONTACTED", "QUOTED", "BOOKED", "CONFIRMED", "COMPLETED", "CANCELLED"}


class VendorBase(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    category: str = Field(min_length=2, max_length=80)
    contact_person: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=60)
    email: EmailStr | None = None
    address: str | None = None
    website: str | None = None
    service_description: str | None = None
    status: str = "SHORTLISTED"
    notes: str | None = None
    event_day_contact: str | None = Field(default=None, max_length=120)
    booking_date: date | None = None

    @model_validator(mode="after")
    def clean_vendor(self):
        self.name = self.name.strip()
        self.category = self.category.strip()
        self.status = self.status.strip().upper()
        if self.contact_person is not None:
            self.contact_person = self.contact_person.strip() or None
        if self.phone is not None:
            self.phone = self.phone.strip() or None
        if self.address is not None:
            self.address = self.address.strip() or None
        if self.website is not None:
            self.website = self.website.strip() or None
        if self.service_description is not None:
            self.service_description = self.service_description.strip() or None
        if self.notes is not None:
            self.notes = self.notes.strip() or None
        if self.event_day_contact is not None:
            self.event_day_contact = self.event_day_contact.strip() or None
        return self


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    contact_person: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=60)
    email: EmailStr | None = None
    address: str | None = None
    website: str | None = None
    service_description: str | None = None
    status: str | None = None
    notes: str | None = None
    event_day_contact: str | None = Field(default=None, max_length=120)
    booking_date: date | None = None

    @model_validator(mode="after")
    def clean_vendor_update(self):
        if self.name is not None:
            self.name = self.name.strip()
        if self.category is not None:
            self.category = self.category.strip()
        if self.status is not None:
            self.status = self.status.strip().upper()
        for field in ["contact_person", "phone", "address", "website", "service_description", "notes", "event_day_contact"]:
            value = getattr(self, field)
            if value is not None:
                setattr(self, field, value.strip() or None)
        return self


class VendorBudgetItemRead(BaseModel):
    id: UUID
    name: str
    category: str
    planned_amount: Decimal
    committed_amount: Decimal
    actual_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    currency: str = "UGX"
    status: str
    due_date: date | None = None


class VendorFinancialSummary(BaseModel):
    planned_total: Decimal
    committed_total: Decimal
    actual_total: Decimal
    paid_total: Decimal
    outstanding_total: Decimal
    variance_amount: Decimal
    payment_percentage: int
    linked_budget_items_count: int


class VendorRead(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    category: str
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    website: str | None = None
    service_description: str | None = None
    status: str
    notes: str | None = None
    event_day_contact: str | None = None
    booking_date: date | None = None
    financial_summary: VendorFinancialSummary
    budget_items: list[VendorBudgetItemRead] = []
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
    booked: int
    needs_attention: int
    with_outstanding_balance: int
    outstanding_balance: Decimal
    planned_total: Decimal
    committed_total: Decimal
    actual_total: Decimal
    paid_total: Decimal
    variance_amount: Decimal
    vendor_usage: VendorUsageRead
