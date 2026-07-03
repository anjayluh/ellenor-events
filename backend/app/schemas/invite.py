from uuid import UUID

from pydantic import BaseModel

from app.core.permissions import ProjectRole


class InviteCreate(BaseModel):
    project_id: UUID
    contact: str
    role_assigned: ProjectRole


class InviteRead(BaseModel):
    id: UUID
    project_id: UUID
    contact: str
    role_assigned: ProjectRole
    status: str
    invite_link: str


class InviteAccept(BaseModel):
    token: str
    name: str
    phone: str | None = None
    email: str | None = None
