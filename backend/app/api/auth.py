from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.core.security import (
    encrypt_token,
    hash_password,
    new_caldav_password,
    new_caldav_username,
)
from app.db.models import User
from app.db.session import get_db
from app.google.client import authorization_url, exchange_code, fetch_userinfo

router = APIRouter(tags=["auth"])


class MeResponse(BaseModel):
    email: str
    caldav_url: str
    caldav_username: str
    caldav_password: str | None = None
    connected: bool = True


@router.get("/auth/google")
async def google_start(request: Request) -> RedirectResponse:
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    return RedirectResponse(authorization_url(state))


@router.get("/auth/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not code or state != request.session.get("oauth_state"):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    tokens = await exchange_code(code)
    access = tokens["access_token"]
    refresh = tokens.get("refresh_token")
    info = await fetch_userinfo(access)
    sub = info["sub"]
    email = info.get("email") or f"{sub}@users.noreply.google.com"

    result = await db.execute(select(User).where(User.google_sub == sub))
    user = result.scalar_one_or_none()
    plain_password: str | None = None

    if user is None:
        plain_password = new_caldav_password()
        if not refresh:
            raise HTTPException(
                status_code=400,
                detail="Google did not return a refresh token; revoke app access and retry",
            )
        user = User(
            google_sub=sub,
            email=email,
            caldav_username=new_caldav_username(email),
            caldav_password_hash=hash_password(plain_password),
            refresh_token_enc=encrypt_token(refresh),
        )
        db.add(user)
    else:
        user.email = email
        if refresh:
            user.refresh_token_enc = encrypt_token(refresh)

    await db.commit()
    await db.refresh(user)

    request.session["user_id"] = user.id
    if plain_password:
        request.session["caldav_password_once"] = plain_password
    return RedirectResponse("/")


@router.get("/api/me", response_model=MeResponse)
async def me(request: Request, db: AsyncSession = Depends(get_db)) -> MeResponse:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not connected")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Not connected")

    settings = get_settings()
    caldav_url = f"{settings.base_url.rstrip('/')}/caldav/{user.caldav_username}/"
    once = request.session.pop("caldav_password_once", None)
    return MeResponse(
        email=user.email,
        caldav_url=caldav_url,
        caldav_username=user.caldav_username,
        caldav_password=once,
        connected=True,
    )


@router.post("/api/me/rotate-password", response_model=MeResponse)
async def rotate_password(request: Request, db: AsyncSession = Depends(get_db)) -> MeResponse:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not connected")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Not connected")

    plain = new_caldav_password()
    user.caldav_password_hash = hash_password(plain)
    await db.commit()
    settings = get_settings()
    return MeResponse(
        email=user.email,
        caldav_url=f"{settings.base_url.rstrip('/')}/caldav/{user.caldav_username}/",
        caldav_username=user.caldav_username,
        caldav_password=plain,
        connected=True,
    )


@router.post("/api/logout")
async def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=204)


def attach_session(app, secret_key: str) -> None:
    settings = get_settings()
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret_key,
        same_site="lax",
        https_only=settings.session_https_only,
    )
