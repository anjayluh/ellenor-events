from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.budget import ProjectBudgetItem
from app.models.customer_account import AccountEntitlement
from app.models.project import Project
from app.models.vendor import Vendor
from app.schemas.vendor import (
    VENDOR_CATEGORIES,
    VENDOR_STATUSES,
    VendorBudgetItemRead,
    VendorCreate,
    VendorFinancialSummary,
    VendorRead,
    VendorSummary,
    VendorUpdate,
    VendorUsageRead,
)
from app.services.entitlement_service import active_entitlements, entitlement_is_active, entitlement_priority
from app.services.project_budget_service import normalize_money, outstanding_amount

VENDORS_PER_EVENT_ENTITLEMENT_KEY = "vendors_per_event"
CONFIRMED_VENDOR_STATUSES = {"BOOKED", "CONFIRMED", "COMPLETED"}
NEEDS_ATTENTION_STATUSES = {"PROSPECT", "SHORTLISTED", "CONTACTED", "QUOTED"}
ZERO = Decimal("0")
CATEGORY_ALIASES = {
    "PA / SOUND": "PA_SOUND",
    "PA SOUND": "PA_SOUND",
    "SOUND": "PA_SOUND",
    "DJ": "DJ_ENTERTAINMENT",
    "ENTERTAINMENT": "DJ_ENTERTAINMENT",
    "DJ / ENTERTAINMENT": "DJ_ENTERTAINMENT",
    "MAKEUP": "MAKEUP_BEAUTY",
    "HAIR": "MAKEUP_BEAUTY",
    "BEAUTY": "MAKEUP_BEAUTY",
    "MAKEUP / BEAUTY": "MAKEUP_BEAUTY",
    "PLANNER / COORDINATOR": "OTHER",
    "PLANNER": "OTHER",
    "COORDINATOR": "OTHER",
    "INVITATIONS": "STATIONERY",
    "INVITATIONS & STATIONERY": "STATIONERY",
}
STATUS_ALIASES = {
    "DECLINED": "CANCELLED",
    "REJECTED": "CANCELLED",
    "QUOTE_REQUESTED": "QUOTED",
    "PREFERRED": "BOOKED",
}


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def normalize_category(value: str) -> str:
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    readable = value.strip().upper()
    normalized = CATEGORY_ALIASES.get(readable, normalized)
    if normalized not in VENDOR_CATEGORIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported vendor category")
    return normalized


def normalize_status(value: str) -> str:
    normalized = value.strip().upper()
    normalized = STATUS_ALIASES.get(normalized, normalized)
    if normalized not in VENDOR_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported vendor status")
    return normalized


def project_or_404(db: Session, project_id: UUID, *, lock: bool = False) -> Project:
    query = db.query(Project).filter(Project.id == project_id)
    if lock:
        query = query.with_for_update()
    project = query.first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def active_vendor_entitlements_for_update(db: Session, customer_account_id: UUID) -> list[AccountEntitlement]:
    entitlements = [
        entitlement
        for entitlement in db.query(AccountEntitlement)
        .filter(AccountEntitlement.customer_account_id == customer_account_id, AccountEntitlement.key == VENDORS_PER_EVENT_ENTITLEMENT_KEY)
        .with_for_update()
        .all()
        if entitlement_is_active(entitlement)
    ]
    return sorted(entitlements, key=entitlement_priority)


def resolve_event_vendor_entitlement(db: Session, customer_account_id: UUID) -> AccountEntitlement:
    entitlements = active_entitlements(db, customer_account_id, VENDORS_PER_EVENT_ENTITLEMENT_KEY)
    if not entitlements:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"code": "VENDOR_ENTITLEMENT_REQUIRED", "message": "Choose an active package before adding vendors."},
        )
    return entitlements[0]


def vendor_count(db: Session, project_id: UUID) -> int:
    return db.query(Vendor).filter(Vendor.project_id == project_id).count()


def usage_from_count(used: int, limit: int | None) -> VendorUsageRead:
    return VendorUsageRead(
        key=VENDORS_PER_EVENT_ENTITLEMENT_KEY,
        label="Vendors",
        used=used,
        limit=limit,
        remaining=None if limit is None else max(limit - used, 0),
    )


def vendor_usage(db: Session, project: Project) -> VendorUsageRead:
    entitlement = resolve_event_vendor_entitlement(db, project.customer_account_id)
    return usage_from_count(vendor_count(db, project.id), entitlement.quantity)


def assert_vendor_capacity(db: Session, project: Project) -> None:
    project_or_404(db, project.id, lock=True)
    entitlements = active_vendor_entitlements_for_update(db, project.customer_account_id)
    if not entitlements:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"code": "VENDOR_ENTITLEMENT_REQUIRED", "message": "Choose an active package before adding vendors."},
        )
    current_count = vendor_count(db, project.id)
    for entitlement in entitlements:
        if entitlement.quantity is None or current_count + 1 <= entitlement.quantity:
            return
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={"code": "VENDOR_ENTITLEMENT_REQUIRED", "message": "This event has reached its vendor limit for the current package."},
    )


def vendor_budget_items(db: Session, vendor: Vendor) -> list[ProjectBudgetItem]:
    return db.query(ProjectBudgetItem).filter(ProjectBudgetItem.project_id == vendor.project_id, ProjectBudgetItem.vendor_id == vendor.id).order_by(ProjectBudgetItem.due_date.asc().nullslast(), ProjectBudgetItem.created_at.desc()).all()


def serialize_vendor_budget_item(item: ProjectBudgetItem) -> VendorBudgetItemRead:
    return VendorBudgetItemRead(
        id=item.id,
        name=item.name,
        category=item.category,
        planned_amount=normalize_money(item.planned_amount),
        committed_amount=normalize_money(item.committed_amount),
        actual_amount=normalize_money(item.actual_amount),
        paid_amount=normalize_money(item.paid_amount),
        outstanding_amount=outstanding_amount(item),
        currency=item.currency,
        status=item.status,
        due_date=item.due_date,
    )


def financial_summary_for_items(items: list[ProjectBudgetItem]) -> VendorFinancialSummary:
    planned = sum((normalize_money(item.planned_amount) for item in items), ZERO)
    committed = sum((normalize_money(item.committed_amount) for item in items), ZERO)
    actual = sum((normalize_money(item.actual_amount) for item in items), ZERO)
    paid = sum((normalize_money(item.paid_amount) for item in items), ZERO)
    outstanding = sum((outstanding_amount(item) for item in items if item.status != "CANCELLED"), ZERO)
    payable = actual if actual > ZERO else committed
    payment_percentage = round((paid / payable) * 100) if payable else 0
    return VendorFinancialSummary(
        planned_total=normalize_money(planned),
        committed_total=normalize_money(committed),
        actual_total=normalize_money(actual),
        paid_total=normalize_money(paid),
        outstanding_total=normalize_money(outstanding),
        variance_amount=normalize_money(actual - planned if actual > ZERO else ZERO),
        payment_percentage=payment_percentage,
        linked_budget_items_count=len(items),
    )


def serialize_vendor(db: Session, vendor: Vendor, *, include_budget_items: bool = False) -> VendorRead:
    items = vendor_budget_items(db, vendor)
    return VendorRead(
        id=vendor.id,
        project_id=vendor.project_id,
        name=vendor.name,
        category=vendor.category,
        contact_person=vendor.contact_person,
        phone=vendor.phone,
        email=vendor.email,
        address=vendor.address,
        website=vendor.website,
        service_description=vendor.service_description,
        status=vendor.status,
        notes=vendor.notes,
        event_day_contact=vendor.event_day_contact,
        booking_date=vendor.booking_date,
        financial_summary=financial_summary_for_items(items),
        budget_items=[serialize_vendor_budget_item(item) for item in items] if include_budget_items else [],
        created_at=vendor.created_at,
        updated_at=vendor.updated_at,
    )


def list_project_vendors(
    db: Session,
    project_id: UUID,
    *,
    search: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    payment_status: str | None = None,
    outstanding: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Vendor]:
    query = db.query(Vendor).filter(Vendor.project_id == project_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(Vendor.name.ilike(pattern), Vendor.contact_person.ilike(pattern), Vendor.email.ilike(pattern), Vendor.phone.ilike(pattern), Vendor.service_description.ilike(pattern)))
    if category:
        query = query.filter(Vendor.category == normalize_category(category))
    if status_filter:
        query = query.filter(Vendor.status == normalize_status(status_filter))
    vendors = query.order_by(Vendor.created_at.desc(), Vendor.name.asc()).all()
    if outstanding is True or payment_status in {"unpaid", "partially_paid"}:
        vendors = [vendor for vendor in vendors if financial_summary_for_items(vendor_budget_items(db, vendor)).outstanding_total > ZERO]
    elif payment_status == "paid":
        vendors = [vendor for vendor in vendors if (summary := financial_summary_for_items(vendor_budget_items(db, vendor))).linked_budget_items_count > 0 and summary.outstanding_total == ZERO]
    return vendors[max(offset, 0) : max(offset, 0) + min(max(limit, 1), 250)]


def get_project_vendor_or_404(db: Session, project_id: UUID, vendor_id: UUID) -> Vendor:
    vendor = db.query(Vendor).filter(Vendor.project_id == project_id, Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return vendor


def create_project_vendor(db: Session, project: Project, payload: VendorCreate) -> Vendor:
    assert_vendor_capacity(db, project)
    vendor = Vendor(
        project_id=project.id,
        name=payload.name.strip(),
        category=normalize_category(payload.category),
        contact_person=clean_optional(payload.contact_person),
        phone=clean_optional(payload.phone),
        email=str(payload.email).lower() if payload.email else None,
        address=clean_optional(payload.address),
        website=clean_optional(payload.website),
        service_description=clean_optional(payload.service_description),
        status=normalize_status(payload.status),
        notes=clean_optional(payload.notes),
        event_day_contact=clean_optional(payload.event_day_contact),
        booking_date=payload.booking_date,
    )
    db.add(vendor)
    db.flush()
    return vendor


def update_project_vendor(db: Session, vendor: Vendor, payload: VendorUpdate) -> Vendor:
    updates = payload.model_dump(exclude_unset=True)
    if "category" in updates and updates["category"] is not None:
        updates["category"] = normalize_category(str(updates["category"]))
    if "status" in updates and updates["status"] is not None:
        updates["status"] = normalize_status(str(updates["status"]))
    if "email" in updates and updates["email"]:
        updates["email"] = str(updates["email"]).lower()
    for field in {"name", "contact_person", "phone", "address", "website", "service_description", "notes", "event_day_contact"}:
        if field in updates and updates[field] is not None:
            updates[field] = clean_optional(str(updates[field]))
    for field, value in updates.items():
        setattr(vendor, field, value)
    vendor.updated_at = datetime.now(timezone.utc)
    db.flush()
    return vendor


def assert_vendor_can_be_deleted(db: Session, vendor: Vendor) -> None:
    linked_count = db.query(ProjectBudgetItem).filter(ProjectBudgetItem.project_id == vendor.project_id, ProjectBudgetItem.vendor_id == vendor.id).count()
    if linked_count:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Remove or reassign linked budget items before deleting this vendor")


def vendor_summary(db: Session, project: Project) -> VendorSummary:
    vendors = db.query(Vendor).filter(Vendor.project_id == project.id).all()
    total = len(vendors)
    confirmed = sum(1 for vendor in vendors if vendor.status in {"CONFIRMED", "COMPLETED"})
    booked = sum(1 for vendor in vendors if vendor.status in CONFIRMED_VENDOR_STATUSES)
    needs_attention = sum(1 for vendor in vendors if vendor.status in NEEDS_ATTENTION_STATUSES)
    summaries = [financial_summary_for_items(vendor_budget_items(db, vendor)) for vendor in vendors]
    return VendorSummary(
        project_id=project.id,
        total=total,
        confirmed=confirmed,
        booked=booked,
        needs_attention=needs_attention,
        with_outstanding_balance=sum(1 for summary in summaries if summary.outstanding_total > ZERO),
        outstanding_balance=sum((summary.outstanding_total for summary in summaries), ZERO),
        planned_total=sum((summary.planned_total for summary in summaries), ZERO),
        committed_total=sum((summary.committed_total for summary in summaries), ZERO),
        actual_total=sum((summary.actual_total for summary in summaries), ZERO),
        paid_total=sum((summary.paid_total for summary in summaries), ZERO),
        variance_amount=sum((summary.variance_amount for summary in summaries), ZERO),
        vendor_usage=vendor_usage(db, project),
    )
