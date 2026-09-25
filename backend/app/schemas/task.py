from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

TASK_STATUSES = {"TODO", "IN_PROGRESS", "DONE"}
TASK_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "URGENT"}
TASK_CATEGORIES = {"GENERAL", "PROGRAM", "FINANCE", "GUESTS", "VENDORS", "LOGISTICS", "VENUE", "DECOR", "COMMUNICATION", "FAMILY", "COMMITTEE"}


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    assigned_to: UUID | None = None
    status: str = "TODO"
    priority: str = "MEDIUM"
    category: str = "GENERAL"
    due_date: date | None = None

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        normalized = value.upper()
        aliases = {"TODO": "TODO", "TO_DO": "TODO", "IN_PROGRESS": "IN_PROGRESS", "DONE": "DONE"}
        normalized = aliases.get(normalized, normalized)
        if normalized not in TASK_STATUSES:
            raise ValueError("Unsupported task status")
        return normalized

    @field_validator("priority")
    @classmethod
    def normalize_priority(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in TASK_PRIORITIES:
            raise ValueError("Unsupported task priority")
        return normalized

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in TASK_CATEGORIES:
            raise ValueError("Unsupported task category")
        return normalized


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    assigned_to: UUID | None = None
    status: str | None = None
    priority: str | None = None
    category: str | None = None
    due_date: date | None = None

    @field_validator("status")
    @classmethod
    def normalize_optional_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper()
        aliases = {"TODO": "TODO", "TO_DO": "TODO", "IN_PROGRESS": "IN_PROGRESS", "DONE": "DONE"}
        normalized = aliases.get(normalized, normalized)
        if normalized not in TASK_STATUSES:
            raise ValueError("Unsupported task status")
        return normalized

    @field_validator("priority")
    @classmethod
    def normalize_optional_priority(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper()
        if normalized not in TASK_PRIORITIES:
            raise ValueError("Unsupported task priority")
        return normalized

    @field_validator("category")
    @classmethod
    def normalize_optional_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper()
        if normalized not in TASK_CATEGORIES:
            raise ValueError("Unsupported task category")
        return normalized


class TaskRead(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str | None = None
    assigned_to: UUID | None = None
    assignee_name: str | None = None
    assignee_email: str | None = None
    created_by_user_id: UUID | None = None
    status: str
    priority: str
    category: str
    due_date: date | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    is_overdue: bool = False
    is_due_soon: bool = False

    model_config = ConfigDict(from_attributes=True)


class TaskSummary(BaseModel):
    project_id: UUID
    total: int
    todo: int
    in_progress: int
    completed: int
    overdue: int
    due_soon: int
    completion_percentage: int
    my_tasks: int


class TaskAssigneeRead(BaseModel):
    user_id: UUID
    name: str | None = None
    email: str | None = None
    role: str
