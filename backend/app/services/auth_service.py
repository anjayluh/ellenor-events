from hashlib import sha256
from hmac import new as hmac_new
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.audit_service import write_audit_log


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password_marker(email: str, password: str) -> str:
    message = f"{email}:{password}".encode("utf-8")
    key = settings.jwt_signing_secret.encode("utf-8")
    return hmac_new(key, message, sha256).hexdigest()


def get_or_create_local_user(db: Session, email: str, name: str | None = None) -> User:
    normalized_email = normalize_email(email)
    user = db.query(User).filter(User.email == normalized_email).first()
    if user:
        if name and not user.name:
            user.name = name
        return user

    user = User(name=name, email=normalized_email)
    db.add(user)
    db.flush()
    write_audit_log(db, "auth.user_created", actor_user_id=user.id, metadata={"channel": "email"})
    return user


def supabase_auth_headers(use_service_role: bool = False) -> dict[str, str]:
    key = settings.supabase_service_role_key if use_service_role and settings.supabase_service_role_key else settings.supabase_anon_key
    if not key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Supabase key is not configured")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def supabase_auth_url(path: str) -> str:
    if not settings.supabase_url:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Supabase URL is not configured")
    return f"{settings.supabase_url.rstrip('/')}/auth/v1/{path.lstrip('/')}"


def upsert_public_user_from_supabase_auth(db: Session, auth_user: dict, name: str | None = None) -> User:
    user_id = UUID(auth_user["id"])
    metadata = auth_user.get("user_metadata") or {}
    user_name = name or metadata.get("name") or metadata.get("full_name")
    phone = auth_user.get("phone")
    email = normalize_email(auth_user["email"]) if auth_user.get("email") else None

    user = db.query(User).filter(User.id == user_id).first()
    if user:
        if user_name and not user.name:
            user.name = user_name
        if phone and not user.phone:
            user.phone = phone
        if email and not user.email:
            user.email = email
        return user

    user = User(id=user_id, name=user_name, phone=phone, email=email)
    db.add(user)
    db.flush()
    write_audit_log(db, "auth.supabase_user_synced", actor_user_id=user.id)
    return user


def register_with_supabase_password(db: Session, payload: RegisterRequest) -> tuple[str, User]:
    request_payload = {
        "email": normalize_email(str(payload.email)),
        "password": payload.password,
        "data": {"name": payload.name} if payload.name else {},
    }
    try:
        response = httpx.post(supabase_auth_url("signup"), headers=supabase_auth_headers(), json=request_payload, timeout=10)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail="Supabase Auth rejected account creation") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Supabase Auth is unavailable") from exc

    data = response.json()
    auth_user = data.get("user") or (data if data.get("id") else None)
    access_token = data.get("access_token") or (data.get("session") or {}).get("access_token")
    if not auth_user:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Supabase Auth response was incomplete")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail="Account created. Confirm the email address before signing in.")

    user = upsert_public_user_from_supabase_auth(db, auth_user, name=payload.name)
    write_audit_log(db, "auth.supabase_password_registered", actor_user_id=user.id)
    return access_token, user


def login_with_supabase_password(db: Session, payload: LoginRequest) -> tuple[str, User]:
    request_payload = {"email": normalize_email(str(payload.email)), "password": payload.password}
    try:
        response = httpx.post(
            supabase_auth_url("token?grant_type=password"),
            headers=supabase_auth_headers(),
            json=request_payload,
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        try:
            error_detail = exc.response.json()
        except ValueError:
            error_detail = {}
        error_message = str(error_detail.get("msg") or error_detail.get("message") or "")
        if "not confirmed" in error_message.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email address is not confirmed") from exc
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Supabase Auth is unavailable") from exc

    data = response.json()
    auth_user = data.get("user")
    access_token = data.get("access_token")
    if not auth_user or not access_token:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Supabase Auth response was incomplete")

    user = upsert_public_user_from_supabase_auth(db, auth_user)
    write_audit_log(db, "auth.supabase_password_login", actor_user_id=user.id)
    return access_token, user
