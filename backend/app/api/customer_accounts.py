from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.customer_account import AccountEntitlement, CustomerAccount, CustomerAccountMember
from app.schemas.customer_account import AccountEntitlementRead, CustomerAccountMemberRead, CustomerAccountOverview
from app.schemas.project import ProjectRead
from app.services.customer_account_service import list_account_projects, list_user_account_memberships, require_account_member
from app.services.entitlement_service import list_account_entitlements
from app.api.projects import serialize_project

router = APIRouter()


def serialize_entitlement(entitlement: AccountEntitlement) -> AccountEntitlementRead:
    return AccountEntitlementRead(
        id=entitlement.id,
        customer_account_id=entitlement.customer_account_id,
        key=entitlement.key,
        quantity=entitlement.quantity,
        used_quantity=entitlement.used_quantity,
        status=entitlement.status,
        starts_at=entitlement.starts_at,
        expires_at=entitlement.expires_at,
        metadata=entitlement.metadata_json or {},
        created_at=entitlement.created_at,
        updated_at=entitlement.updated_at,
    )


def build_overview(db: Session, account: CustomerAccount, membership: CustomerAccountMember) -> CustomerAccountOverview:
    return CustomerAccountOverview(
        account=account,
        membership=membership,
        entitlements=[serialize_entitlement(entitlement) for entitlement in list_account_entitlements(db, account.id)],
        projects=[ProjectRead(**serialize_project(project).model_dump()) for project in list_account_projects(db, account.id)],
    )


@router.get("", response_model=list[CustomerAccountOverview])
def list_my_customer_accounts(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = list_user_account_memberships(db, current_user.id)
    return [build_overview(db, account, membership) for account, membership in rows]


@router.get("/{customer_account_id}", response_model=CustomerAccountOverview)
def get_customer_account(customer_account_id: UUID, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    membership = require_account_member(db, customer_account_id, current_user.id)
    account = db.query(CustomerAccount).filter(CustomerAccount.id == customer_account_id).first()
    return build_overview(db, account, membership)


@router.get("/{customer_account_id}/memberships/me", response_model=CustomerAccountMemberRead)
def get_my_account_membership(customer_account_id: UUID, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return require_account_member(db, customer_account_id, current_user.id)


@router.get("/{customer_account_id}/entitlements", response_model=list[AccountEntitlementRead])
def get_account_entitlements(customer_account_id: UUID, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_account_member(db, customer_account_id, current_user.id)
    return [serialize_entitlement(entitlement) for entitlement in list_account_entitlements(db, customer_account_id)]


@router.get("/{customer_account_id}/projects", response_model=list[ProjectRead])
def get_account_projects(customer_account_id: UUID, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_account_member(db, customer_account_id, current_user.id)
    return [serialize_project(project) for project in list_account_projects(db, customer_account_id)]
