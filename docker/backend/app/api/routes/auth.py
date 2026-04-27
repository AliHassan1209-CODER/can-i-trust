from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, get_current_user
)
from app.services.user_service import UserService
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, RefreshRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    user = await UserService.create(db, data)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login and receive JWT tokens."""
    user = await UserService.authenticate(db, data.email, data.password)
    access_token  = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a refresh token for a new access token."""
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Invalid refresh token")
    user = await UserService.get_by_id(db, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    access_token  = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user=Depends(get_current_user)):
    """Get currently authenticated user's profile."""
    return current_user


@router.post("/logout")
async def logout():
    """Logout — client should discard tokens. Add Redis blacklist here for full revocation."""
    return {"message": "Logged out successfully"}
