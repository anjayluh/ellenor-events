from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_project_membership, membership_role
from app.core.permissions import PROJECT_ADMIN_ROLES, require_role
from app.db.session import get_db
from app.models.testimonial import Testimonial
from app.schemas.testimonial import TestimonialCreate, TestimonialRead, TestimonialUpdate
from app.services.audit_service import write_audit_log

router = APIRouter()


def get_testimonial_or_404(db: Session, project_id: UUID, testimonial_id: UUID) -> Testimonial:
    testimonial = db.query(Testimonial).filter(Testimonial.project_id == project_id, Testimonial.id == testimonial_id).first()
    if not testimonial:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Testimonial not found")
    return testimonial


@router.get("", response_model=list[TestimonialRead])
def list_testimonials(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return db.query(Testimonial).filter(Testimonial.project_id == project_id).all()


@router.post("", response_model=TestimonialRead)
def create_testimonial(project_id: UUID, payload: TestimonialCreate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    testimonial = Testimonial(project_id=project_id, type=payload.type, url=str(payload.url), caption=payload.caption)
    db.add(testimonial)
    write_audit_log(db, "testimonial.created", actor_user_id=membership.user_id, project_id=project_id)
    db.commit()
    db.refresh(testimonial)
    return testimonial


@router.patch("/{testimonial_id}", response_model=TestimonialRead)
def update_testimonial(project_id: UUID, testimonial_id: UUID, payload: TestimonialUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    testimonial = get_testimonial_or_404(db, project_id, testimonial_id)
    updates = payload.model_dump(exclude_unset=True)
    if "url" in updates and updates["url"] is not None:
        updates["url"] = str(updates["url"])
    for field, value in updates.items():
        setattr(testimonial, field, value)
    write_audit_log(db, "testimonial.updated", actor_user_id=membership.user_id, project_id=project_id, metadata={"testimonial_id": str(testimonial_id)})
    db.commit()
    db.refresh(testimonial)
    return testimonial


@router.delete("/{testimonial_id}")
def delete_testimonial(project_id: UUID, testimonial_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    testimonial = get_testimonial_or_404(db, project_id, testimonial_id)
    db.delete(testimonial)
    write_audit_log(db, "testimonial.deleted", actor_user_id=membership.user_id, project_id=project_id, metadata={"testimonial_id": str(testimonial_id)})
    db.commit()
    return {"status": "deleted"}
