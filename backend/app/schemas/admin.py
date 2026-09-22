from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class AdminPermissionGrant(BaseModel):
    email: EmailStr
    role: str = "STAFF_VIEWER"
    permissions: list[str] = []
    status: str = "active"


class StaffMemberRead(BaseModel):
    id: UUID
    user_id: UUID
    email: str | None = None
    name: str | None = None
    role: str
    permissions: list[str]
    status: str


class UserAdminRead(BaseModel):
    id: UUID
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogRead(BaseModel):
    id: UUID
    actor_user_id: UUID | None = None
    project_id: UUID | None = None
    action: str
    metadata: dict
    created_at: datetime


class CustomerAccountAdminRead(BaseModel):
    id: UUID
    name: str
    status: str
    owner_email: str | None = None
    owner_user_id: UUID | None = None
    project_count: int = 0
    entitlement_count: int = 0
    created_at: datetime
