from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.auth import AuthToken, AuthUser, LoginChallenge, LoginRequest, VerifyOtpRequest
from app.services.auth_service import create_login_challenge, verify_login_challenge

router = APIRouter()


@router.post("/login", response_model=LoginChallenge)
def request_login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> LoginChallenge:
    challenge = create_login_challenge(db, payload, request.client.host if request.client else None)
    db.commit()

    delivery_mode = "sms_otp" if challenge.channel == "phone" else "email_magic_link"
    development_code = settings.development_otp_code if settings.environment == "development" else None
    development_magic_link = (
        f"{settings.frontend_url}/auth/verify?contact={challenge.contact}&code={settings.development_otp_code}"
        if settings.environment == "development" and challenge.channel == "email"
        else None
    )
    return LoginChallenge(
        status="otp_sent" if challenge.channel == "phone" else "magic_link_sent",
        channel=challenge.channel,
        contact=challenge.contact,
        expires_at=challenge.expires_at,
        delivery_mode=delivery_mode,
        development_code=development_code,
        development_magic_link=development_magic_link,
    )


@router.post("/verify-otp", response_model=AuthToken)
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)) -> AuthToken:
    user = verify_login_challenge(db, payload.contact, payload.code, name=payload.name)
    token = create_access_token(user.id, extra_claims={"auth_provider": settings.auth_provider})
    db.commit()
    return AuthToken(
        access_token=token,
        user=AuthUser(id=user.id, name=user.name, phone=user.phone, email=user.email),
    )
