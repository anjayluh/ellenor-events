from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.catalog import EntitlementDefinition, PackageEntitlementGrant, PackagePlan
from app.schemas.catalog import PackageEntitlementGrantCreate, PackageEntitlementGrantUpdate


def list_entitlement_definitions(db: Session) -> list[EntitlementDefinition]:
    return db.query(EntitlementDefinition).order_by(EntitlementDefinition.key.asc()).all()


def get_entitlement_definition_or_404(db: Session, key: str) -> EntitlementDefinition:
    definition = db.query(EntitlementDefinition).filter(EntitlementDefinition.key == key).first()
    if not definition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entitlement definition not found")
    return definition


def validate_grant_against_definition(definition: EntitlementDefinition, *, scope: str, value_type: str, quantity: int | None) -> None:
    if definition.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Entitlement definition is not active")
    if definition.scope != scope:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Grant scope must match entitlement definition")
    if definition.value_type != value_type:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Grant value type must match entitlement definition")
    if value_type == "QUANTITY" and (quantity is None or quantity <= 0):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Quantity entitlements require a positive quantity")
    if value_type in {"BOOLEAN", "UNLIMITED"} and quantity is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Boolean and unlimited entitlements cannot have a quantity")


def get_package_grants(db: Session, package_plan_id: UUID) -> list[PackageEntitlementGrant]:
    return (
        db.query(PackageEntitlementGrant)
        .filter(PackageEntitlementGrant.package_plan_id == package_plan_id)
        .order_by(PackageEntitlementGrant.created_at.asc())
        .all()
    )


def create_package_grant(db: Session, package: PackagePlan, payload: PackageEntitlementGrantCreate) -> PackageEntitlementGrant:
    definition = get_entitlement_definition_or_404(db, payload.entitlement_key)
    validate_grant_against_definition(definition, scope=payload.scope, value_type=payload.value_type, quantity=payload.quantity)
    duplicate = (
        db.query(PackageEntitlementGrant)
        .filter(PackageEntitlementGrant.package_plan_id == package.id, PackageEntitlementGrant.entitlement_key == payload.entitlement_key)
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Package already grants this entitlement")
    grant = PackageEntitlementGrant(
        package_plan_id=package.id,
        entitlement_key=payload.entitlement_key,
        scope=payload.scope,
        value_type=payload.value_type,
        quantity=payload.quantity,
        duration_days=payload.duration_days,
        metadata_json=payload.metadata,
    )
    db.add(grant)
    db.flush()
    return grant


def get_package_grant_or_404(db: Session, grant_id: UUID) -> PackageEntitlementGrant:
    grant = db.query(PackageEntitlementGrant).filter(PackageEntitlementGrant.id == grant_id).first()
    if not grant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package entitlement grant not found")
    return grant


def update_package_grant(db: Session, grant: PackageEntitlementGrant, payload: PackageEntitlementGrantUpdate) -> PackageEntitlementGrant:
    scope = payload.scope if payload.scope is not None else grant.scope
    value_type = payload.value_type if payload.value_type is not None else grant.value_type
    quantity = payload.quantity if "quantity" in payload.model_fields_set else grant.quantity
    definition = get_entitlement_definition_or_404(db, grant.entitlement_key)
    validate_grant_against_definition(definition, scope=scope, value_type=value_type, quantity=quantity)
    values = payload.model_dump(exclude_unset=True)
    for field, value in values.items():
        setattr(grant, "metadata_json" if field == "metadata" else field, value)
    grant.updated_at = datetime.now(timezone.utc)
    db.flush()
    return grant


def normalized_package_entitlements(db: Session, package_plan_id: UUID) -> list[dict]:
    return [
        {
            "entitlement_key": grant.entitlement_key,
            "scope": grant.scope,
            "value_type": grant.value_type,
            "quantity": grant.quantity,
            "duration_days": grant.duration_days,
            "metadata": grant.metadata_json or {},
        }
        for grant in get_package_grants(db, package_plan_id)
    ]
