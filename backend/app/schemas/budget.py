from pydantic import BaseModel, Field


class BudgetUpdate(BaseModel):
    total: float = Field(ge=0)
    spent: float = Field(ge=0)


class BudgetRead(BaseModel):
    visibility: str
    total: float | None = None
    spent: float | None = None
    contribution_progress: float | None = None
