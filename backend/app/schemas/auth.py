from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class LoginRequest(BaseModel):
    phone: str | None = Field(default=None, examples=["+256700000000"])
    email: EmailStr | None = None

    @model_validator(mode="after")
    def validate_contact(self):
        if not self.phone and not self.email:
            raise ValueError("Phone or email is required")
        if self.phone and self.email:
            raise ValueError("Use either phone or email, not both")
        return self


class LoginChallenge(BaseModel):
    status: str
    channel: str
    contact: str
    expires_at: datetime
    delivery_mode: str
    development_code: str | None = None
    development_magic_link: str | None = None


class VerifyOtpRequest(BaseModel):
    contact: str
    code: str = Field(min_length=4, max_length=8)
    name: str | None = None


class AuthUser(BaseModel):
    id: UUID
    name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser
