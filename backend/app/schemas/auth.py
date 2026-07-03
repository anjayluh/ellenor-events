from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    phone: str | None = Field(default=None, examples=["+256700000000"])
    email: EmailStr | None = None


class VerifyOtpRequest(BaseModel):
    contact: str
    code: str = Field(min_length=4, max_length=8)


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
