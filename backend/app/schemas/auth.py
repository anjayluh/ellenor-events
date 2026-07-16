from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterRequest(LoginRequest):
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


class AuthMessage(BaseModel):
    status: str
    message: str
