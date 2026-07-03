from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TaskCreate(BaseModel):
    title: str
    assigned_to: UUID | None = None
    status: str = "todo"
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    assigned_to: UUID | None = None
    status: str | None = None
    due_date: date | None = None


class TaskRead(TaskCreate):
    id: UUID
    project_id: UUID

    model_config = ConfigDict(from_attributes=True)
