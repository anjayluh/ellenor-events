from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


BUDGET_ITEM_STATUSES = {"PLANNED", "QUOTED", "COMMITTED", "PARTIALLY_PAID", "PAID", "CANCELLED"}


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


class ProjectBudgetItemBase(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    category: str = Field(min_length=2, max_length=80)
    description: str | None = None
    vendor_id: UUID | None = None
    planned_amount: Decimal = Field(default=Decimal("0"), ge=0)
    committed_amount: Decimal = Field(default=Decimal("0"), ge=0)
    paid_amount: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="UGX", min_length=3, max_length=3)
    due_date: date | None = None
    status: str = "PLANNED"
    notes: str | None = None

    @model_validator(mode="after")
    def validate_amounts_and_status(self):
        status_value = self.status.upper()
        if status_value not in BUDGET_ITEM_STATUSES:
            raise ValueError("Unsupported budget item status")
        self.status = status_value
        self.currency = self.currency.upper()
        if self.paid_amount > self.committed_amount:
            raise ValueError("Paid amount cannot exceed the committed amount")
        if status_value == "PAID" and self.committed_amount != self.paid_amount:
            raise ValueError("Paid budget items must have paid amount equal to committed amount")
        if status_value == "PARTIALLY_PAID" and not (Decimal("0") < self.paid_amount < self.committed_amount):
            raise ValueError("Partially paid budget items require paid amount below committed amount")
        if status_value in {"PLANNED", "QUOTED"} and self.paid_amount > Decimal("0"):
            raise ValueError("Planned or quoted budget items cannot have payments recorded")
        return self


class ProjectBudgetItemCreate(ProjectBudgetItemBase):
    pass


class ProjectBudgetItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = None
    vendor_id: UUID | None = None
    planned_amount: Decimal | None = Field(default=None, ge=0)
    committed_amount: Decimal | None = Field(default=None, ge=0)
    paid_amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    due_date: date | None = None
    status: str | None = None
    notes: str | None = None


class ProjectBudgetItemRead(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    category: str
    description: str | None = None
    vendor_id: UUID | None = None
    vendor_name: str | None = None
    planned_amount: Decimal
    committed_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    currency: str
    due_date: date | None = None
    status: str
    notes: str | None = None
    created_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    is_overdue: bool = False
    is_upcoming: bool = False

    model_config = ConfigDict(from_attributes=True)


class BudgetCategorySummary(BaseModel):
    category: str
    planned_amount: Decimal
    committed_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    item_count: int


class BudgetUpcomingPayment(BaseModel):
    id: UUID
    name: str
    category: str
    due_date: date
    outstanding_amount: Decimal
    currency: str


class BudgetItemSummary(BaseModel):
    project_id: UUID
    currency: str = "UGX"
    total_items: int
    total_planned: Decimal
    total_committed: Decimal
    total_paid: Decimal
    total_outstanding: Decimal
    unpaid_items: int
    overdue_items: int
    upcoming_payments_count: int
    paid_items: int
    partially_paid_items: int
    utilization_percentage: int
    paid_percentage: int
    category_breakdown: list[BudgetCategorySummary]
    upcoming_payments: list[BudgetUpcomingPayment]


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
    items: list[ProjectBudgetItemRead] | None = None
    summary: BudgetItemSummary | None = None


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
