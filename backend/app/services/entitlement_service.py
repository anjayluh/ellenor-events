from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.customer_account import AccountEntitlement

EVENTS_ENTITLEMENT_KEY = "events"
COMPATIBILITY_ENTITLEMENT_METADATA = {"source": "compatibility_foundation", "compatibility": True}


def comparable_time(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def entitlement_is_active(entitlement: AccountEntitlement, *, now: datetime | None = None) -> bool:
    current = now or datetime.now(timezone.utc)
    if entitlement.status != "ACTIVE":
        return False
    if entitlement.starts_at and comparable_time(entitlement.starts_at) > current:
        return False
    if entitlement.expires_at and comparable_time(entitlement.expires_at) <= current:
        return False
    return True


def list_account_entitlements(db: Session, customer_account_id: UUID) -> list[AccountEntitlement]:
    return (
        db.query(AccountEntitlement)
        .filter(AccountEntitlement.customer_account_id == customer_account_id)
        .order_by(AccountEntitlement.created_at.asc())
        .all()
    )


def create_entitlement(
    db: Session,
    customer_account_id: UUID,
    key: str,
    *,
    quantity: int | None = None,
    used_quantity: int = 0,
    status_value: str = "ACTIVE",
    starts_at: datetime | None = None,
    expires_at: datetime | None = None,
    metadata: dict | None = None,
) -> AccountEntitlement:
    entitlement = AccountEntitlement(
        customer_account_id=customer_account_id,
        key=key,
        quantity=quantity,
        used_quantity=used_quantity,
        status=status_value,
        starts_at=starts_at,
        expires_at=expires_at,
        metadata_json=metadata or {},
    )
    db.add(entitlement)
    db.flush()
    return entitlement


def active_entitlements(db: Session, customer_account_id: UUID, key: str, *, now: datetime | None = None) -> list[AccountEntitlement]:
    entitlements = [
        entitlement
        for entitlement in db.query(AccountEntitlement)
        .filter(AccountEntitlement.customer_account_id == customer_account_id, AccountEntitlement.key == key)
        .order_by(AccountEntitlement.created_at.asc())
        .all()
        if entitlement_is_active(entitlement, now=now)
    ]
    return sorted(entitlements, key=entitlement_priority)


def entitlement_priority(entitlement: AccountEntitlement) -> int:
    source = str((entitlement.metadata_json or {}).get("source", "")).upper()
    if source == "PAID":
        return 0
    if source == "MARKETING":
        return 1
    if (entitlement.metadata_json or {}).get("compatibility") is True:
        return 9
    return 5


def ensure_compatibility_events_entitlement(db: Session, customer_account_id: UUID) -> AccountEntitlement:
    existing = db.query(AccountEntitlement).filter(AccountEntitlement.customer_account_id == customer_account_id, AccountEntitlement.key == EVENTS_ENTITLEMENT_KEY).first()
    if existing:
        return existing
    return create_entitlement(
        db,
        customer_account_id,
        EVENTS_ENTITLEMENT_KEY,
        quantity=None,
        used_quantity=0,
        metadata=COMPATIBILITY_ENTITLEMENT_METADATA,
    )


def assert_entitlement_allows_usage(db: Session, customer_account_id: UUID, key: str, *, amount: int = 1) -> AccountEntitlement:
    entitlements = active_entitlements(db, customer_account_id, key)
    for entitlement in entitlements:
        if entitlement.quantity is None or entitlement.used_quantity + amount <= entitlement.quantity:
            return entitlement
    raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=f"No active {key} entitlement is available for this customer account")


def consume_entitlement_usage(db: Session, entitlement: AccountEntitlement, *, amount: int = 1) -> AccountEntitlement:
    entitlement.used_quantity = (entitlement.used_quantity or 0) + amount
    entitlement.updated_at = datetime.now(timezone.utc)
    db.flush()
    return entitlement
