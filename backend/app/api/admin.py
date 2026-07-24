from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.staff_member import StaffMember
from app.models.user import User
from app.schemas.admin import AdminPermissionGrant, AuditLogRead, StaffMemberRead, UserAdminRead
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


def require_users_view(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> StaffMember:
    return require_admin_permission("admin.users.view", current_user, db)


def require_users_manage(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> StaffMember:
    return require_admin_permission("admin.users.manage", current_user, db)


def require_logs_view(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> StaffMember:
    return require_admin_permission("admin.logs.view", current_user, db)


def require_permissions_manage(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> StaffMember:
    return require_admin_permission("admin.permissions.manage", current_user, db)


@router.get("/me", response_model=StaffMemberRead)
def admin_me(staff_member: StaffMember = Depends(require_users_view), db: Session = Depends(get_db)):
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
