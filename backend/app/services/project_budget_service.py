from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.permissions import BUDGET_EDIT_PERMISSION, PROJECT_OWNER_ROLES, ProjectRole, has_permission
from app.models.budget import ProjectBudgetCategory, ProjectBudgetItem
from app.models.project_member import ProjectMember
from app.models.vendor import Vendor
from app.schemas.budget import (
    BUDGET_ITEM_STATUSES,
    BudgetCategorySummary,
    BudgetItemSummary,
    BudgetUpcomingPayment,
    ProjectBudgetCategoryCreate,
    ProjectBudgetCategoryUpdate,
    ProjectBudgetItemCreate,
    ProjectBudgetItemRead,
    ProjectBudgetItemUpdate,
)

ZERO = Decimal("0")
UPCOMING_WINDOW_DAYS = 30


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def normalize_money(value: Decimal | int | float | str | None) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(str(value)).quantize(Decimal("0.01"))


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def payable_amount(item: ProjectBudgetItem) -> Decimal:
    actual = normalize_money(getattr(item, "actual_amount", ZERO))
    return actual if actual > ZERO else normalize_money(item.committed_amount)


def outstanding_amount(item: ProjectBudgetItem) -> Decimal:
    return max(payable_amount(item) - normalize_money(item.paid_amount), ZERO)


def is_overdue(item: ProjectBudgetItem) -> bool:
    return bool(item.due_date and item.due_date < today_utc() and outstanding_amount(item) > ZERO and item.status not in {"PAID", "CANCELLED"})


def is_upcoming(item: ProjectBudgetItem) -> bool:
    if not item.due_date or outstanding_amount(item) <= ZERO or item.status in {"PAID", "CANCELLED"}:
        return False
    current = today_utc()
    return current <= item.due_date <= current + timedelta(days=UPCOMING_WINDOW_DAYS)


def can_manage_budget(membership: ProjectMember) -> bool:
    role = ProjectRole(membership.role)
    return role in PROJECT_OWNER_ROLES or has_permission(role, getattr(membership, "permissions_json", None), BUDGET_EDIT_PERMISSION)


def require_budget_manager(membership: ProjectMember) -> None:
    if can_manage_budget(membership):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient event permissions")


def validate_status_amounts(status_value: str, planned_amount: Decimal, committed_amount: Decimal, actual_amount: Decimal, paid_amount: Decimal) -> None:
    if status_value not in BUDGET_ITEM_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported budget item status")
    if planned_amount < ZERO or committed_amount < ZERO or actual_amount < ZERO or paid_amount < ZERO:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Budget amounts cannot be negative")
    payable = actual_amount if actual_amount > ZERO else committed_amount
    if paid_amount > payable:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Paid amount cannot exceed the committed or actual amount")
    if status_value == "PAID" and (payable <= ZERO or payable != paid_amount):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Paid budget items must have paid amount equal to the committed or actual amount")
    if status_value == "PARTIALLY_PAID" and not (ZERO < paid_amount < payable):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Partially paid budget items require paid amount below the committed or actual amount")
    if status_value in {"PLANNED", "QUOTED"} and paid_amount > ZERO:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Planned or quoted budget items cannot have payments recorded")


def validate_vendor(db: Session, project_id: UUID, vendor_id: UUID | None) -> Vendor | None:
    if vendor_id is None:
        return None
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.project_id == project_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Budget vendor must belong to this event")
    return vendor


def get_budget_category_or_404(db: Session, project_id: UUID, category_id: UUID) -> ProjectBudgetCategory:
    category = db.query(ProjectBudgetCategory).filter(ProjectBudgetCategory.project_id == project_id, ProjectBudgetCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget category not found")
    return category


def validate_category(db: Session, project_id: UUID, category_id: UUID | None) -> ProjectBudgetCategory | None:
    if category_id is None:
        return None
    category = get_budget_category_or_404(db, project_id, category_id)
    return category


def list_budget_categories(db: Session, project_id: UUID) -> list[ProjectBudgetCategory]:
    return db.query(ProjectBudgetCategory).filter(ProjectBudgetCategory.project_id == project_id).order_by(ProjectBudgetCategory.sort_order.asc(), ProjectBudgetCategory.name.asc()).all()


def create_budget_category(db: Session, project_id: UUID, payload: ProjectBudgetCategoryCreate) -> ProjectBudgetCategory:
    name = payload.name.strip()
    existing = db.query(ProjectBudgetCategory).filter(ProjectBudgetCategory.project_id == project_id, ProjectBudgetCategory.name == name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Budget category already exists")
    category = ProjectBudgetCategory(project_id=project_id, name=name, description=clean_optional(payload.description), sort_order=payload.sort_order)
    db.add(category)
    db.flush()
    return category


def update_budget_category(db: Session, category: ProjectBudgetCategory, payload: ProjectBudgetCategoryUpdate) -> ProjectBudgetCategory:
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"]:
        name = str(updates["name"]).strip()
        duplicate = db.query(ProjectBudgetCategory).filter(ProjectBudgetCategory.project_id == category.project_id, ProjectBudgetCategory.name == name, ProjectBudgetCategory.id != category.id).first()
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Budget category already exists")
        category.name = name
        for item in db.query(ProjectBudgetItem).filter(ProjectBudgetItem.category_id == category.id).all():
            item.category = name
    if "description" in updates:
        category.description = clean_optional(updates["description"])
    if "sort_order" in updates and updates["sort_order"] is not None:
        category.sort_order = updates["sort_order"]
    category.updated_at = datetime.now(timezone.utc)
    db.flush()
    return category


def delete_budget_category(db: Session, category: ProjectBudgetCategory) -> None:
    for item in db.query(ProjectBudgetItem).filter(ProjectBudgetItem.category_id == category.id).all():
        item.category_id = None
    db.delete(category)
    db.flush()


def get_budget_item_or_404(db: Session, project_id: UUID, item_id: UUID) -> ProjectBudgetItem:
    item = db.query(ProjectBudgetItem).filter(ProjectBudgetItem.project_id == project_id, ProjectBudgetItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget item not found")
    return item


def serialize_budget_item(item: ProjectBudgetItem, vendors: dict[UUID, Vendor] | None = None) -> ProjectBudgetItemRead:
    vendor = vendors.get(item.vendor_id) if vendors and item.vendor_id else None
    return ProjectBudgetItemRead(
        id=item.id,
        project_id=item.project_id,
        name=item.name,
        category_id=getattr(item, "category_id", None),
        category=item.category,
        description=item.description,
        vendor_id=item.vendor_id,
        vendor_name=vendor.name if vendor else None,
        planned_amount=normalize_money(item.planned_amount),
        committed_amount=normalize_money(item.committed_amount),
        actual_amount=normalize_money(getattr(item, "actual_amount", ZERO)),
        paid_amount=normalize_money(item.paid_amount),
        outstanding_amount=outstanding_amount(item),
        currency=item.currency,
        due_date=item.due_date,
        status=item.status,
        notes=item.notes,
        created_by_user_id=item.created_by_user_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        is_overdue=is_overdue(item),
        is_upcoming=is_upcoming(item),
    )


def vendor_map(db: Session, items: list[ProjectBudgetItem]) -> dict[UUID, Vendor]:
    vendor_ids = {item.vendor_id for item in items if item.vendor_id}
    if not vendor_ids:
        return {}
    return {vendor.id: vendor for vendor in db.query(Vendor).filter(Vendor.id.in_(vendor_ids)).all()}


def list_project_budget_items(
    db: Session,
    project_id: UUID,
    *,
    search: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    vendor_id: UUID | None = None,
    payment_filter: str | None = None,
    overdue: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[ProjectBudgetItem]:
    query = db.query(ProjectBudgetItem).filter(ProjectBudgetItem.project_id == project_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(ProjectBudgetItem.name.ilike(pattern), ProjectBudgetItem.description.ilike(pattern), ProjectBudgetItem.category.ilike(pattern), ProjectBudgetItem.notes.ilike(pattern)))
    if category:
        query = query.filter(ProjectBudgetItem.category == category)
    if status_filter:
        query = query.filter(ProjectBudgetItem.status == status_filter.upper())
    if vendor_id:
        query = query.filter(ProjectBudgetItem.vendor_id == vendor_id)
    if payment_filter == "paid":
        query = query.filter(ProjectBudgetItem.status == "PAID")
    if payment_filter == "unpaid":
        query = query.filter(ProjectBudgetItem.status != "PAID", ProjectBudgetItem.status != "CANCELLED", ProjectBudgetItem.committed_amount > ProjectBudgetItem.paid_amount)
    if overdue is True:
        query = query.filter(ProjectBudgetItem.due_date.isnot(None), ProjectBudgetItem.due_date < today_utc(), ProjectBudgetItem.status.notin_(["PAID", "CANCELLED"]), ProjectBudgetItem.committed_amount > ProjectBudgetItem.paid_amount)
    return query.order_by(ProjectBudgetItem.due_date.asc().nullslast(), ProjectBudgetItem.created_at.desc()).offset(max(offset, 0)).limit(min(max(limit, 1), 250)).all()


def create_budget_item(db: Session, project_id: UUID, payload: ProjectBudgetItemCreate, *, created_by_user_id: UUID) -> ProjectBudgetItem:
    vendor = validate_vendor(db, project_id, payload.vendor_id)
    category = validate_category(db, project_id, payload.category_id)
    status_value = payload.status.upper()
    planned = normalize_money(payload.planned_amount)
    committed = normalize_money(payload.committed_amount)
    actual = normalize_money(payload.actual_amount)
    paid = normalize_money(payload.paid_amount)
    validate_status_amounts(status_value, planned, committed, actual, paid)
    item = ProjectBudgetItem(
        project_id=project_id,
        name=payload.name.strip(),
        category_id=category.id if category else None,
        category=category.name if category else payload.category.strip(),
        description=clean_optional(payload.description),
        vendor_id=vendor.id if vendor else None,
        planned_amount=planned,
        committed_amount=committed,
        actual_amount=actual,
        paid_amount=paid,
        currency=payload.currency.upper(),
        due_date=payload.due_date,
        status=status_value,
        notes=clean_optional(payload.notes),
        created_by_user_id=created_by_user_id,
    )
    db.add(item)
    db.flush()
    return item


def update_budget_item(db: Session, item: ProjectBudgetItem, payload: ProjectBudgetItemUpdate) -> ProjectBudgetItem:
    updates = payload.model_dump(exclude_unset=True)
    if "vendor_id" in updates:
        vendor = validate_vendor(db, item.project_id, updates["vendor_id"])
        updates["vendor_id"] = vendor.id if vendor else None
    if "category_id" in updates:
        category = validate_category(db, item.project_id, updates["category_id"])
        updates["category_id"] = category.id if category else None
        if category:
            updates["category"] = category.name
    for field in {"name", "category"}:
        if field in updates and updates[field] is not None:
            updates[field] = str(updates[field]).strip()
    for field in {"description", "notes"}:
        if field in updates:
            updates[field] = clean_optional(updates[field])
    if "currency" in updates and updates["currency"]:
        updates["currency"] = str(updates["currency"]).upper()
    if "status" in updates and updates["status"]:
        updates["status"] = str(updates["status"]).upper()

    planned = normalize_money(updates.get("planned_amount", item.planned_amount))
    committed = normalize_money(updates.get("committed_amount", item.committed_amount))
    actual = normalize_money(updates.get("actual_amount", getattr(item, "actual_amount", ZERO)))
    paid = normalize_money(updates.get("paid_amount", item.paid_amount))
    status_value = str(updates.get("status", item.status)).upper()
    validate_status_amounts(status_value, planned, committed, actual, paid)

    for field, value in updates.items():
        setattr(item, field, value)
    item.planned_amount = planned
    item.committed_amount = committed
    item.actual_amount = actual
    item.paid_amount = paid
    item.status = status_value
    item.updated_at = datetime.now(timezone.utc)
    db.flush()
    return item


def budget_item_summary(db: Session, project_id: UUID) -> BudgetItemSummary:
    items = db.query(ProjectBudgetItem).filter(ProjectBudgetItem.project_id == project_id).all()
    total_planned = sum((normalize_money(item.planned_amount) for item in items), ZERO)
    total_committed = sum((normalize_money(item.committed_amount) for item in items), ZERO)
    total_actual = sum((normalize_money(getattr(item, "actual_amount", ZERO)) for item in items), ZERO)
    total_paid = sum((normalize_money(item.paid_amount) for item in items), ZERO)
    total_outstanding = sum((outstanding_amount(item) for item in items if item.status != "CANCELLED"), ZERO)
    paid_items = sum(1 for item in items if item.status == "PAID")
    partially_paid_items = sum(1 for item in items if item.status == "PARTIALLY_PAID")
    overdue_items = sum(1 for item in items if is_overdue(item))
    upcoming_items = [item for item in items if is_upcoming(item)]

    categories: dict[str, dict[str, Decimal | int | UUID | None]] = {}
    for item in items:
        bucket = categories.setdefault(item.category, {"category_id": getattr(item, "category_id", None), "planned": ZERO, "committed": ZERO, "actual": ZERO, "paid": ZERO, "outstanding": ZERO, "count": 0})
        bucket["planned"] = Decimal(str(bucket["planned"])) + normalize_money(item.planned_amount)
        bucket["committed"] = Decimal(str(bucket["committed"])) + normalize_money(item.committed_amount)
        bucket["actual"] = Decimal(str(bucket["actual"])) + normalize_money(getattr(item, "actual_amount", ZERO))
        bucket["paid"] = Decimal(str(bucket["paid"])) + normalize_money(item.paid_amount)
        bucket["outstanding"] = Decimal(str(bucket["outstanding"])) + outstanding_amount(item)
        bucket["count"] = int(bucket["count"]) + 1

    category_breakdown = [
        BudgetCategorySummary(
            category_id=values["category_id"] if isinstance(values["category_id"], UUID) else None,
            category=category,
            planned_amount=Decimal(str(values["planned"])),
            committed_amount=Decimal(str(values["committed"])),
            actual_amount=Decimal(str(values["actual"])),
            paid_amount=Decimal(str(values["paid"])),
            outstanding_amount=Decimal(str(values["outstanding"])),
            item_count=int(values["count"]),
        )
        for category, values in sorted(categories.items(), key=lambda row: str(row[0]).lower())
    ]
    upcoming = [
        BudgetUpcomingPayment(
            id=item.id,
            name=item.name,
            category=item.category,
            due_date=item.due_date,
            outstanding_amount=outstanding_amount(item),
            currency=item.currency,
        )
        for item in sorted(upcoming_items, key=lambda current: current.due_date or date.max)[:5]
        if item.due_date
    ]
    utilization = round((total_committed / total_planned) * 100) if total_planned else 0
    paid_percentage = round((total_paid / total_committed) * 100) if total_committed else 0
    return BudgetItemSummary(
        project_id=project_id,
        total_items=len(items),
        total_planned=total_planned,
        total_committed=total_committed,
        total_actual=total_actual,
        total_paid=total_paid,
        total_outstanding=total_outstanding,
        unpaid_items=sum(1 for item in items if outstanding_amount(item) > ZERO and item.status not in {"PAID", "CANCELLED"}),
        overdue_items=overdue_items,
        upcoming_payments_count=len(upcoming_items),
        paid_items=paid_items,
        partially_paid_items=partially_paid_items,
        utilization_percentage=utilization,
        paid_percentage=paid_percentage,
        variance_amount=total_actual - total_planned if total_actual > ZERO else ZERO,
        category_breakdown=category_breakdown,
        upcoming_payments=upcoming,
    )
