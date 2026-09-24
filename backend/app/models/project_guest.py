from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjectGuest(Base):
    __tablename__ = "project_guests"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    display_name: Mapped[str] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    group_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    invitation_card_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    invitation_status: Mapped[str] = mapped_column(String, default="NOT_SENT", index=True)
    rsvp_status: Mapped[str] = mapped_column(String, default="PENDING", index=True)
    rsvp_responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProjectGuestInvitation(Base):
    __tablename__ = "project_guest_invitations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_guest_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("project_guests.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    recipient_email: Mapped[str] = mapped_column(String, index=True)
    recipient_name: Mapped[str] = mapped_column(String)
    token: Mapped[str] = mapped_column(String, unique=True, index=True)
    status: Mapped[str] = mapped_column(String, default="SENT", index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notification_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    provider_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
