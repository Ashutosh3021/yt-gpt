"""FastAPI dependencies: auth, workspace resolution and app services."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request

from ..auth.base import AuthProvider, User
from ..auth.session import COOKIE_NAME, decode_session
from ..events import EventBus
from ..ingest.jobs import IngestRunner
from ..workspace.store import NotFound, StoreError, WorkspaceStore


def get_app(request: Request) -> Any:
    return request.app


def get_auth(request: Request) -> AuthProvider:
    return request.app.state.auth


def get_bus(request: Request) -> EventBus:
    return request.app.state.bus


def get_runner(request: Request) -> IngestRunner:
    return request.app.state.runner


def _user_id(request: Request) -> str | None:
    data = decode_session(request.cookies.get(COOKIE_NAME))
    return str(data["uid"]) if data else None


async def optional_user(request: Request) -> User | None:
    user_id = _user_id(request)
    if not user_id:
        return None
    return await get_auth(request).current_user(user_id)


async def require_user(request: Request) -> User:
    user = await optional_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in first.")
    return user


def get_store(user: Annotated[User, Depends(require_user)]) -> WorkspaceStore:
    return WorkspaceStore(user["id"])


def resolve_workspace(
    workspace_id: str,
    store: Annotated[WorkspaceStore, Depends(get_store)],
) -> tuple[WorkspaceStore, Path]:
    try:
        return store, store.resolve(workspace_id)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


CurrentUser = Annotated[User, Depends(require_user)]
OptionalUser = Annotated[User | None, Depends(optional_user)]
Store = Annotated[WorkspaceStore, Depends(get_store)]
WorkspacePath = Annotated[tuple[WorkspaceStore, Path], Depends(resolve_workspace)]


def workspace_response(store: WorkspaceStore, ws_dir: Path) -> dict[str, Any]:
    try:
        return store.get_workspace(ws_dir.name)
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
