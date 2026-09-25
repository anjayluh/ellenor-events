from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.customer_account import AccountEntitlement
from app.models.project import Project
from app.models.vendor import Vendor
from app.schemas.vendor import VendorCreate, VendorSummary, VendorUpdate, VendorUsageRead
from app.services.entitlement_service import active_entitlements, entitlement_is_active, entitlement_priority

VENDORS_PER_EVENT_ENTITLEMENT_KEY = "vendors_per_event"
VENDOR_STATUSES = {
    "shortlisted",
    "contacted",
    "confirmed",
    "declined",
    "cancelled",
    "quote_requested",
    "preferred",
    "booked",
    "rejected",
    "completed",
}
CONFIRMED_VENDOR_STATUSES = {"confirmed", "booked", "completed"}
PAYMENT_STATUSES = {"not_applicable", "unpaid", "partially_paid", "paid"}
ZERO = Decimal("0")


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def normalize_money(value: Decimal | int | float | str | None) -> Decimal:
    if value is None:
        return ZERO
    amount = Decimal(str(value))
    return amount.quantize(Decimal("0.01"))


def derive_payment_status(agreed_amount: Decimal, amount_paid: Decimal) -> str:
    if agreed_amount == ZERO:
        return "not_applicable"
    if amount_paid == ZERO:
        return "unpaid"
    if amount_paid < agreed_amount:
        return "partially_paid"
    return "paid"


def validate_vendor_financials(agreed_amount: Decimal, amount_paid: Decimal) -> None:
    if agreed_amount < ZERO or amount_paid < ZERO:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Vendor amounts cannot be negative")
    if amount_paid > agreed_amount:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Amount paid cannot exceed the agreed amount")


def apply_vendor_financials(vendor: Vendor, agreed_amount: Decimal, amount_paid: Decimal) -> None:
    validate_vendor_financials(agreed_amount, amount_paid)
    vendor.agreed_amount = agreed_amount
    vendor.amount_paid = amount_paid
    vendor.balance_amount = agreed_amount - amount_paid
    vendor.payment_status = derive_payment_status(agreed_amount, amount_paid)


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


def list_project_vendors(
    db: Session,
    project_id: UUID,
    *,
    search: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    payment_status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Vendor]:
    query = db.query(Vendor).filter(Vendor.project_id == project_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(Vendor.name.ilike(pattern), Vendor.contact_name.ilike(pattern), Vendor.contact.ilike(pattern), Vendor.email.ilike(pattern), Vendor.phone.ilike(pattern)))
    if category:
        query = query.filter(Vendor.category == category)
    if status_filter:
        query = query.filter(Vendor.status == status_filter)
    if payment_status:
        query = query.filter(Vendor.payment_status == payment_status)
    return query.order_by(Vendor.created_at.desc(), Vendor.name.asc()).offset(max(offset, 0)).limit(min(max(limit, 1), 250)).all()


def get_project_vendor_or_404(db: Session, project_id: UUID, vendor_id: UUID) -> Vendor:
    vendor = db.query(Vendor).filter(Vendor.project_id == project_id, Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return vendor


def create_project_vendor(db: Session, project: Project, payload: VendorCreate) -> Vendor:
    assert_vendor_capacity(db, project)
    status_value = payload.status.lower()
    if status_value not in VENDOR_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported vendor status")
    vendor = Vendor(
        project_id=project.id,
        name=payload.name.strip(),
        category=payload.category.strip(),
        contact=clean_optional(payload.contact),
        contact_name=clean_optional(payload.contact_name),
        phone=clean_optional(payload.phone),
        email=str(payload.email).lower() if payload.email else None,
        status=status_value,
        notes=clean_optional(payload.notes),
        external_url=clean_optional(payload.external_url),
    )
    apply_vendor_financials(vendor, normalize_money(payload.agreed_amount), normalize_money(payload.amount_paid))
    db.add(vendor)
    db.flush()
    return vendor


def update_project_vendor(db: Session, vendor: Vendor, payload: VendorUpdate) -> Vendor:
    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] is not None:
        updates["status"] = str(updates["status"]).lower()
        if updates["status"] not in VENDOR_STATUSES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported vendor status")
    for field in {"name", "category"}:
        if field in updates and updates[field] is not None:
            updates[field] = str(updates[field]).strip()
    for field in {"contact", "contact_name", "phone", "notes", "external_url"}:
        if field in updates:
            updates[field] = clean_optional(updates[field])
    if "email" in updates and updates["email"]:
        updates["email"] = str(updates["email"]).lower()

    agreed_amount = normalize_money(updates.pop("agreed_amount", vendor.agreed_amount or ZERO))
    amount_paid = normalize_money(updates.pop("amount_paid", vendor.amount_paid or ZERO))
    for field, value in updates.items():
        if field == "payment_status":
            continue
        setattr(vendor, field, value)
    apply_vendor_financials(vendor, agreed_amount, amount_paid)
    vendor.updated_at = datetime.now(timezone.utc)
    db.flush()
    return vendor


def vendor_summary(db: Session, project: Project) -> VendorSummary:
    vendors = db.query(Vendor).filter(Vendor.project_id == project.id).all()
    total = len(vendors)
    confirmed = sum(1 for vendor in vendors if vendor.status in CONFIRMED_VENDOR_STATUSES)
    needs_attention = total - confirmed
    outstanding_balance = sum((normalize_money(vendor.balance_amount) for vendor in vendors), ZERO)
    return VendorSummary(
        project_id=project.id,
        total=total,
        confirmed=confirmed,
        needs_attention=needs_attention,
        outstanding_balance=outstanding_balance,
        vendor_usage=vendor_usage(db, project),
    )
