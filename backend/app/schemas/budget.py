from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BudgetUpdate(BaseModel):
    total: float = Field(ge=0)
    spent: float = Field(ge=0)


class BudgetLineItemCreate(BaseModel):
    category: str
    description: str
    item_name: str | None = None
    unit_cost: float = Field(default=0, ge=0)
    quantity: float = Field(default=1, ge=0)
    total_cost: float = Field(default=0, ge=0)
    deposited_amount: float = Field(default=0, ge=0)
    balance: float = Field(default=0, ge=0)
    next_deposit_date: date | None = None
    payment_details: str | None = None
    estimated_amount: float = Field(ge=0)
    actual_amount: float = Field(default=0, ge=0)
    status: str = "planned"


class BudgetLineItemUpdate(BaseModel):
    category: str | None = None
    description: str | None = None
    item_name: str | None = None
    unit_cost: float | None = Field(default=None, ge=0)
    quantity: float | None = Field(default=None, ge=0)
    total_cost: float | None = Field(default=None, ge=0)
    deposited_amount: float | None = Field(default=None, ge=0)
    balance: float | None = Field(default=None, ge=0)
    next_deposit_date: date | None = None
    payment_details: str | None = None
    estimated_amount: float | None = Field(default=None, ge=0)
    actual_amount: float | None = Field(default=None, ge=0)
    status: str | None = None


class BudgetLineItemRead(BudgetLineItemCreate):
    unit_cost: float | None = Field(default=0, ge=0)
    quantity: float | None = Field(default=1, ge=0)
    total_cost: float | None = Field(default=0, ge=0)
    deposited_amount: float | None = Field(default=0, ge=0)
    balance: float | None = Field(default=0, ge=0)
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
    line_item_total_cost: float | None = None
    line_item_deposited_total: float | None = None
    line_item_balance_total: float | None = None
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
