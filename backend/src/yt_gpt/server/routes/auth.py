"""Local sign-up, sign-in and session cookie endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from ...auth.base import AuthError, User
from ...auth.session import clear_session_cookie, set_session_cookie
from ...workspace.models import SignInBody, SignUpBody
from ..deps import CurrentUser, OptionalUser, get_auth

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me")
async def me(user: OptionalUser) -> User | None:
    return user


@router.post("/signup")
async def signup(body: SignUpBody, request: Request, response: Response) -> User:
    try:
        user = await get_auth(request).sign_up(body.name, body.email, body.password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    set_session_cookie(response, user["id"])
    return user


@router.post("/login")
async def login(body: SignInBody, request: Request, response: Response) -> User:
    try:
        user = await get_auth(request).sign_in(body.email, body.password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    set_session_cookie(response, user["id"])
    return user


@router.post("/logout", status_code=204)
async def logout(request: Request) -> Response:
    await get_auth(request).sign_out()
    response = Response(status_code=204)
    clear_session_cookie(response)
    return response


@router.get("/profile")
async def profile(user: CurrentUser) -> User:
    return user
