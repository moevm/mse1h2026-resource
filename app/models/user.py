from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=6, max_length=128, description="Password")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., description="Password")


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
