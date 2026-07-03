from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjectSettings(Base):
    __tablename__ = "project_settings"

    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), primary_key=True)
    whatsapp_first: Mapped[bool] = mapped_column(Boolean, default=True)
    email_fallback: Mapped[bool] = mapped_column(Boolean, default=True)
    rsvp_required: Mapped[bool] = mapped_column(Boolean, default=False)
    budget_editing_mode: Mapped[str] = mapped_column(String, default="owners_only")
    vendor_mode: Mapped[str] = mapped_column(String, default="directory")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
