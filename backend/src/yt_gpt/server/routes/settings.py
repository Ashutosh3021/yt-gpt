"""LLM settings, connection test and derived-file rebuild."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ... import settings_store
from ...llm.capabilities import model_capabilities
from ...llm.provider import LlmConfig, test_connection
from ...workspace.models import LlmPatchBody
from ...workspace.store import StoreError
from ..deps import CurrentUser, Store

router = APIRouter(prefix="/api", tags=["settings"])


def _public(user_id: str) -> dict[str, Any]:
    stored = settings_store.read_llm(user_id)
    api_key = settings_store.get_api_key(user_id)
    return {
        "provider": stored["provider"],
        "baseUrl": stored["base_url"],
        "model": stored["model"],
        "embeddingModel": stored["embedding_model"],
        "hasKey": bool(api_key),
        "keyMasked": settings_store.mask_key(api_key),
        "capabilities": model_capabilities(stored["provider"], stored["model"]),
    }


@router.get("/settings/llm")
async def get_llm(user: CurrentUser) -> dict[str, Any]:
    return _public(user["id"])


@router.put("/settings/llm")
async def put_llm(body: LlmPatchBody, user: CurrentUser) -> dict[str, Any]:
    patch = body.model_dump(exclude_none=True)
    api_key = patch.pop("apiKey", None)
    if "baseUrl" in patch:
        patch["base_url"] = patch.pop("baseUrl")
    if "embeddingModel" in patch:
        patch["embedding_model"] = patch.pop("embeddingModel")
    provider = patch.get("provider")
    current = settings_store.read_llm(user["id"])
    if provider and provider != current["provider"]:
        patch.setdefault("base_url", settings_store.DEFAULT_BASE_URLS[provider])
        patch.setdefault("model", settings_store.DEFAULT_MODELS[provider])
        patch.setdefault("embedding_model", settings_store.DEFAULT_EMBEDDING_MODELS[provider])
    settings_store.write_llm(user["id"], patch)
    if isinstance(api_key, str) and api_key.strip():
        settings_store.set_api_key(user["id"], api_key)
    return _public(user["id"])


@router.post("/settings/llm/test")
async def test_llm(user: CurrentUser) -> dict[str, Any]:
    ok, message = await test_connection(LlmConfig.for_user(user["id"]))
    return {"ok": ok, "message": message}


@router.post("/doctor/rebuild")
async def rebuild(user: CurrentUser, store: Store) -> dict[str, Any]:
    count = 0
    failed = 0
    for workspace in store.list_workspaces():
        try:
            ws_dir = store.resolve(str(workspace.get("id")))
            count += store.rebuild_derived(ws_dir)
        except StoreError:
            failed += 1
    if failed:
        return {"ok": False, "message": f"Rebuilt {count} video(s); {failed} workspace(s) failed."}
    return {"ok": True, "message": f"Rebuilt derived files for {count} video(s)."}
