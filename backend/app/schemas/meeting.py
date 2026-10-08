from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.schemas.task import TaskRead


class MeetingCategory(StrEnum):
    PLANNING = "PLANNING"
    FAMILY = "FAMILY"
    COMMITTEE = "COMMITTEE"
    BUDGET = "BUDGET"
    VENDOR = "VENDOR"
    GUESTS = "GUESTS"
    TIMELINE = "TIMELINE"
    OTHER = "OTHER"


class MeetingStatus(StrEnum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MeetingAttendanceStatus(StrEnum):
    INVITED = "INVITED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    TENTATIVE = "TENTATIVE"


class MeetingCreate(BaseModel):
    type: str = Field(default="planning", min_length=1, max_length=80)
    title: str = Field(min_length=3, max_length=180)
    agenda: str | None = Field(default=None, max_length=4000)
    notes: str | None = Field(default=None, max_length=8000)
    decisions_log: str | None = Field(default=None, max_length=8000)
    scheduled_time: datetime | None = None
    category: MeetingCategory = MeetingCategory.PLANNING
    description: str | None = Field(default=None, max_length=4000)
    location: str | None = Field(default=None, max_length=300)
    meeting_link: HttpUrl | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    timezone: str | None = Field(default="Africa/Kampala", max_length=80)

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.start_at is None and self.scheduled_time is None:
            raise ValueError("A meeting start time is required")
        if self.start_at is not None and self.end_at is not None and self.end_at < self.start_at:
            raise ValueError("Meeting end time cannot be before its start time")
        return self


class MeetingUpdate(BaseModel):
    type: str | None = Field(default=None, min_length=1, max_length=80)
    title: str | None = Field(default=None, min_length=3, max_length=180)
    agenda: str | None = Field(default=None, max_length=4000)
    notes: str | None = Field(default=None, max_length=8000)
    decisions_log: str | None = Field(default=None, max_length=8000)
    status: str | None = None
    scheduled_time: datetime | None = None
    category: MeetingCategory | None = None
    description: str | None = Field(default=None, max_length=4000)
    location: str | None = Field(default=None, max_length=300)
    meeting_link: HttpUrl | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    timezone: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.start_at is not None and self.end_at is not None and self.end_at < self.start_at:
            raise ValueError("Meeting end time cannot be before its start time")
        return self


class MeetingParticipantRead(BaseModel):
    id: UUID
    meeting_id: UUID
    project_id: UUID
    user_id: UUID
    name: str | None = None
    email: str | None = None
    role: str | None = None
    attendance_status: MeetingAttendanceStatus
    responded_at: datetime | None = None


class MeetingParticipantUpsert(BaseModel):
    user_id: UUID
    attendance_status: MeetingAttendanceStatus = MeetingAttendanceStatus.INVITED


class MeetingAgendaItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int = Field(default=0, ge=0, le=10000)
    owner_user_id: UUID | None = None


class MeetingAgendaItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int | None = Field(default=None, ge=0, le=10000)
    owner_user_id: UUID | None = None


class MeetingAgendaItemRead(MeetingAgendaItemCreate):
    id: UUID
    meeting_id: UUID
    project_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MeetingDecisionCreate(BaseModel):
    decision_text: str = Field(min_length=1, max_length=4000)
    context: str | None = Field(default=None, max_length=2000)


class MeetingDecisionUpdate(BaseModel):
    decision_text: str | None = Field(default=None, min_length=1, max_length=4000)
    context: str | None = Field(default=None, max_length=2000)


class MeetingDecisionRead(MeetingDecisionCreate):
    id: UUID
    meeting_id: UUID
    project_id: UUID
    recorded_by_user_id: UUID
    recorder_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MeetingDocumentRead(BaseModel):
    id: UUID
    meeting_id: UUID
    project_id: UUID
    document_id: UUID
    original_filename: str | None = None
    category: str | None = None
    created_at: datetime | None = None


class MeetingDocumentAttach(BaseModel):
    document_id: UUID


class MeetingAgendaReorder(BaseModel):
    item_ids: list[UUID] = Field(min_length=1, max_length=200)


class MeetingRead(BaseModel):
    id: UUID
    project_id: UUID
    type: str
    title: str
    agenda: str | None = None
    notes: str | None = None
    decisions_log: str | None = None
    status: str
    scheduled_time: datetime
    created_by: UUID
    category: str = "PLANNING"
    description: str | None = None
    location: str | None = None
    meeting_link: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    timezone: str | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    updated_at: datetime | None = None
    participants: list[MeetingParticipantRead] = Field(default_factory=list)
    agenda_items: list[MeetingAgendaItemRead] = Field(default_factory=list)
    decisions: list[MeetingDecisionRead] = Field(default_factory=list)
    follow_up_tasks: list[TaskRead] = Field(default_factory=list)
    documents: list[MeetingDocumentRead] = Field(default_factory=list)
    conflict_ids: list[UUID] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class MeetingSummary(BaseModel):
    project_id: UUID
    total: int
    planned: int
    in_progress: int
    completed: int
    cancelled: int
    upcoming: int
    today: int
    current_item: MeetingRead | None = None
    next_item: MeetingRead | None = None
    conflicts: int


class MeetingNotesUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=8000)
    decisions_log: str | None = Field(default=None, max_length=8000)


class RsvpCreate(BaseModel):
    status: str
    comment: str | None = None


class RsvpRead(BaseModel):
    id: UUID
    meeting_id: UUID
    user_id: UUID
    status: str
    comment: str | None = None

    model_config = ConfigDict(from_attributes=True)
