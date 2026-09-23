from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.auth import AuthMessage, AuthToken, AuthUser, LoginRequest, PasswordResetConfirm, PasswordResetRequest, RegisterRequest
from app.services.auth_service import confirm_supabase_password_reset, get_or_create_local_user, login_with_supabase_password, register_with_supabase_password, request_supabase_password_reset

router = APIRouter()


def serialize_auth_token(token: str, user) -> AuthToken:
    return AuthToken(
        access_token=token,
        user=AuthUser(id=user.id, name=user.name, phone=user.phone, email=user.email),
    )


@router.post("/register", response_model=AuthToken, responses={202: {"model": AuthMessage}})
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthToken:
    if settings.auth_provider == "supabase":
        token, user = register_with_supabase_password(db, payload)
        db.commit()
        return serialize_auth_token(token, user)

    user = get_or_create_local_user(db, str(payload.email), name=payload.name)
    token = create_access_token(user.id, extra_claims={"auth_provider": "local_dev"})
    db.commit()
    return serialize_auth_token(token, user)


@router.post("/login", response_model=AuthToken)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthToken:
    if settings.auth_provider == "supabase":
        token, user = login_with_supabase_password(db, payload)
        db.commit()
        return serialize_auth_token(token, user)

    user = get_or_create_local_user(db, str(payload.email))
    token = create_access_token(user.id, extra_claims={"auth_provider": "local_dev"})
    db.commit()
    return serialize_auth_token(token, user)


@router.post("/password-reset/request", response_model=AuthMessage)
def request_password_reset(payload: PasswordResetRequest) -> AuthMessage:
    if settings.uses_remote_supabase_auth:
        request_supabase_password_reset(payload)
    return AuthMessage(
        status="ok",
        message="If an account exists for that email, a password reset link has been sent.",
    )


@router.post("/password-reset/confirm", response_model=AuthMessage)
def confirm_password_reset(payload: PasswordResetConfirm) -> AuthMessage:
    if settings.uses_remote_supabase_auth:
        confirm_supabase_password_reset(payload)
    return AuthMessage(status="ok", message="Password updated. You can now sign in with the new password.")
