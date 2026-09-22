from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.catalog import PackageEntitlementGrant, PackagePlan, PackagePrice
from app.schemas.catalog import PackageEntitlementGrantRead, PackagePlanRead, PackagePriceRead, PublicPackageRead
from app.services.catalog_service import get_public_package_by_code, list_package_prices, list_public_packages
from app.services.package_entitlement_service import get_package_grants

router = APIRouter()


def serialize_price(price: PackagePrice) -> PackagePriceRead:
    return PackagePriceRead.model_validate(price)


def serialize_grant(grant: PackageEntitlementGrant) -> PackageEntitlementGrantRead:
    return PackageEntitlementGrantRead(
        id=grant.id,
        package_plan_id=grant.package_plan_id,
        entitlement_key=grant.entitlement_key,
        scope=grant.scope,
        value_type=grant.value_type,
        quantity=grant.quantity,
        duration_days=grant.duration_days,
        metadata=grant.metadata_json or {},
        created_at=grant.created_at,
        updated_at=grant.updated_at,
    )


def serialize_package(package: PackagePlan, db: Session, *, public: bool = False) -> PackagePlanRead | PublicPackageRead:
    prices = [serialize_price(price) for price in list_package_prices(db, package.id, public_only=public)]
    grants = [serialize_grant(grant) for grant in get_package_grants(db, package.id)]
    payload = {
        "id": package.id,
        "code": package.code,
        "name": package.name,
        "description": package.description,
        "is_add_on": package.is_add_on,
        "display_order": package.display_order,
        "prices": prices,
        "entitlement_grants": grants,
    }
    if public:
        return PublicPackageRead(**payload)
    return PackagePlanRead(
        **payload,
        status=package.status,
        is_public=package.is_public,
        metadata=package.metadata_json or {},
        created_at=package.created_at,
        updated_at=package.updated_at,
    )


@router.get("/packages", response_model=list[PublicPackageRead])
def list_catalog_packages(db: Session = Depends(get_db)):
    return [serialize_package(package, db, public=True) for package in list_public_packages(db)]


@router.get("/packages/{code}", response_model=PublicPackageRead)
def get_catalog_package(code: str, db: Session = Depends(get_db)):
    return serialize_package(get_public_package_by_code(db, code), db, public=True)
