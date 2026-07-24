from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VendorProfile(Base):
    __tablename__ = "vendor_profiles"

    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    business_name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, index=True)
    contact_email: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VendorPortfolioItem(Base):
    __tablename__ = "vendor_portfolio_items"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    vendor_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("vendor_profiles.user_id"), index=True)
    title: Mapped[str] = mapped_column(String)
    image_url: Mapped[str] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VendorBooking(Base):
    __tablename__ = "vendor_bookings"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), index=True)
    vendor_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("vendor_profiles.user_id"), index=True)
    requested_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String, default="requested", index=True)
    meeting_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meeting_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VendorPayment(Base):
    __tablename__ = "vendor_payments"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("vendor_bookings.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    received_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
