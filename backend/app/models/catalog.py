from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EntitlementDefinition(Base):
    __tablename__ = "entitlement_definitions"
    __table_args__ = (
        UniqueConstraint("key", name="uq_entitlement_definition_key"),
        CheckConstraint("value_type in ('BOOLEAN','QUANTITY','UNLIMITED')", name="ck_entitlement_definition_value_type"),
        CheckConstraint("scope in ('ACCOUNT','EVENT')", name="ck_entitlement_definition_scope"),
        CheckConstraint("status in ('ACTIVE','INACTIVE')", name="ck_entitlement_definition_status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    value_type: Mapped[str] = mapped_column(String)
    scope: Mapped[str] = mapped_column(String)
    is_usage_tracked: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PackagePlan(Base):
    __tablename__ = "package_plans"
    __table_args__ = (
        UniqueConstraint("code", name="uq_package_plan_code"),
        CheckConstraint("status in ('DRAFT','ACTIVE','INACTIVE','ARCHIVED')", name="ck_package_plan_status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="DRAFT", index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_add_on: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PackagePrice(Base):
    __tablename__ = "package_prices"
    __table_args__ = (
        CheckConstraint("currency in ('UGX')", name="ck_package_price_currency"),
        CheckConstraint("amount_minor >= 0", name="ck_package_price_amount_minor"),
        CheckConstraint("billing_interval in ('ONE_TIME','MONTHLY','YEARLY')", name="ck_package_price_billing_interval"),
        CheckConstraint("status in ('DRAFT','ACTIVE','INACTIVE','ARCHIVED')", name="ck_package_price_status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    package_plan_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("package_plans.id", ondelete="CASCADE"), index=True)
    currency: Mapped[str] = mapped_column(String, default="UGX", index=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    billing_interval: Mapped[str] = mapped_column(String, default="ONE_TIME", index=True)
    status: Mapped[str] = mapped_column(String, default="DRAFT", index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PackageEntitlementGrant(Base):
    __tablename__ = "package_entitlement_grants"
    __table_args__ = (
        UniqueConstraint("package_plan_id", "entitlement_key", name="uq_package_entitlement_grant_key"),
        CheckConstraint("value_type in ('BOOLEAN','QUANTITY','UNLIMITED')", name="ck_package_entitlement_grant_value_type"),
        CheckConstraint("scope in ('ACCOUNT','EVENT')", name="ck_package_entitlement_grant_scope"),
        CheckConstraint("quantity is null or quantity >= 0", name="ck_package_entitlement_grant_quantity_nonnegative"),
        CheckConstraint("duration_days is null or duration_days > 0", name="ck_package_entitlement_grant_duration_positive"),
        CheckConstraint(
            "(value_type = 'QUANTITY' and quantity is not null and quantity > 0) or (value_type in ('BOOLEAN','UNLIMITED') and quantity is null)",
            name="ck_package_entitlement_grant_value_quantity",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    package_plan_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("package_plans.id", ondelete="CASCADE"), index=True)
    entitlement_key: Mapped[str] = mapped_column(String, ForeignKey("entitlement_definitions.key"), index=True)
    scope: Mapped[str] = mapped_column(String)
    value_type: Mapped[str] = mapped_column(String)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
