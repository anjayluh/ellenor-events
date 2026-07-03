from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ParticipantCreate(BaseModel):
    name: str
    contact: str | None = None
    role_type: str
    linked_user_id: UUID | None = None


class ParticipantUpdate(BaseModel):
    name: str | None = None
    contact: str | None = None
    role_type: str | None = None
    linked_user_id: UUID | None = None


class ParticipantRead(ParticipantCreate):
    id: UUID
    project_id: UUID

    model_config = ConfigDict(from_attributes=True)
