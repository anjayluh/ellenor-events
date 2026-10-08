from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Meeting(Base):
    __tablename__ = "meetings"
    __table_args__ = (UniqueConstraint("id", "project_id", name="uq_meetings_id_project"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), index=True)
    type: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    agenda: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    decisions_log: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="scheduled")
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(String, default="PLANNING")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    meeting_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MeetingRsvp(Base):
    __tablename__ = "meeting_rsvp"
    __table_args__ = (UniqueConstraint("meeting_id", "user_id", name="uq_meeting_rsvp_user"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("meetings.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String)
    comment: Mapped[str | None] = mapped_column(Text)
    responded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"
    __table_args__ = (
        UniqueConstraint("meeting_id", "user_id", name="uq_meeting_participant_user"),
        ForeignKeyConstraint(["meeting_id", "project_id"], ["meetings.id", "meetings.project_id"], name="fk_meeting_participant_meeting_project"),
        ForeignKeyConstraint(["project_id", "user_id"], ["project_members.project_id", "project_members.user_id"], name="fk_meeting_participant_project_member"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    attendance_status: Mapped[str] = mapped_column(String, default="INVITED")
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MeetingAgendaItem(Base):
    __tablename__ = "meeting_agenda_items"
    __table_args__ = (
        ForeignKeyConstraint(["meeting_id", "project_id"], ["meetings.id", "meetings.project_id"], name="fk_meeting_agenda_meeting_project"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    owner_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MeetingDecision(Base):
    __tablename__ = "meeting_decisions"
    __table_args__ = (
        ForeignKeyConstraint(["meeting_id", "project_id"], ["meetings.id", "meetings.project_id"], name="fk_meeting_decision_meeting_project"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    decision_text: Mapped[str] = mapped_column(Text)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MeetingDocument(Base):
    __tablename__ = "meeting_documents"
    __table_args__ = (
        UniqueConstraint("meeting_id", "document_id", name="uq_meeting_document"),
        ForeignKeyConstraint(["meeting_id", "project_id"], ["meetings.id", "meetings.project_id"], name="fk_meeting_document_meeting_project"),
        ForeignKeyConstraint(["document_id", "project_id"], ["project_documents.id", "project_documents.project_id"], name="fk_meeting_document_project_document"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    document_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
