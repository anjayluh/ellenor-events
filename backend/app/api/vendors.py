from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_project_membership, membership_role
from app.core.permissions import ProjectRole, require_role
from app.db.session import get_db
from app.models.vendor import Vendor
from app.schemas.vendor import VendorCreate, VendorRead, VendorUpdate
from app.services.audit_service import write_audit_log

router = APIRouter()
VENDOR_WRITE_ROLES = {ProjectRole.OWNER, ProjectRole.PARTNER, ProjectRole.COMMITTEE_CHAIR, ProjectRole.COMMITTEE_MEMBER}


def get_vendor_or_404(db: Session, project_id: UUID, vendor_id: UUID) -> Vendor:
    vendor = db.query(Vendor).filter(Vendor.project_id == project_id, Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return vendor


@router.get("", response_model=list[VendorRead])
def list_vendors(project_id: UUID, category: str | None = None, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    query = db.query(Vendor).filter(Vendor.project_id == project_id)
    if category:
        query = query.filter(Vendor.category == category)
    return query.order_by(Vendor.category.asc(), Vendor.name.asc()).all()


@router.post("", response_model=VendorRead)
def create_vendor(project_id: UUID, payload: VendorCreate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), VENDOR_WRITE_ROLES)
    vendor = Vendor(project_id=project_id, **payload.model_dump())
    db.add(vendor)
    write_audit_log(db, "vendor.created", actor_user_id=membership.user_id, project_id=project_id)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.patch("/{vendor_id}", response_model=VendorRead)
def update_vendor(project_id: UUID, vendor_id: UUID, payload: VendorUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), VENDOR_WRITE_ROLES)
    vendor = get_vendor_or_404(db, project_id, vendor_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)
    write_audit_log(db, "vendor.updated", actor_user_id=membership.user_id, project_id=project_id, metadata={"vendor_id": str(vendor_id)})
    db.commit()
    db.refresh(vendor)
    return vendor


@router.delete("/{vendor_id}")
def delete_vendor(project_id: UUID, vendor_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), VENDOR_WRITE_ROLES)
    vendor = get_vendor_or_404(db, project_id, vendor_id)
    db.delete(vendor)
    write_audit_log(db, "vendor.deleted", actor_user_id=membership.user_id, project_id=project_id, metadata={"vendor_id": str(vendor_id)})
    db.commit()
    return {"status": "deleted"}
