"""
Pydantic schemas for user-related API operations.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# --- Request Schemas ---

class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: str | None = None


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile."""

    full_name: str | None = None
    # TODO: Add password change (requires current_password verification)


# --- Response Schemas ---

class UserResponse(BaseModel):
    """Schema for user data in API responses."""

    id: int
    email: str
    full_name: str | None
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload data."""

    sub: int  # user_id
    exp: datetime
