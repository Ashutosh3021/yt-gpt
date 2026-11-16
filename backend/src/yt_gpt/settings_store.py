"""Per-user LLM settings and secrets.

Keys go to the OS keyring when possible. The fallback is a 0600 file under the
user's private ``secrets/`` directory, never inside a workspace.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from . import config
from .util import atomic_write_text, ensure_private, iso_now, read_json, write_json

DEFAULT_PROVIDER = "openai"
DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "google": "https://generativelanguage.googleapis.com/v1beta",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://127.0.0.1:11434/v1",
    "custom": "",
}
DEFAULT_MODELS = {
    "openai": "gpt-4.1-mini",
    "anthropic": "claude-sonnet-4-5",
    "google": "gemini-2.5-flash",
    "openrouter": "openai/gpt-4.1-mini",
    "ollama": "llama3.1",
    "custom": "local-model",
}
DEFAULT_EMBEDDING_MODELS = {
    "openai": "text-embedding-3-small",
    "anthropic": "",
    "google": "text-embedding-004",
    "openrouter": "",
    "ollama": "nomic-embed-text",
    "custom": "",
}
PROVIDERS = set(DEFAULT_BASE_URLS)
KEYRING_SERVICE = "yt-gpt"


def _settings_path(user_id: str) -> Path:
    return config.user_root(user_id) / "settings.json"


def _keyring():
    try:
        import keyring

        return keyring
    except Exception:
        return None


def _keyring_username(user_id: str) -> str:
    return f"{user_id}:llm"


def read_llm(user_id: str) -> dict[str, Any]:
    raw = read_json(_settings_path(user_id))
    llm = raw.get("llm") if isinstance(raw, dict) else None
    stored = llm if isinstance(llm, dict) else {}
    provider_value = stored.get("provider")
    provider = (
        provider_value
        if isinstance(provider_value, str) and provider_value in PROVIDERS
        else DEFAULT_PROVIDER
    )
    base_url = stored.get("base_url")
    model = stored.get("model")
    embedding = stored.get("embedding_model")
    return {
        "provider": provider,
        "base_url": str(base_url) if base_url is not None else DEFAULT_BASE_URLS[provider],
        "model": str(model) if model else DEFAULT_MODELS[provider],
        "embedding_model": str(embedding) if embedding is not None else DEFAULT_EMBEDDING_MODELS[provider],
    }


def write_llm(user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    current = read_llm(user_id)
    provider = patch.get("provider", current["provider"])
    if provider not in PROVIDERS:
        provider = current["provider"]
    base_url = patch.get("base_url", current["base_url"])
    model = patch.get("model", current["model"])
    embedding = patch.get("embedding_model", current["embedding_model"])
    updated = {
        "provider": provider,
        "base_url": str(base_url or DEFAULT_BASE_URLS[provider]),
        "model": str(model or DEFAULT_MODELS[provider]),
        "embedding_model": str(embedding or ""),
    }
    path = _settings_path(user_id)
    raw = read_json(path)
    data = raw if isinstance(raw, dict) else {}
    data["llm"] = updated
    data["updated_at"] = iso_now()
    write_json(path, data)
    return updated


def _fallback_key_path(user_id: str) -> Path:
    return config.secrets_root() / f"{user_id}.llm.key"


def set_api_key(user_id: str, api_key: str) -> None:
    api_key = api_key.strip()
    if not api_key:
        return
    keyring = _keyring()
    if keyring is not None:
        try:
            keyring.set_password(KEYRING_SERVICE, _keyring_username(user_id), api_key)
            path = _fallback_key_path(user_id)
            if path.exists():
                path.unlink()
            return
        except Exception:
            pass
    path = _fallback_key_path(user_id)
    atomic_write_text(path, api_key + "\n")
    ensure_private(path)


def get_api_key(user_id: str) -> str | None:
    env_key = _env_api_key(read_llm(user_id)["provider"])
    if env_key:
        return env_key
    keyring = _keyring()
    if keyring is not None:
        try:
            value = keyring.get_password(KEYRING_SERVICE, _keyring_username(user_id))
        except Exception:
            value = None
        if value:
            return value
    path = _fallback_key_path(user_id)
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def delete_api_key(user_id: str) -> None:
    keyring = _keyring()
    if keyring is not None:
        try:
            keyring.delete_password(KEYRING_SERVICE, _keyring_username(user_id))
        except Exception:
            pass
    path = _fallback_key_path(user_id)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def _env_api_key(provider: str) -> str | None:
    names: dict[str, tuple[str, ...]] = {
        "openai": ("OPENAI_API_KEY",),
        "anthropic": ("ANTHROPIC_API_KEY",),
        "google": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "openrouter": ("OPENROUTER_API_KEY",),
        "ollama": ("OLLAMA_API_KEY",),
        "custom": ("YT_GPT_API_KEY", "OPENAI_API_KEY"),
    }
    for name in names.get(provider, ()):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def mask_key(api_key: str | None) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "•" * max(4, len(api_key))
    return f"{api_key[:3]}…{api_key[-4:]}"


def uses_keyring_fallback(user_id: str) -> bool:
    return _fallback_key_path(user_id).exists() and get_api_key(user_id) is not None
