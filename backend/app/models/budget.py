from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Budget(Base):
    __tablename__ = "budgets"

    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), primary_key=True)
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    spent: Mapped[float] = mapped_column(Numeric(12, 2), default=0)


class BudgetLineItem(Base):
    __tablename__ = "budget_line_items"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), index=True)
    category: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    item_name: Mapped[str | None] = mapped_column(String, nullable=True)
    unit_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=1)
    total_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    deposited_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    next_deposit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    actual_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String, default="planned")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BudgetProposal(Base):
    __tablename__ = "budget_proposals"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), index=True)
    proposed_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String, default="pending")
    reviewed_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Contribution(Base):
    __tablename__ = "contributions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), index=True)
    contributor: Mapped[str] = mapped_column(String)
    pledged: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    paid: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String, default="pledged")
