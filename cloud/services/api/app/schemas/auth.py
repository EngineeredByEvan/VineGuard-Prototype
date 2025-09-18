from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    org_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class UserResponse(BaseModel):
    id: UUID
    org_id: UUID
    email: EmailStr
    role: str
    created_at: datetime
