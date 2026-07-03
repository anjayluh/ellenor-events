from uuid import UUID

from pydantic import BaseModel

from app.core.permissions import BudgetVisibilityMode, ProjectRole


class MemberCreate(BaseModel):
    user_id: UUID
    role: ProjectRole
    budget_visibility_mode: BudgetVisibilityMode = BudgetVisibilityMode.NO_ACCESS


class MemberRead(MemberCreate):
    id: UUID
    project_id: UUID
