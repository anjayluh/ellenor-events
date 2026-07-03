from datetime import datetime, timedelta, timezone
from hashlib import sha256
from hmac import new as hmac_new

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.auth_challenge import AuthChallenge
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.services.audit_service import write_audit_log


def normalize_contact(payload: LoginRequest | str) -> tuple[str, str] | str:
    if isinstance(payload, str):
        contact = payload.strip().lower()
        if contact.startswith("+"):
            return contact.replace(" ", "")
        return contact

    if payload.phone:
        return payload.phone.strip().replace(" ", ""), "phone"
    return str(payload.email).strip().lower(), "email"


def hash_otp(contact: str, code: str) -> str:
    message = f"{contact}:{code}".encode("utf-8")
    key = settings.jwt_secret.encode("utf-8")
    return hmac_new(key, message, sha256).hexdigest()


def enforce_rate_limit(db: Session, contact: str) -> None:
    window_start = datetime.now(timezone.utc) - timedelta(minutes=settings.otp_rate_limit_window_minutes)
    attempts = (
        db.query(AuthChallenge)
        .filter(AuthChallenge.contact == contact, AuthChallenge.requested_at >= window_start)
        .count()
    )
    if attempts >= settings.otp_rate_limit_max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please wait before requesting another code.",
        )


def create_login_challenge(db: Session, payload: LoginRequest, request_ip: str | None) -> AuthChallenge:
    contact, channel = normalize_contact(payload)
    enforce_rate_limit(db, contact)
    code = settings.development_otp_code
    challenge = AuthChallenge(
        contact=contact,
        channel=channel,
        purpose="login",
        code_hash=hash_otp(contact, code),
        status="pending",
        request_ip=request_ip,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes),
    )
    db.add(challenge)
    write_audit_log(db, "auth.challenge_requested", metadata={"channel": channel, "contact": contact})
    return challenge


def get_or_create_user(db: Session, contact: str, channel: str, name: str | None = None) -> User:
    query = db.query(User).filter(User.phone == contact) if channel == "phone" else db.query(User).filter(User.email == contact)
    user = query.first()
    if user:
        if name and not user.name:
            user.name = name
        return user

    user = User(name=name, phone=contact if channel == "phone" else None, email=contact if channel == "email" else None)
    db.add(user)
    db.flush()
    write_audit_log(db, "auth.user_created", actor_user_id=user.id, metadata={"channel": channel})
    return user


def verify_login_challenge(db: Session, contact: str, code: str, name: str | None = None) -> User:
    normalized_contact = normalize_contact(contact)
    now = datetime.now(timezone.utc)
    challenge = (
        db.query(AuthChallenge)
        .filter(AuthChallenge.contact == normalized_contact, AuthChallenge.status == "pending")
        .order_by(AuthChallenge.requested_at.desc())
        .first()
    )
    if not challenge or challenge.expires_at < now:
        if challenge:
            challenge.status = "expired"
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Verification code expired or not found")

    if challenge.code_hash != hash_otp(normalized_contact, code):
        write_audit_log(db, "auth.challenge_failed", metadata={"channel": challenge.channel, "contact": normalized_contact})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid verification code")

    user = get_or_create_user(db, normalized_contact, challenge.channel, name=name)
    challenge.user_id = user.id
    challenge.status = "verified"
    challenge.verified_at = now
    write_audit_log(db, "auth.challenge_verified", actor_user_id=user.id, metadata={"channel": challenge.channel})
    return user
