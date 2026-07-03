from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.core.permissions import PROJECT_ADMIN_ROLES, ProjectRole, require_role
from app.db.session import get_db
from app.models.invite import Invite
from app.models.project_member import ProjectMember
from app.schemas.invite import InviteAccept, InviteCreate, InviteRead
from app.services.audit_service import write_audit_log
from app.services.invite_service import build_invite_link
from app.services.whatsapp_service import build_whatsapp_invite_url

router = APIRouter()


def require_invite_permission(payload: InviteCreate, current_user: CurrentUser, db: Session) -> None:
    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == payload.project_id, ProjectMember.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this project")
    require_role(ProjectRole(membership.role), PROJECT_ADMIN_ROLES)


@router.post("", response_model=InviteRead)
def create_invite(payload: InviteCreate, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_invite_permission(payload, current_user, db)
    token = token_urlsafe(32)
    invite = Invite(
        project_id=payload.project_id,
        contact=payload.contact,
        role_assigned=payload.role_assigned,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invite)
    write_audit_log(db, "invite.created", actor_user_id=current_user.id, project_id=payload.project_id, metadata={"contact": payload.contact, "role": str(payload.role_assigned)})
    db.commit()
    db.refresh(invite)
    invite_link = build_invite_link(token)
    build_whatsapp_invite_url(payload.contact, invite_link)
    return InviteRead(**invite.__dict__, invite_link=invite_link)


@router.post("/accept")
def accept_invite(payload: InviteAccept, db: Session = Depends(get_db)):
    write_audit_log(db, "invite.accept_attempted", metadata={"token_prefix": payload.token[:8]})
    db.commit()
    return {"status": "accepted", "token": payload.token}
