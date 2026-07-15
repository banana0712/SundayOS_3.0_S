"""Shared dependency context for the FastAPI app.

ENGINEERING_CONTRACT §1/§2: routes live in `routers/<domain>.py` and must reach
shared singletons (stores, runtime, engines, auth) through THIS module — never
by importing main.py (which would be a circular import and a second source of
truth).

main.py builds the singletons at startup and calls `set_context(...)` once.
Routers then depend on `get_current_user` / `require_admin` (FastAPI Depends)
or read `ctx.<name>` directly.

This is the foundation step of the main.py split: it does NOT change behavior,
it only relocates where the auth helpers and shared handles live so routes can
be extracted domain by domain.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from fastapi import Header, HTTPException


@dataclass
class _Context:
    """Holds the live singletons. Populated once by main.py at startup."""
    user_store: Any = None
    memory: Any = None
    conversations: Any = None
    pref_store: Any = None
    runtime: Any = None
    engines: Any = None
    api_key: str = ""
    owner_username: str = ""
    version: str = "0.0.0-dev"


# Module-level singleton context. Import `ctx` and read ctx.<name>.
ctx = _Context()


def set_context(**kwargs: Any) -> None:
    """Called once by main.py after all subsystems are built."""
    for k, v in kwargs.items():
        if not hasattr(ctx, k):
            raise KeyError(f"deps.set_context: unknown field {k!r}")
        setattr(ctx, k, v)


# ── Auth (single source of truth; main.py delegates to these) ────────────────

def auth(x_api_key: str | None = None,
         x_sunday_token: str | None = None) -> str:
    """Authenticate. Returns user_id on success, raises 401 on failure.

    Dual auth: user token first (logged-in users), then API key (admin /
    Shortcuts / scripts). An old-format API key passed as a token is accepted
    as a migration path. Behavior identical to main.py's original _auth.
    """
    # Path 1: user token (webchat/console login)
    if x_sunday_token:
        user = ctx.user_store.get_user_by_token(x_sunday_token)
        if user is not None:
            return user.id
        if x_sunday_token == ctx.api_key:
            return "user_" + hashlib.sha256(x_sunday_token.encode("utf-8")).hexdigest()[:16]
        raise HTTPException(status_code=401, detail="Token 已过期，请重新登录")

    # Path 2: legacy API key (admin / Shortcuts / curl)
    if x_api_key:
        if x_api_key == ctx.api_key:
            return "user_" + hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()[:16]
        raise HTTPException(status_code=401, detail="invalid or missing API Key")

    raise HTTPException(status_code=401, detail="请先登录或提供 API Key")


def require_admin(x_api_key: str | None = None,
                  x_sunday_token: str | None = None) -> str:
    """Admin gate. Static API key is the owner backdoor; otherwise the caller's
    role must be 'owner' (role support lands with the invite system — until then
    only the API key path grants admin, matching current behavior)."""
    user_id = auth(x_api_key, x_sunday_token)
    if x_api_key == ctx.api_key or x_sunday_token == ctx.api_key:
        return user_id
    # Role-based path (no-op until users.role exists; see INVITE_SYSTEM_PLAN.md)
    get_role = getattr(ctx.user_store, "get_role", None)
    if get_role and get_role(user_id) == "owner":
        return user_id
    raise HTTPException(status_code=403, detail="需要管理员权限")


# ── FastAPI dependency wrappers (use with Depends in routers) ─────────────────

def get_current_user(
    x_api_key: str | None = Header(default=None),
    x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token"),
) -> str:
    return auth(x_api_key, x_sunday_token)


def get_admin(
    x_api_key: str | None = Header(default=None),
    x_sunday_token: str | None = Header(default=None, alias="X-Sunday-Token"),
) -> str:
    return require_admin(x_api_key, x_sunday_token)
