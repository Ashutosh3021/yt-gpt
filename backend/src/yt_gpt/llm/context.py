"""Assemble the per-turn prompt within a token budget."""

from __future__ import annotations

from typing import Any

from ..retrieval.hybrid import Retriever
from ..util import estimate_tokens, truncate
from ..workspace.store import WorkspaceStore
from .prompts import build_system_prompt, evidence_message, sources_message

HISTORY_MESSAGES = 12
HISTORY_CHAR_LIMIT = 4000


def total_transcript_tokens(videos: list[dict[str, Any]]) -> int:
    return sum(int(video.get("tokens") or 0) for video in videos if video.get("status") == "ready")


def _history(session: dict[str, Any], query: str) -> list[dict[str, str]]:
    messages = [message for message in session.get("messages") or [] if isinstance(message, dict)]
    if (
        messages
        and messages[-1].get("role") == "user"
        and str(messages[-1].get("content", "")).strip() == query.strip()
    ):
        messages = messages[:-1]
    recent = messages[-HISTORY_MESSAGES:]
    out: list[dict[str, str]] = []
    for message in recent:
        role = message.get("role")
        if role not in {"user", "assistant"}:
            continue
        content = truncate(str(message.get("content") or ""), HISTORY_CHAR_LIMIT)
        if content:
            out.append({"role": role, "content": content})
    return out


def _select_evidence(
    *,
    store: WorkspaceStore,
    ws_dir: Any,
    videos: list[dict[str, Any]],
    query: str,
    retriever: Retriever,
    budget_tokens: int,
) -> tuple[list[dict[str, Any]], bool]:
    ready_tokens = total_transcript_tokens(videos)
    if ready_tokens and ready_tokens <= budget_tokens:
        chunks = store.all_chunks(ws_dir)
        if chunks:
            selected: list[dict[str, Any]] = []
            used = 0
            for chunk in chunks:
                cost = int(chunk.get("tokens") or estimate_tokens(str(chunk.get("text") or "")))
                if selected and used + cost > budget_tokens:
                    break
                selected.append(chunk)
                used += cost
            return selected, True

    candidates = retriever.search(query, k=24)
    selected = []
    used = 0
    for chunk in candidates:
        cost = int(chunk.get("tokens") or estimate_tokens(str(chunk.get("text") or "")))
        if selected and used + cost > budget_tokens:
            continue
        selected.append(chunk)
        used += cost
        if len(selected) >= 12:
            break
    return selected, False


def build_messages(
    *,
    store: WorkspaceStore,
    ws_dir: Any,
    workspace: dict[str, Any],
    session: dict[str, Any],
    config: Any,
    query: str,
    retriever: Retriever | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    videos = [video for video in workspace.get("videos") or [] if isinstance(video, dict)]
    sources = [source for source in workspace.get("sources") or [] if isinstance(source, dict)]
    settings = session.get("settings")
    if not isinstance(settings, dict):
        settings = {}
    grounding = str(settings.get("grounding") or "strict")
    persona_id = str(settings.get("personaId") or "default")
    persona_prompt = settings.get("personaPrompt")
    context_k = int((config.capabilities or {}).get("contextK") or 32)
    total_budget = max(4000, int(context_k * 1000 * 0.6))
    evidence_budget = int(total_budget * 0.55)

    if retriever is None:
        retriever = Retriever.from_store(store, ws_dir)
    chunks, full_context = _select_evidence(
        store=store,
        ws_dir=ws_dir,
        videos=videos,
        query=query,
        retriever=retriever,
        budget_tokens=evidence_budget,
    )

    system = build_system_prompt(
        workspace_name=str(workspace.get("name") or "Workspace"),
        grounding=grounding,
        persona_id=persona_id,
        persona_prompt=str(persona_prompt) if persona_prompt else None,
        videos=videos,
        sources=sources,
        rolling_summary=str(session.get("rollingSummary") or ""),
    )
    workspace_settings = workspace.get("settings") if isinstance(workspace.get("settings"), dict) else {}
    if (
        workspace_settings.get("useVisuals")
        and settings.get("useVisuals")
        and (config.capabilities or {}).get("vision")
    ):
        system += (
            "\n\nVisual tools are enabled. When the question depends on slides, charts, demos or "
            "on-screen text, inspect a contact sheet and use get_frame for small details. Cite the "
            "exact timestamp and do not describe visual details you have not actually seen."
        )
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]

    evidence = evidence_message(chunks, full_context=full_context)
    if evidence:
        messages.append({"role": "system", "content": evidence})

    if grounding != "strict":
        notes = sources_message(sources)
        if notes:
            messages.append({"role": "system", "content": notes})

    messages.extend(_history(session, query))
    messages.append({"role": "user", "content": query})
    return messages, chunks, full_context
