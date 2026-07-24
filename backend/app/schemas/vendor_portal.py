from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VendorProfileUpsert(BaseModel):
    business_name: str
    category: str
    contact_email: str | None = None
    contact_phone: str | None = None
    bio: str | None = None
    payment_details: str | None = None
    status: str = "active"


class VendorProfileRead(VendorProfileUpsert):
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)


class VendorPortfolioCreate(BaseModel):
    title: str
    image_url: str
    caption: str | None = None


class VendorPortfolioRead(VendorPortfolioCreate):
    id: UUID
    vendor_user_id: UUID

    model_config = ConfigDict(from_attributes=True)


class VendorBookingCreate(BaseModel):
    vendor_user_id: UUID
    meeting_requested_at: datetime | None = None
    meeting_notes: str | None = None


class VendorBookingUpdate(BaseModel):
    status: str | None = None
    meeting_requested_at: datetime | None = None
    meeting_notes: str | None = None


class VendorBookingRead(BaseModel):
    id: UUID
    project_id: UUID
    vendor_user_id: UUID
    requested_by: UUID
    status: str
    meeting_requested_at: datetime | None = None
    meeting_notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class VendorPaymentCreate(BaseModel):
    amount: float = Field(ge=0)
    received_at: date | None = None
    payment_method: str | None = None
    payment_reference: str | None = None
    notes: str | None = None


class VendorPaymentRead(VendorPaymentCreate):
    id: UUID
    booking_id: UUID

    model_config = ConfigDict(from_attributes=True)
