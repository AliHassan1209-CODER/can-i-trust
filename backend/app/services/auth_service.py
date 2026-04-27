from datetime import timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    get_user_id_from_token
)
from app.core.config import settings


class AuthService:

    # ─────────────────────────────────────────
    # Register
    # ─────────────────────────────────────────

    @staticmethod
    async def register(data: UserRegister, db: AsyncSession) -> User:
        # Check if email already exists
        result = await db.execute(select(User).where(User.email == data.email))
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        # Create new user
        new_user = User(
            full_name=data.full_name,
            email=data.email,
            hashed_password=hash_password(data.password),
        )
        db.add(new_user)
        await db.flush()          # Get the ID without committing
        await db.refresh(new_user)
        return new_user

    # ─────────────────────────────────────────
    # Login
    # ─────────────────────────────────────────

    @staticmethod
    async def login(data: UserLogin, db: AsyncSession) -> TokenResponse:
        # Find user by email
        result = await db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        # Issue tokens
        token_data = {"sub": str(user.id), "email": user.email}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ─────────────────────────────────────────
    # Refresh Access Token
    # ─────────────────────────────────────────

    @staticmethod
    async def refresh_token(refresh_token: str, db: AsyncSession) -> TokenResponse:
        from app.core.security import decode_token
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user_id = int(payload.get("sub"))
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        token_data = {"sub": str(user.id), "email": user.email}
        new_access = create_access_token(token_data)
        new_refresh = create_refresh_token(token_data)

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ─────────────────────────────────────────
    # Get Current User (from token)
    # ─────────────────────────────────────────

    @staticmethod
    async def get_current_user(token: str, db: AsyncSession) -> User:
        user_id = get_user_id_from_token(token)
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user
