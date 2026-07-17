"""Auth router — user registration, login, and authentication."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..deps import get_current_user, ctx


router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
async def auth_register(req: AuthRequest) -> dict:
    """Register a new user account. Returns a token for immediate login."""
    try:
        user = ctx.user_store.create_user(req.username, req.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {
        "token": user.token,
        "user_id": user.id,
        "username": user.username,
    }


@router.post("/login")
async def auth_login(req: AuthRequest) -> dict:
    """Login with username + password. Returns a fresh token."""
    user = ctx.user_store.verify_user(req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {
        "token": user.token,
        "user_id": user.id,
        "username": user.username,
    }


@router.get("/me")
async def auth_me(user_id: str = Depends(get_current_user)) -> dict:
    """Get current user info from token."""
    user = ctx.user_store.get_user_by_id(user_id)
    if user is not None:
        return {"user_id": user.id, "username": user.username, "created_at": user.created_at}
    # Legacy API key user
    return {"user_id": user_id, "username": "admin"}
