from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), index=True)
    recipient_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    recipient_contact: Mapped[str | None] = mapped_column(String, nullable=True)
    channel: Mapped[str] = mapped_column(String, default="email")
    provider: Mapped[str] = mapped_column(String, default="resend")
    subject: Mapped[str | None] = mapped_column(String, nullable=True)
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="prepared", index=True)
    provider_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    prepared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), primary_key=True)
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    email_fallback_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    meeting_updates: Mapped[bool] = mapped_column(Boolean, default=True)
    invite_updates: Mapped[bool] = mapped_column(Boolean, default=True)
    budget_updates: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
