"""Workspace source documents with version history."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from ...workspace.models import SourceCreateBody, SourceUpdateBody
from ...workspace.store import StoreError
from ..deps import Store, WorkspacePath, get_bus

router = APIRouter(prefix="/api/workspaces/{workspace_id}/sources", tags=["sources"])


def _publish(request: Request, store: Store, ws_dir: Any) -> None:
    try:
        data = store._read_workspace_json(ws_dir)
        get_bus(request).publish(str(data.get("id") or ws_dir.name), "update")
    except Exception:
        return


@router.get("")
async def list_sources(resolved: WorkspacePath) -> list[dict[str, Any]]:
    store, ws_dir = resolved
    return store.list_sources(ws_dir)


@router.post("", status_code=201)
async def create_source(
    body: SourceCreateBody,
    request: Request,
    resolved: WorkspacePath,
) -> dict[str, Any]:
    store, ws_dir = resolved
    try:
        source = store.create_source(ws_dir, body.name, body.content)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _publish(request, store, ws_dir)
    return source


@router.get("/{name}")
async def get_source(name: str, resolved: WorkspacePath) -> dict[str, Any]:
    store, ws_dir = resolved
    try:
        return store.get_source(ws_dir, name)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.put("/{name}")
async def update_source(
    name: str,
    body: SourceUpdateBody,
    request: Request,
    resolved: WorkspacePath,
) -> dict[str, Any]:
    store, ws_dir = resolved
    try:
        source = store.update_source(ws_dir, name, body.content, body.note)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _publish(request, store, ws_dir)
    return source


@router.delete("/{name}", status_code=204)
async def delete_source(name: str, request: Request, resolved: WorkspacePath) -> Response:
    store, ws_dir = resolved
    try:
        store.delete_source(ws_dir, name)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _publish(request, store, ws_dir)
    return Response(status_code=204)


@router.get("/{name}/versions")
async def list_versions(name: str, resolved: WorkspacePath) -> list[dict[str, Any]]:
    store, ws_dir = resolved
    try:
        return store.get_source(ws_dir, name)["versions"]
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{name}/versions/{version_id}")
async def restore_version(
    name: str,
    version_id: str,
    request: Request,
    resolved: WorkspacePath,
) -> dict[str, Any]:
    store, ws_dir = resolved
    try:
        source = store.restore_version(ws_dir, name, version_id)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _publish(request, store, ws_dir)
    return source
