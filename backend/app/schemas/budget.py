from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BudgetUpdate(BaseModel):
    total: float = Field(ge=0)
    spent: float = Field(ge=0)


class BudgetLineItemCreate(BaseModel):
    category: str
    description: str
    estimated_amount: float = Field(ge=0)
    actual_amount: float = Field(default=0, ge=0)
    status: str = "planned"


class BudgetLineItemUpdate(BaseModel):
    category: str | None = None
    description: str | None = None
    estimated_amount: float | None = Field(default=None, ge=0)
    actual_amount: float | None = Field(default=None, ge=0)
    status: str | None = None


class BudgetLineItemRead(BudgetLineItemCreate):
    id: UUID
    project_id: UUID

    model_config = ConfigDict(from_attributes=True)


class ContributionCreate(BaseModel):
    contributor: str
    pledged: float = Field(default=0, ge=0)
    paid: float = Field(default=0, ge=0)
    status: str = "pledged"


class ContributionUpdate(BaseModel):
    contributor: str | None = None
    pledged: float | None = Field(default=None, ge=0)
    paid: float | None = Field(default=None, ge=0)
    status: str | None = None


class ContributionRead(ContributionCreate):
    id: UUID
    project_id: UUID

    model_config = ConfigDict(from_attributes=True)


class BudgetProposalCreate(BaseModel):
    title: str
    description: str | None = None
    amount: float = Field(ge=0)


class BudgetProposalReview(BaseModel):
    status: str


class BudgetProposalRead(BudgetProposalCreate):
    id: UUID
    project_id: UUID
    proposed_by: UUID
    status: str
    reviewed_by: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class BudgetRead(BaseModel):
    visibility: str
    total: float | None = None
    spent: float | None = None
    remaining: float | None = None
    contribution_progress: float | None = None
    pledged_total: float | None = None
    line_items: list[BudgetLineItemRead] | None = None
    contributions: list[ContributionRead] | None = None


class BudgetExport(BaseModel):
    project_id: UUID
    total: float
    spent: float
    remaining: float
    contribution_progress: float
    pledged_total: float
    line_items: list[BudgetLineItemRead]
    contributions: list[ContributionRead]
    proposals: list[BudgetProposalRead]
