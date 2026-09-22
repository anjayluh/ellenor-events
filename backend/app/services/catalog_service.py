from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.catalog import PackageEntitlementGrant, PackagePlan, PackagePrice
from app.schemas.catalog import PackagePlanCreate, PackagePlanUpdate, PackagePriceCreate, PackagePriceUpdate


def current_time() -> datetime:
    return datetime.now(timezone.utc)


def comparable_time(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def price_is_current(price: PackagePrice, *, now: datetime | None = None) -> bool:
    current = now or current_time()
    if price.status != "ACTIVE":
        return False
    if price.starts_at and comparable_time(price.starts_at) > current:
        return False
    if price.ends_at and comparable_time(price.ends_at) <= current:
        return False
    return True


def package_is_publicly_visible(package: PackagePlan) -> bool:
    return package.status == "ACTIVE" and package.is_public


def list_public_packages(db: Session) -> list[PackagePlan]:
    return (
        db.query(PackagePlan)
        .filter(PackagePlan.status == "ACTIVE", PackagePlan.is_public.is_(True))
        .order_by(PackagePlan.display_order.asc(), PackagePlan.name.asc())
        .all()
    )


def get_public_package_by_code(db: Session, code: str) -> PackagePlan:
    package = db.query(PackagePlan).filter(PackagePlan.code == code, PackagePlan.status == "ACTIVE", PackagePlan.is_public.is_(True)).first()
    if not package:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    return package


def list_packages_for_admin(db: Session) -> list[PackagePlan]:
    return db.query(PackagePlan).order_by(PackagePlan.display_order.asc(), PackagePlan.name.asc()).all()


def get_package_or_404(db: Session, package_plan_id: UUID) -> PackagePlan:
    package = db.query(PackagePlan).filter(PackagePlan.id == package_plan_id).first()
    if not package:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    return package


def get_package_by_code_or_404(db: Session, code: str) -> PackagePlan:
    package = db.query(PackagePlan).filter(PackagePlan.code == code).first()
    if not package:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    return package


def create_package(db: Session, payload: PackagePlanCreate) -> PackagePlan:
    existing = db.query(PackagePlan).filter(PackagePlan.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Package code already exists")
    package = PackagePlan(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        is_public=payload.is_public,
        is_add_on=payload.is_add_on,
        display_order=payload.display_order,
        metadata_json=payload.metadata,
    )
    db.add(package)
    db.flush()
    return package


def update_package(db: Session, package: PackagePlan, payload: PackagePlanUpdate) -> PackagePlan:
    values = payload.model_dump(exclude_unset=True)
    if "code" in values:
        existing = db.query(PackagePlan).filter(PackagePlan.code == values["code"], PackagePlan.id != package.id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Package code already exists")
    for field, value in values.items():
        setattr(package, "metadata_json" if field == "metadata" else field, value)
    package.updated_at = current_time()
    db.flush()
    return package


def set_package_status(db: Session, package: PackagePlan, status_value: str) -> PackagePlan:
    package.status = status_value
    package.updated_at = current_time()
    db.flush()
    return package


def list_package_prices(db: Session, package_plan_id: UUID, *, public_only: bool = False) -> list[PackagePrice]:
    prices = db.query(PackagePrice).filter(PackagePrice.package_plan_id == package_plan_id).order_by(PackagePrice.created_at.asc()).all()
    if public_only:
        return [price for price in prices if price_is_current(price)]
    return prices


def get_price_or_404(db: Session, price_id: UUID) -> PackagePrice:
    price = db.query(PackagePrice).filter(PackagePrice.id == price_id).first()
    if not price:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package price not found")
    return price


def create_package_price(db: Session, package: PackagePlan, payload: PackagePriceCreate) -> PackagePrice:
    price = PackagePrice(package_plan_id=package.id, **payload.model_dump())
    db.add(price)
    db.flush()
    return price


def update_package_price(db: Session, price: PackagePrice, payload: PackagePriceUpdate) -> PackagePrice:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(price, field, value)
    price.updated_at = current_time()
    db.flush()
    return price


def list_package_grants(db: Session, package_plan_id: UUID) -> list[PackageEntitlementGrant]:
    return (
        db.query(PackageEntitlementGrant)
        .filter(PackageEntitlementGrant.package_plan_id == package_plan_id)
        .order_by(PackageEntitlementGrant.created_at.asc())
        .all()
    )
