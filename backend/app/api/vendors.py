from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_project_membership, membership_role
from app.core.permissions import PROJECT_ADMIN_ROLES, VENDORS_MANAGE_PERMISSION, require_permission
from app.db.session import get_db
from app.schemas.vendor import VendorCreate, VendorRead, VendorSummary, VendorUpdate
from app.services.audit_service import write_audit_log
from app.services.project_vendor_service import (
    create_project_vendor,
    get_project_vendor_or_404,
    list_project_vendors,
    project_or_404,
    update_project_vendor,
    vendor_summary,
)

router = APIRouter()
VENDOR_WRITE_ROLES = PROJECT_ADMIN_ROLES


def require_vendor_manager(membership):
    require_permission(membership_role(membership), getattr(membership, "permissions_json", None), VENDOR_WRITE_ROLES, VENDORS_MANAGE_PERMISSION)


def serialize_vendor(vendor) -> VendorRead:
    return VendorRead.model_validate(vendor)


@router.get("", response_model=list[VendorRead])
def list_vendors(
    project_id: UUID,
    search: str | None = None,
    category: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    payment_status: str | None = None,
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    return [
        serialize_vendor(vendor)
        for vendor in list_project_vendors(
            db,
            project_id,
            search=search,
            category=category,
            status_filter=status_filter,
            payment_status=payment_status,
            limit=limit,
            offset=offset,
        )
    ]


@router.get("/summary", response_model=VendorSummary)
def get_vendor_summary(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    project = project_or_404(db, project_id)
    return vendor_summary(db, project)


@router.post("", response_model=VendorRead)
def create_vendor(project_id: UUID, payload: VendorCreate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_vendor_manager(membership)
    project = project_or_404(db, project_id, lock=True)
    vendor = create_project_vendor(db, project, payload)
    write_audit_log(db, "vendor.created", actor_user_id=membership.user_id, project_id=project_id, metadata={"vendor_id": str(vendor.id)})
    db.commit()
    db.refresh(vendor)
    return serialize_vendor(vendor)


@router.get("/{vendor_id}", response_model=VendorRead)
def get_vendor(project_id: UUID, vendor_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return serialize_vendor(get_project_vendor_or_404(db, project_id, vendor_id))


@router.patch("/{vendor_id}", response_model=VendorRead)
def update_vendor(project_id: UUID, vendor_id: UUID, payload: VendorUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_vendor_manager(membership)
    vendor = get_project_vendor_or_404(db, project_id, vendor_id)
    update_project_vendor(db, vendor, payload)
    write_audit_log(db, "vendor.updated", actor_user_id=membership.user_id, project_id=project_id, metadata={"vendor_id": str(vendor_id)})
    db.commit()
    db.refresh(vendor)
    return serialize_vendor(vendor)


@router.delete("/{vendor_id}")
def delete_vendor(project_id: UUID, vendor_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_vendor_manager(membership)
    vendor = get_project_vendor_or_404(db, project_id, vendor_id)
    db.delete(vendor)
    write_audit_log(db, "vendor.deleted", actor_user_id=membership.user_id, project_id=project_id, metadata={"vendor_id": str(vendor_id)})
    db.commit()
    return {"status": "deleted"}
