from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., max_length=254, description="User email")
    username: str = Field(..., min_length=3, max_length=32, description="Username")
    password: str = Field(..., min_length=5, max_length=72, description="Password")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., max_length=254, description="User email")
    password: str = Field(..., min_length=1, max_length=72, description="Password")


class UserResponse(BaseModel):
    user_id: str
    email: str
    username: str
    is_active: bool = True
    created_at: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str
