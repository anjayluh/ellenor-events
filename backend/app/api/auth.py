from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from app.core.security import create_access_token
from app.schemas.auth import AuthToken, LoginRequest, VerifyOtpRequest

router = APIRouter()


@router.post("/login")
def request_login(payload: LoginRequest) -> dict[str, str]:
    if not payload.phone and not payload.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone or email is required")
    return {"status": "otp_sent", "channel": "phone" if payload.phone else "email"}


@router.post("/verify-otp", response_model=AuthToken)
def verify_otp(payload: VerifyOtpRequest) -> AuthToken:
    # Development placeholder. Production should verify Supabase/Firebase OTP and map/create global user.
    if payload.code != "000000":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid verification code")
    return AuthToken(access_token=create_access_token(uuid4()))
