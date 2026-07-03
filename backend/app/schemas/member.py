from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.permissions import BudgetVisibilityMode, ProjectRole


class MemberCreate(BaseModel):
    user_id: UUID
    role: ProjectRole
    budget_visibility_mode: BudgetVisibilityMode = BudgetVisibilityMode.NO_ACCESS


class MemberUpdate(BaseModel):
    role: ProjectRole | None = None
    permissions_level: str | None = None
    budget_visibility_mode: BudgetVisibilityMode | None = None


class MemberRead(MemberCreate):
    id: UUID
    project_id: UUID
    permissions_level: str | None = None

    model_config = ConfigDict(from_attributes=True)
