"""Workspace CRUD."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse

from ...workspace.models import WorkspaceCreateBody, WorkspacePatchBody
from ...workspace.store import StoreError
from ..deps import Store, WorkspacePath, get_bus
from ..sse import sse_response, workspace_events

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.get("")
async def list_workspaces(store: Store) -> list[dict[str, Any]]:
    return store.list_workspaces()


@router.post("", status_code=201)
async def create_workspace(body: WorkspaceCreateBody, store: Store) -> dict[str, Any]:
    try:
        return store.create_workspace(body.name)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/{workspace_id}")
async def get_workspace(resolved: WorkspacePath) -> dict[str, Any]:
    store, ws_dir = resolved
    try:
        return store.get_workspace(ws_dir.name)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.patch("/{workspace_id}")
async def update_workspace(body: WorkspacePatchBody, resolved: WorkspacePath) -> dict[str, Any]:
    store, ws_dir = resolved
    try:
        data = store._read_workspace_json(ws_dir)
        ws_id = str(data.get("id") or ws_dir.name)
        if body.name is not None:
            data = store.rename_workspace(ws_id, body.name)
            ws_dir = store.resolve(str(data.get("id") or ws_id))
        if body.settings is not None:
            data = store.update_workspace_settings(ws_id, body.settings.model_dump(exclude_none=True))
        return data
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(resolved: WorkspacePath) -> Response:
    store, ws_dir = resolved
    try:
        data = store._read_workspace_json(ws_dir)
        store.delete_workspace(str(data.get("id") or ws_dir.name))
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return Response(status_code=204)


@router.get("/{workspace_id}/export", response_class=PlainTextResponse)
async def export_workspace(resolved: WorkspacePath) -> PlainTextResponse:
    store, ws_dir = resolved
    try:
        content = store.write_transcripts(ws_dir)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return PlainTextResponse(
        content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="transcripts.md"'},
    )


@router.get("/{workspace_id}/events")
async def workspace_events_route(request: Request, resolved: WorkspacePath):
    store, ws_dir = resolved
    try:
        data = store._read_workspace_json(ws_dir)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    channel = str(data.get("id") or ws_dir.name)
    return sse_response(workspace_events(get_bus(request), channel))
