"""Video library endpoints and ingest kick-off."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from ...ingest.metadata import MetadataError, expand_playlist
from ...ingest.urls import canonical_url, normalize_links
from ...workspace.models import LinksBody
from ...workspace.store import StoreError
from ..deps import CurrentUser, Store, WorkspacePath, get_bus, get_runner

router = APIRouter(prefix="/api/workspaces/{workspace_id}/videos", tags=["videos"])


@router.post("")
async def add_videos(
    body: LinksBody,
    request: Request,
    user: CurrentUser,
    store: Store,
    resolved: WorkspacePath,
) -> dict[str, Any]:
    _, ws_dir = resolved
    parsed = normalize_links(body.links)
    runner = get_runner(request)
    bus = get_bus(request)

    playlist_ids: list[str] = []
    invalid = list(parsed.invalid)
    for url in parsed.playlist_urls:
        try:
            playlist_ids.extend(await asyncio.to_thread(expand_playlist, url))
        except MetadataError as exc:
            invalid.append(f"{url} ({exc})")

    order: list[str] = []
    seen: set[str] = set()
    for video_id in [*parsed.video_ids, *playlist_ids]:
        if video_id not in seen:
            seen.add(video_id)
            order.append(video_id)

    added: list[dict[str, Any]] = []
    skipped: list[str] = []
    for video_id in order:
        try:
            video = store.add_video(ws_dir, video_id, canonical_url(video_id))
        except StoreError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        if video is None:
            skipped.append(video_id)
            continue
        added.append(video)
        await runner.submit(user["id"], ws_dir, video_id)

    if added:
        store.touch_workspace(ws_dir)
        bus.publish(str((store.get_workspace(ws_dir.name)).get("id")), "update")
    return {"added": added, "skipped": skipped, "invalid": invalid}


@router.get("/{video_id}")
async def get_video(video_id: str, resolved: WorkspacePath) -> dict[str, Any]:
    store, ws_dir = resolved
    try:
        return store.get_video(ws_dir, video_id)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.delete("/{video_id}", status_code=204)
async def remove_video(video_id: str, resolved: WorkspacePath) -> Response:
    store, ws_dir = resolved
    try:
        store.remove_video(ws_dir, video_id)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return Response(status_code=204)


@router.post("/{video_id}/retry", status_code=204)
async def retry_video(
    video_id: str,
    request: Request,
    user: CurrentUser,
    resolved: WorkspacePath,
) -> Response:
    store, ws_dir = resolved
    try:
        store.retry_video(ws_dir, video_id)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    await get_runner(request).submit(user["id"], ws_dir, video_id)
    get_bus(request).publish(str(store.get_workspace(ws_dir.name).get("id")), "update")
    return Response(status_code=204)
