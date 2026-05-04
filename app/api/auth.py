from __future__ import annotations

from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.repositories import session_repo, user_repo

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> Dict[str, Any]:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token")

    if await session_repo.is_token_blacklisted(payload["jti"]):
        raise HTTPException(status_code=401, detail="Token revoked")

    user = user_repo.get_by_id(payload["sub"])
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "username": user["username"],
        "jti": payload["jti"],
    }


CurrentUser = Annotated[Dict[str, Any], Depends(get_current_user)]


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    existing = user_repo.get_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    password_hash = hash_password(body.password)
    user = user_repo.create_user(body.email, body.username, password_hash)
    return UserResponse(**user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    user = user_repo.get_by_email(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is deactivated")

    access_token = create_access_token(user["user_id"])
    refresh_token = create_refresh_token(user["user_id"])

    refresh_payload = decode_token(refresh_token)
    await session_repo.store_refresh_token(user["user_id"], refresh_payload["jti"])

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshTokenRequest):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload["sub"]
    jti = payload["jti"]

    if not await session_repo.validate_refresh_token(user_id, jti):
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    user = user_repo.get_by_id(user_id)
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    await session_repo.revoke_refresh_token(user_id, jti)

    access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)

    new_payload = decode_token(new_refresh_token)
    await session_repo.store_refresh_token(user_id, new_payload["jti"])

    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshTokenRequest,
    token: str = Depends(oauth2_scheme),
):
    if token:
        access_payload = decode_token(token)
        if access_payload and access_payload.get("type") == "access":
            ttl = settings.access_token_expire_minutes * 60
            await session_repo.blacklist_access_token(access_payload["jti"], ttl)

    refresh_payload = decode_token(body.refresh_token)
    if refresh_payload and refresh_payload.get("type") == "refresh":
        await session_repo.revoke_refresh_token(
            refresh_payload["sub"], refresh_payload["jti"]
        )
