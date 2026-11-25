"""Session CRUD and the streaming chat endpoint."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import replace
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from ...llm.chat import maybe_summarize, run_chat
from ...llm.provider import LlmConfig, LlmError
from ...util import iso_now, truncate
from ...workspace.models import ChatBody, SessionCreateBody, SessionPatchBody
from ...workspace.store import StoreError
from ..deps import CurrentUser, Store, WorkspacePath, get_bus
from ..sse import sse, sse_response

router = APIRouter(prefix="/api/workspaces/{workspace_id}/sessions", tags=["sessions"])


def _publish(request: Request, store: Store, ws_dir: Any) -> None:
    try:
        data = store._read_workspace_json(ws_dir)
        get_bus(request).publish(str(data.get("id") or ws_dir.name), "update")
    except Exception:
        return


@router.get("")
async def list_sessions(resolved: WorkspacePath) -> list[dict[str, Any]]:
    store, ws_dir = resolved
    return store.list_sessions(ws_dir)


@router.post("", status_code=201)
async def create_session(
    body: SessionCreateBody,
    request: Request,
    resolved: WorkspacePath,
) -> dict[str, Any]:
    store, ws_dir = resolved
    try:
        session = store.create_session(ws_dir, body.title)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _publish(request, store, ws_dir)
    return session


@router.get("/{session_id}")
async def get_session(session_id: str, resolved: WorkspacePath) -> dict[str, Any]:
    store, ws_dir = resolved
    try:
        return store.get_session(ws_dir, session_id)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.patch("/{session_id}")
async def update_session(
    session_id: str,
    body: SessionPatchBody,
    request: Request,
    resolved: WorkspacePath,
) -> dict[str, Any]:
    store, ws_dir = resolved
    settings = body.settings.model_dump(exclude_none=True) if body.settings else None
    try:
        session = store.update_session(ws_dir, session_id, title=body.title, settings=settings)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _publish(request, store, ws_dir)
    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: str, request: Request, resolved: WorkspacePath) -> Response:
    store, ws_dir = resolved
    try:
        store.delete_session(ws_dir, session_id)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    _publish(request, store, ws_dir)
    return Response(status_code=204)


@router.post("/{session_id}/messages")
async def send_message(
    session_id: str,
    body: ChatBody,
    request: Request,
    user: CurrentUser,
    resolved: WorkspacePath,
) -> StreamingResponse:
    store, ws_dir = resolved
    question = body.content.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Write a question first.")
    try:
        raw = store.load_session(ws_dir, session_id)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    if not raw.get("messages"):
        title = truncate(question, 42, "…")
        try:
            store.update_session(ws_dir, session_id, title=title)
        except StoreError:
            pass

    store.append_message(
        ws_dir,
        session_id,
        {"id": f"m_{uuid.uuid4().hex[:12]}", "role": "user", "content": question, "ts": iso_now()},
    )
    workspace = store.get_workspace(ws_dir.name)
    session = store.get_session(ws_dir, session_id)

    config = LlmConfig.for_user(user["id"])
    override = (session.get("settings") or {}).get("modelOverride")
    if isinstance(override, str) and override.strip():
        config = replace(config, model=override.strip())

    async def events() -> AsyncIterator[str]:
        try:
            async for event in run_chat(
                store=store,
                ws_dir=ws_dir,
                workspace=workspace,
                session=session,
                query=question,
                config=config,
            ):
                if event["type"] == "token":
                    yield sse({"token": event["text"]})
                elif event["type"] == "final":
                    message = {
                        "id": f"m_{uuid.uuid4().hex[:12]}",
                        "role": "assistant",
                        "content": event["content"],
                        "citations": event["citations"],
                        "ts": iso_now(),
                    }
                    store.append_message(ws_dir, session_id, message)
                    _publish(request, store, ws_dir)
                    yield sse({"message": message})
                    asyncio.create_task(
                        maybe_summarize(
                            store=store,
                            ws_dir=ws_dir,
                            session_id=session_id,
                            config=config,
                        )
                    )
        except LlmError as exc:
            payload: dict[str, Any] = {"error": str(exc)}
            if exc.retry_after is not None:
                payload["retryAfter"] = exc.retry_after
            yield sse(payload)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            yield sse({"error": f"The answer failed: {str(exc)[:240]}"})
        yield sse("[DONE]")

    return sse_response(events())
