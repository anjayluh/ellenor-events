from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.project import ProjectRead


class CustomerAccountRead(BaseModel):
    id: UUID
    name: str
    status: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CustomerAccountMemberRead(BaseModel):
    id: UUID
    customer_account_id: UUID
    user_id: UUID
    role: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountEntitlementRead(BaseModel):
    id: UUID
    customer_account_id: UUID
    key: str
    quantity: int | None = None
    used_quantity: int = 0
    status: str
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime | None = None


class CustomerAccountOverview(BaseModel):
    account: CustomerAccountRead
    membership: CustomerAccountMemberRead
    entitlements: list[AccountEntitlementRead] = Field(default_factory=list)
    projects: list[ProjectRead] = Field(default_factory=list)
