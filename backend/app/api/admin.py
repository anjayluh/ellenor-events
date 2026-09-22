from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.billing import serialize_payment, serialize_subscription
from app.api.catalog import serialize_grant, serialize_package, serialize_price
from app.api.dependencies import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.billing import CustomerSubscription, MarketingAccessToken, PaymentTransaction
from app.models.catalog import PackagePlan
from app.models.customer_account import AccountEntitlement, CustomerAccount, CustomerAccountMember
from app.models.project import Project
from app.models.staff_member import StaffMember
from app.models.user import User
from app.schemas.admin import AdminPermissionGrant, AuditLogRead, CustomerAccountAdminRead, StaffMemberRead, UserAdminRead
from app.schemas.billing import (
    CustomerSubscriptionRead,
    MarketingAccessTokenCreate,
    MarketingAccessTokenRead,
    MarketingAccessTokenUpdate,
    PaymentTransactionRead,
)
from app.schemas.catalog import (
    EntitlementDefinitionRead,
    PackageEntitlementGrantCreate,
    PackageEntitlementGrantRead,
    PackageEntitlementGrantUpdate,
    PackagePlanCreate,
    PackagePlanRead,
    PackagePlanUpdate,
    PackagePriceCreate,
    PackagePriceRead,
    PackagePriceUpdate,
)
from app.services.billing_service import create_marketing_access_token, update_marketing_access_token
from app.services.catalog_service import (
    create_package,
    create_package_price,
    get_package_or_404,
    get_price_or_404,
    list_packages_for_admin,
    set_package_status,
    update_package,
    update_package_price,
)
from app.services.package_entitlement_service import create_package_grant, get_package_grant_or_404, list_entitlement_definitions, update_package_grant
from app.services.audit_service import write_audit_log
from app.services.auth_service import normalize_email

router = APIRouter()

ALL_ADMIN_PERMISSIONS = {
    "admin.users.view",
    "admin.users.manage",
    "admin.logs.view",
    "admin.permissions.manage",
    "admin.projects.view",
    "admin.projects.manage",
    "admin.vendors.view",
    "admin.vendors.manage",
    "admin.catalog.view",
    "admin.catalog.manage",
    "admin.billing.view",
    "admin.billing.manage",
}


def staff_permissions(staff_member: StaffMember) -> set[str]:
    if staff_member.role == "SUPER_ADMIN":
        return set(ALL_ADMIN_PERMISSIONS)
    raw_permissions = staff_member.permissions_json or {}
    permissions = raw_permissions.get("permissions", raw_permissions if isinstance(raw_permissions, list) else [])
    return {str(permission) for permission in permissions}


def serialize_staff(staff_member: StaffMember, user: User | None = None) -> StaffMemberRead:
    return StaffMemberRead(
        id=staff_member.id,
        user_id=staff_member.user_id,
        email=user.email if user else None,
        name=user.name if user else None,
        role=staff_member.role,
        permissions=sorted(staff_permissions(staff_member)),
        status=staff_member.status,
    )


def require_admin_permission(
    permission: str,
    current_user: CurrentUser,
    db: Session,
) -> StaffMember:
    staff_member = (
        db.query(StaffMember)
        .filter(StaffMember.user_id == current_user.id, StaffMember.status == "active")
        .first()
    )
    if not staff_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    permissions = staff_permissions(staff_member)
    if permission not in permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")
    return staff_member


def require_active_staff(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> StaffMember:
    staff_member = (
        db.query(StaffMember)
        .filter(StaffMember.user_id == current_user.id, StaffMember.status == "active")
        .first()
    )
    if not staff_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return staff_member


def require_users_view(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> StaffMember:
    return require_admin_permission("admin.users.view", current_user, db)


def require_users_manage(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> StaffMember:
    return require_admin_permission("admin.users.manage", current_user, db)


def require_logs_view(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> StaffMember:
    return require_admin_permission("admin.logs.view", current_user, db)


def require_permissions_manage(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> StaffMember:
    return require_admin_permission("admin.permissions.manage", current_user, db)


def require_projects_view(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> StaffMember:
    return require_admin_permission("admin.projects.view", current_user, db)


def require_catalog_view(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> StaffMember:
    return require_admin_permission("admin.catalog.view", current_user, db)


def require_catalog_manage(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> StaffMember:
    return require_admin_permission("admin.catalog.manage", current_user, db)


def require_billing_view(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> StaffMember:
    return require_admin_permission("admin.billing.view", current_user, db)


def require_billing_manage(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> StaffMember:
    return require_admin_permission("admin.billing.manage", current_user, db)


@router.get("/me", response_model=StaffMemberRead)
def admin_me(staff_member: StaffMember = Depends(require_active_staff), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == staff_member.user_id).first()
    return serialize_staff(staff_member, user)


@router.get("/users", response_model=list[UserAdminRead])
def list_users(staff_member: StaffMember = Depends(require_users_view), db: Session = Depends(get_db)):
    write_audit_log(db, "admin.users_viewed", actor_user_id=staff_member.user_id)
    db.commit()
    return db.query(User).order_by(User.created_at.desc()).limit(250).all()


@router.get("/staff", response_model=list[StaffMemberRead])
def list_staff(staff_member: StaffMember = Depends(require_permissions_manage), db: Session = Depends(get_db)):
    rows = db.query(StaffMember, User).join(User, User.id == StaffMember.user_id).order_by(User.email.asc()).all()
    write_audit_log(db, "admin.staff_viewed", actor_user_id=staff_member.user_id)
    db.commit()
    return [serialize_staff(row_staff, user) for row_staff, user in rows]


@router.post("/staff", response_model=StaffMemberRead)
def grant_staff_permissions(payload: AdminPermissionGrant, staff_member: StaffMember = Depends(require_permissions_manage), db: Session = Depends(get_db)):
    email = normalize_email(str(payload.email))
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.flush()

    target = db.query(StaffMember).filter(StaffMember.user_id == user.id).first()
    if not target:
        target = StaffMember(user_id=user.id)
        db.add(target)
    target.role = payload.role
    target.status = payload.status
    target.permissions_json = {"permissions": sorted(set(payload.permissions))}
    write_audit_log(
        db,
        "admin.staff_permissions_updated",
        actor_user_id=staff_member.user_id,
        metadata={"target_user_id": str(user.id), "role": payload.role, "permissions": payload.permissions},
    )
    db.commit()
    db.refresh(target)
    return serialize_staff(target, user)


@router.delete("/staff/{user_id}")
def revoke_staff_access(user_id: UUID, staff_member: StaffMember = Depends(require_permissions_manage), db: Session = Depends(get_db)):
    target = db.query(StaffMember).filter(StaffMember.user_id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")
    if target.role == "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Super admin access cannot be removed here")
    target.status = "inactive"
    write_audit_log(db, "admin.staff_access_revoked", actor_user_id=staff_member.user_id, metadata={"target_user_id": str(user_id)})
    db.commit()
    return {"status": "inactive"}


@router.get("/logs", response_model=list[AuditLogRead])
def list_audit_logs(staff_member: StaffMember = Depends(require_logs_view), db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(250).all()
    write_audit_log(db, "admin.logs_viewed", actor_user_id=staff_member.user_id)
    db.commit()
    return [
        AuditLogRead(
            id=log.id,
            actor_user_id=log.actor_user_id,
            project_id=log.project_id,
            action=log.action,
            metadata=log.metadata_json or {},
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get("/customer-accounts", response_model=list[CustomerAccountAdminRead])
def list_customer_accounts(staff_member: StaffMember = Depends(require_projects_view), db: Session = Depends(get_db)):
    project_counts = dict(db.query(Project.customer_account_id, func.count(Project.id)).group_by(Project.customer_account_id).all())
    entitlement_counts = dict(db.query(AccountEntitlement.customer_account_id, func.count(AccountEntitlement.id)).group_by(AccountEntitlement.customer_account_id).all())
    owner_rows = (
        db.query(CustomerAccountMember.customer_account_id, User.id, User.email)
        .join(User, User.id == CustomerAccountMember.user_id)
        .filter(CustomerAccountMember.role == "OWNER", CustomerAccountMember.status == "ACTIVE")
        .all()
    )
    owners = {account_id: (user_id, email) for account_id, user_id, email in owner_rows}
    write_audit_log(db, "admin.customer_accounts_viewed", actor_user_id=staff_member.user_id)
    db.commit()
    return [
        CustomerAccountAdminRead(
            id=account.id,
            name=account.name,
            status=account.status,
            owner_user_id=owners.get(account.id, (None, None))[0],
            owner_email=owners.get(account.id, (None, None))[1],
            project_count=project_counts.get(account.id, 0),
            entitlement_count=entitlement_counts.get(account.id, 0),
            created_at=account.created_at,
        )
        for account in db.query(CustomerAccount).order_by(CustomerAccount.created_at.desc()).limit(250).all()
    ]


@router.get("/catalog/entitlement-definitions", response_model=list[EntitlementDefinitionRead])
def admin_list_entitlement_definitions(staff_member: StaffMember = Depends(require_catalog_view), db: Session = Depends(get_db)):
    write_audit_log(db, "admin.catalog_entitlements_viewed", actor_user_id=staff_member.user_id)
    db.commit()
    return list_entitlement_definitions(db)


@router.get("/catalog/packages", response_model=list[PackagePlanRead])
def admin_list_packages(staff_member: StaffMember = Depends(require_catalog_view), db: Session = Depends(get_db)):
    write_audit_log(db, "admin.catalog_packages_viewed", actor_user_id=staff_member.user_id)
    db.commit()
    return [serialize_package(package, db) for package in list_packages_for_admin(db)]


@router.post("/catalog/packages", response_model=PackagePlanRead)
def admin_create_package(payload: PackagePlanCreate, staff_member: StaffMember = Depends(require_catalog_manage), db: Session = Depends(get_db)):
    package = create_package(db, payload)
    write_audit_log(db, "admin.catalog_package_created", actor_user_id=staff_member.user_id, metadata={"package_code": package.code})
    db.commit()
    db.refresh(package)
    return serialize_package(package, db)


@router.patch("/catalog/packages/{package_plan_id}", response_model=PackagePlanRead)
def admin_update_package(package_plan_id: UUID, payload: PackagePlanUpdate, staff_member: StaffMember = Depends(require_catalog_manage), db: Session = Depends(get_db)):
    package = update_package(db, get_package_or_404(db, package_plan_id), payload)
    write_audit_log(db, "admin.catalog_package_updated", actor_user_id=staff_member.user_id, metadata={"package_id": str(package.id)})
    db.commit()
    db.refresh(package)
    return serialize_package(package, db)


@router.post("/catalog/packages/{package_plan_id}/deactivate", response_model=PackagePlanRead)
def admin_deactivate_package(package_plan_id: UUID, staff_member: StaffMember = Depends(require_catalog_manage), db: Session = Depends(get_db)):
    package = set_package_status(db, get_package_or_404(db, package_plan_id), "INACTIVE")
    write_audit_log(db, "admin.catalog_package_deactivated", actor_user_id=staff_member.user_id, metadata={"package_id": str(package.id)})
    db.commit()
    db.refresh(package)
    return serialize_package(package, db)


@router.post("/catalog/packages/{package_plan_id}/archive", response_model=PackagePlanRead)
def admin_archive_package(package_plan_id: UUID, staff_member: StaffMember = Depends(require_catalog_manage), db: Session = Depends(get_db)):
    package = set_package_status(db, get_package_or_404(db, package_plan_id), "ARCHIVED")
    write_audit_log(db, "admin.catalog_package_archived", actor_user_id=staff_member.user_id, metadata={"package_id": str(package.id)})
    db.commit()
    db.refresh(package)
    return serialize_package(package, db)


@router.post("/catalog/packages/{package_plan_id}/prices", response_model=PackagePriceRead)
def admin_create_package_price(package_plan_id: UUID, payload: PackagePriceCreate, staff_member: StaffMember = Depends(require_catalog_manage), db: Session = Depends(get_db)):
    price = create_package_price(db, get_package_or_404(db, package_plan_id), payload)
    write_audit_log(db, "admin.catalog_price_created", actor_user_id=staff_member.user_id, metadata={"package_id": str(package_plan_id)})
    db.commit()
    db.refresh(price)
    return serialize_price(price)


@router.patch("/catalog/prices/{price_id}", response_model=PackagePriceRead)
def admin_update_package_price(price_id: UUID, payload: PackagePriceUpdate, staff_member: StaffMember = Depends(require_catalog_manage), db: Session = Depends(get_db)):
    price = update_package_price(db, get_price_or_404(db, price_id), payload)
    write_audit_log(db, "admin.catalog_price_updated", actor_user_id=staff_member.user_id, metadata={"price_id": str(price.id)})
    db.commit()
    db.refresh(price)
    return serialize_price(price)


@router.post("/catalog/packages/{package_plan_id}/grants", response_model=PackageEntitlementGrantRead)
def admin_create_package_grant(package_plan_id: UUID, payload: PackageEntitlementGrantCreate, staff_member: StaffMember = Depends(require_catalog_manage), db: Session = Depends(get_db)):
    grant = create_package_grant(db, get_package_or_404(db, package_plan_id), payload)
    write_audit_log(db, "admin.catalog_grant_created", actor_user_id=staff_member.user_id, metadata={"package_id": str(package_plan_id), "entitlement_key": grant.entitlement_key})
    db.commit()
    db.refresh(grant)
    return serialize_grant(grant)


@router.patch("/catalog/grants/{grant_id}", response_model=PackageEntitlementGrantRead)
def admin_update_package_grant(grant_id: UUID, payload: PackageEntitlementGrantUpdate, staff_member: StaffMember = Depends(require_catalog_manage), db: Session = Depends(get_db)):
    grant = update_package_grant(db, get_package_grant_or_404(db, grant_id), payload)
    write_audit_log(db, "admin.catalog_grant_updated", actor_user_id=staff_member.user_id, metadata={"grant_id": str(grant.id)})
    db.commit()
    db.refresh(grant)
    return serialize_grant(grant)


@router.get("/billing/subscriptions", response_model=list[CustomerSubscriptionRead])
def admin_list_subscriptions(staff_member: StaffMember = Depends(require_billing_view), db: Session = Depends(get_db)):
    write_audit_log(db, "admin.billing_subscriptions_viewed", actor_user_id=staff_member.user_id)
    db.commit()
    subscriptions = db.query(CustomerSubscription).order_by(CustomerSubscription.created_at.desc()).limit(250).all()
    return [serialize_subscription(subscription, db) for subscription in subscriptions]


@router.get("/billing/payments", response_model=list[PaymentTransactionRead])
def admin_list_payments(staff_member: StaffMember = Depends(require_billing_view), db: Session = Depends(get_db)):
    write_audit_log(db, "admin.billing_payments_viewed", actor_user_id=staff_member.user_id)
    db.commit()
    return [serialize_payment(transaction) for transaction in db.query(PaymentTransaction).order_by(PaymentTransaction.created_at.desc()).limit(250).all()]


@router.get("/billing/access-tokens", response_model=list[MarketingAccessTokenRead])
def admin_list_access_tokens(staff_member: StaffMember = Depends(require_billing_view), db: Session = Depends(get_db)):
    write_audit_log(db, "admin.billing_access_tokens_viewed", actor_user_id=staff_member.user_id)
    db.commit()
    return db.query(MarketingAccessToken).order_by(MarketingAccessToken.created_at.desc()).limit(250).all()


@router.post("/billing/access-tokens", response_model=MarketingAccessTokenRead)
def admin_create_access_token(payload: MarketingAccessTokenCreate, staff_member: StaffMember = Depends(require_billing_manage), db: Session = Depends(get_db)):
    token = create_marketing_access_token(db, payload, created_by=staff_member.user_id)
    write_audit_log(db, "admin.billing_access_token_created", actor_user_id=staff_member.user_id, metadata={"access_token_id": str(token.id)})
    db.commit()
    db.refresh(token)
    return token


@router.patch("/billing/access-tokens/{access_token_id}", response_model=MarketingAccessTokenRead)
def admin_update_access_token(access_token_id: UUID, payload: MarketingAccessTokenUpdate, staff_member: StaffMember = Depends(require_billing_manage), db: Session = Depends(get_db)):
    token = db.query(MarketingAccessToken).filter(MarketingAccessToken.id == access_token_id).first()
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access token not found")
    update_marketing_access_token(db, token, payload)
    write_audit_log(db, "admin.billing_access_token_updated", actor_user_id=staff_member.user_id, metadata={"access_token_id": str(token.id)})
    db.commit()
    db.refresh(token)
    return token
