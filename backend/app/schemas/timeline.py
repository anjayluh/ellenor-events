from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TIMELINE_CATEGORIES = {
    "PREPARATION",
    "CEREMONY",
    "RECEPTION",
    "FAMILY",
    "PHOTOGRAPHY",
    "VIDEOGRAPHY",
    "CATERING",
    "DECOR",
    "ENTERTAINMENT",
    "TRANSPORT",
    "GUESTS",
    "VENDORS",
    "PROGRAM",
    "BREAK",
    "OTHER",
}
TIMELINE_STATUSES = {"UPCOMING", "IN_PROGRESS", "COMPLETED", "CANCELLED"}


class TimelineItemBase(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    category: str = "PROGRAM"
    start_at: datetime
    end_at: datetime
    location: str | None = Field(default=None, max_length=180)
    assignee_user_id: UUID | None = None
    status: str = "UPCOMING"
    notes: str | None = None
    sort_order: int = 0

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in TIMELINE_CATEGORIES:
            raise ValueError("Unsupported timeline category")
        return normalized

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in TIMELINE_STATUSES:
            raise ValueError("Unsupported timeline status")
        return normalized

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.end_at <= self.start_at:
            raise ValueError("End time must be after start time")
        return self


class TimelineItemCreate(TimelineItemBase):
    pass


class TimelineItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    location: str | None = Field(default=None, max_length=180)
    assignee_user_id: UUID | None = None
    status: str | None = None
    notes: str | None = None
    sort_order: int | None = None

    @field_validator("category")
    @classmethod
    def normalize_optional_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper()
        if normalized not in TIMELINE_CATEGORIES:
            raise ValueError("Unsupported timeline category")
        return normalized

    @field_validator("status")
    @classmethod
    def normalize_optional_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper()
        if normalized not in TIMELINE_STATUSES:
            raise ValueError("Unsupported timeline status")
        return normalized


class TimelineConflictRead(BaseModel):
    id: UUID
    title: str
    start_at: datetime
    end_at: datetime


class TimelineItemRead(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str | None = None
    category: str
    start_at: datetime
    end_at: datetime
    location: str | None = None
    assignee_user_id: UUID | None = None
    assignee_name: str | None = None
    assignee_email: str | None = None
    created_by_user_id: UUID | None = None
    status: str
    stored_status: str
    notes: str | None = None
    sort_order: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    duration_minutes: int
    has_conflict: bool = False
    conflicts: list[TimelineConflictRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TimelineSummaryItem(BaseModel):
    id: UUID
    title: str
    category: str
    start_at: datetime
    end_at: datetime
    location: str | None = None
    assignee_name: str | None = None
    status: str


class TimelineSummary(BaseModel):
    project_id: UUID
    total: int
    upcoming: int
    completed: int
    cancelled: int
    today: int
    in_progress: int
    conflicts: int
    current_item: TimelineSummaryItem | None = None
    next_item: TimelineSummaryItem | None = None
    next_upcoming_at: datetime | None = None


class TimelineDateFilter(BaseModel):
    date: date
