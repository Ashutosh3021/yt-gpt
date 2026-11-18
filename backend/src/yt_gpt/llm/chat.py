"""The retrieval -> answer -> tool loop, streamed as SSE-friendly events."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any

from ..retrieval.hybrid import Retriever
from ..util import parse_seconds, truncate
from ..workspace.store import WorkspaceStore
from .context import build_messages
from .provider import LlmConfig, LlmError, complete, embed_texts, stream_chat
from .tools import ToolContext, ToolResult, execute_tool, tool_definitions

log = logging.getLogger(__name__)

CITATION_RE = re.compile(r"\[([A-Za-z0-9_-]{6,})\s*@\s*(\d{1,3}(?::\d{2}){1,2})\]")
CITE_TAG_RE = re.compile(r"\[\[cite:([A-Za-z0-9_-]{6,}):(\d+)\]\]")
MAX_TOOL_ROUNDS = 4


def extract_citations(text: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for match in CITATION_RE.finditer(text):
        video_id = match.group(1)
        start = parse_seconds(match.group(2))
        key = (video_id, start)
        if key not in seen:
            seen.add(key)
            found.append({"videoId": video_id, "start": start})
    for match in CITE_TAG_RE.finditer(text):
        video_id = match.group(1)
        start = int(match.group(2))
        key = (video_id, start)
        if key not in seen:
            seen.add(key)
            found.append({"videoId": video_id, "start": start})
    return found


def filter_citations(citations: list[dict[str, Any]], workspace: dict[str, Any]) -> list[dict[str, Any]]:
    valid = {
        str(video.get("id")) for video in workspace.get("videos") or [] if video.get("status") == "ready"
    }
    return [citation for citation in citations if citation["videoId"] in valid]


def _parse_arguments(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _tool_context(
    store: WorkspaceStore,
    ws_dir: Any,
    workspace: dict[str, Any],
    session: dict[str, Any],
    retriever: Retriever,
    config: LlmConfig,
    visuals: bool,
) -> ToolContext:
    return ToolContext(
        store=store,
        ws_dir=ws_dir,
        workspace=workspace,
        session=session,
        retriever=retriever,
        config=config,
        visuals=visuals,
    )


async def run_chat(
    *,
    store: WorkspaceStore,
    ws_dir: Any,
    workspace: dict[str, Any],
    session: dict[str, Any],
    query: str,
    config: LlmConfig,
) -> AsyncIterator[dict[str, Any]]:
    retriever = Retriever.from_store(store, ws_dir, config.embedding_model or None)
    if retriever.has_dense:
        try:
            query_vectors = await embed_texts(config, [query])
            retriever.set_query_vector(query_vectors[0] if query_vectors else None)
        except LlmError as exc:
            log.warning("Query embedding failed; using keyword search only: %s", exc)
    messages, _chunks, _full = build_messages(
        store=store,
        ws_dir=ws_dir,
        workspace=workspace,
        session=session,
        config=config,
        query=query,
        retriever=retriever,
    )
    capabilities = config.capabilities
    workspace_settings = workspace.get("settings")
    if not isinstance(workspace_settings, dict):
        workspace_settings = {}
    session_settings = session.get("settings")
    if not isinstance(session_settings, dict):
        session_settings = {}
    visuals = bool(
        workspace_settings.get("useVisuals")
        and session_settings.get("useVisuals")
        and capabilities.get("vision")
    )
    tools = tool_definitions(visuals=visuals) if capabilities.get("tools") else []
    context = _tool_context(store, ws_dir, workspace, session, retriever, config, visuals)

    answer_parts: list[str] = []
    for round_index in range(MAX_TOOL_ROUNDS + 1):
        assistant_text = ""
        tool_calls: list[dict[str, Any]] = []
        async for event in stream_chat(config, messages, tools=tools or None):
            if event["type"] == "token":
                assistant_text += event["text"]
                yield {"type": "token", "text": event["text"]}
            elif event["type"] == "tool_calls":
                tool_calls = event["tool_calls"]
        if assistant_text:
            answer_parts.append(assistant_text)
        if not tool_calls:
            break
        if round_index >= MAX_TOOL_ROUNDS:
            if assistant_text:
                messages.append({"role": "assistant", "content": assistant_text})
            messages.append(
                {
                    "role": "user",
                    "content": "Stop using tools and answer now with the evidence you already have.",
                }
            )
            final = await complete(config, messages, max_tokens=1200)
            if final:
                answer_parts.append(final)
                yield {"type": "token", "text": final}
            break

        messages.append({"role": "assistant", "content": assistant_text or "", "tool_calls": tool_calls})
        for index, call in enumerate(tool_calls):
            function = call.get("function") if isinstance(call, dict) else None
            name = str((function or {}).get("name") or "")
            arguments = _parse_arguments(str((function or {}).get("arguments") or "{}"))
            call_id = str(call.get("id") or f"call_{round_index}_{index}")
            result = await execute_tool(name, arguments, context)
            if isinstance(result, ToolResult):
                messages.append({"role": "tool", "tool_call_id": call_id, "content": result.text})
                if result.images:
                    parts: list[dict[str, Any]] = [
                        {
                            "type": "text",
                            "text": f"Image returned by {name}. Inspect it for visual evidence.",
                        }
                    ]
                    parts.extend(
                        {"type": "image_url", "image_url": {"url": image}} for image in result.images
                    )
                    messages.append({"role": "user", "content": parts})
            else:
                messages.append({"role": "tool", "tool_call_id": call_id, "content": result})

    content = "\n\n".join(part.strip() for part in answer_parts if part.strip()).strip()
    citations = filter_citations(extract_citations(content), workspace)
    yield {"type": "final", "content": content, "citations": citations}


async def maybe_summarize(
    *,
    store: WorkspaceStore,
    ws_dir: Any,
    session_id: str,
    config: LlmConfig,
    keep_messages: int = 8,
    threshold: int = 20,
) -> None:
    try:
        raw = store.load_session(ws_dir, session_id)
        messages = [message for message in raw.get("messages") or [] if isinstance(message, dict)]
        if len(messages) <= threshold:
            return
        older = messages[:-keep_messages]
        recent = messages[-keep_messages:]
        transcript = "\n".join(
            f"{message.get('role')}: {truncate(str(message.get('content') or ''), 1200)}" for message in older
        )
        summary = await complete(
            config,
            [
                {
                    "role": "system",
                    "content": "Summarize the conversation compactly. Keep decisions, citations and open questions.",
                },
                {"role": "user", "content": transcript},
            ],
            max_tokens=500,
        )
        if not summary.strip():
            return
        raw["rolling_summary"] = summary.strip()
        raw["messages"] = recent
        store.save_session(ws_dir, raw)
    except LlmError:
        return
    except Exception:
        log.exception("Rolling summary failed for %s", session_id)
