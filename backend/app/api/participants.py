from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_project_membership, membership_role
from app.core.permissions import PROJECT_ADMIN_ROLES, require_role
from app.db.session import get_db
from app.models.participant import Participant
from app.schemas.participant import ParticipantCreate, ParticipantRead, ParticipantUpdate
from app.services.audit_service import write_audit_log

router = APIRouter()


def get_participant_or_404(db: Session, project_id: UUID, participant_id: UUID) -> Participant:
    participant = db.query(Participant).filter(Participant.project_id == project_id, Participant.id == participant_id).first()
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    return participant


@router.get("", response_model=list[ParticipantRead])
def list_participants(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return db.query(Participant).filter(Participant.project_id == project_id).all()


@router.post("", response_model=ParticipantRead)
def create_participant(project_id: UUID, payload: ParticipantCreate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    participant = Participant(project_id=project_id, **payload.model_dump())
    db.add(participant)
    write_audit_log(db, "participant.created", actor_user_id=membership.user_id, project_id=project_id)
    db.commit()
    db.refresh(participant)
    return participant


@router.patch("/{participant_id}", response_model=ParticipantRead)
def update_participant(project_id: UUID, participant_id: UUID, payload: ParticipantUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    participant = get_participant_or_404(db, project_id, participant_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(participant, field, value)
    write_audit_log(db, "participant.updated", actor_user_id=membership.user_id, project_id=project_id, metadata={"participant_id": str(participant_id)})
    db.commit()
    db.refresh(participant)
    return participant


@router.delete("/{participant_id}")
def delete_participant(project_id: UUID, participant_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    participant = get_participant_or_404(db, project_id, participant_id)
    db.delete(participant)
    write_audit_log(db, "participant.deleted", actor_user_id=membership.user_id, project_id=project_id, metadata={"participant_id": str(participant_id)})
    db.commit()
    return {"status": "deleted"}
