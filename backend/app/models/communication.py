from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, ForeignKeyConstraint, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjectCommunication(Base):
    __tablename__ = "project_communications"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_project_communications_id_project"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    author_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    communication_type: Mapped[str] = mapped_column(String(32), default="UPDATE", index=True)
    priority: Mapped[str] = mapped_column(String(16), default="NORMAL", index=True)
    audience_mode: Mapped[str] = mapped_column(String(24), default="ALL_MEMBERS")
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProjectCommunicationRecipient(Base):
    __tablename__ = "project_communication_recipients"
    __table_args__ = (
        UniqueConstraint("communication_id", "recipient_user_id", name="uq_project_communication_recipient"),
        ForeignKeyConstraint(["communication_id", "project_id"], ["project_communications.id", "project_communications.project_id"]),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    communication_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("project_communications.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    recipient_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProjectCommunicationRead(Base):
    __tablename__ = "project_communication_reads"
    __table_args__ = (
        UniqueConstraint("communication_id", "user_id", name="uq_project_communication_read"),
        ForeignKeyConstraint(["communication_id", "project_id"], ["project_communications.id", "project_communications.project_id"]),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    communication_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("project_communications.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
