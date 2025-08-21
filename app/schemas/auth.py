"""Authentication schemas."""

from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    organization_slug: Optional[str] = None


class RefreshRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class UserResponse(BaseModel):
    """User response schema."""
    id: UUID
    email: EmailStr
    username: str
    full_name: Optional[str]
    role: str
    organization_id: UUID
    is_active: bool
    is_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LoginResponse(TokenResponse):
    """Login response schema with user info."""
    user: UserResponse