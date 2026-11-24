"""Conservative capability guesses plus a live probe for ``test``."""

from __future__ import annotations

import os
from typing import Any

GROQ_PROMPT_TOKENS = 5500
DEFAULT_PROMPT_TOKENS = 12000

VISION_HINTS = (
    "gpt-4o",
    "gpt-4.1",
    "gpt-5",
    "o4",
    "claude-3",
    "claude-4",
    "claude-sonnet-4",
    "claude-opus-4",
    "gemini",
    "llama-3.2-vision",
    "llama-4",
    "pixtral",
    "qwen-vl",
    "qwen2-vl",
)
CACHE_PROVIDERS = {"openai", "anthropic", "google", "openrouter"}
CONTEXT_SIZES: tuple[tuple[str, int], ...] = (
    ("gemini-1.5-pro", 2000),
    ("gemini-2", 1000),
    ("gemini-1.5", 1000),
    ("claude", 200),
    ("gpt-4.1", 1000),
    ("gpt-4o", 128),
    ("gpt-4", 128),
    ("gpt-3.5", 16),
    ("o1", 200),
    ("o3", 200),
    ("o4", 200),
    ("llama", 128),
    ("mistral", 128),
    ("qwen", 128),
    ("deepseek", 128),
    ("kimi", 256),
)


def _prompt_token_limit(base_url: str, context_k: int) -> int:
    override = os.environ.get("YT_GPT_MAX_PROMPT_TOKENS", "").strip()
    if override:
        try:
            return max(1000, int(override))
        except ValueError:
            pass
    limit = GROQ_PROMPT_TOKENS if "groq.com" in (base_url or "").lower() else DEFAULT_PROMPT_TOKENS
    return max(1000, min(limit, int(context_k * 1000 * 0.75)))


def model_capabilities(provider: str, model: str, base_url: str = "") -> dict[str, Any]:
    name = (model or "").lower()
    context = 32
    for hint, size in CONTEXT_SIZES:
        if hint in name:
            context = size
            break
    vision = any(hint in name for hint in VISION_HINTS)
    tools = True
    if provider == "ollama" and any(hint in name for hint in ("phi", "gemma")):
        tools = False
    return {
        "vision": vision,
        "tools": tools,
        "caching": provider in CACHE_PROVIDERS,
        "contextK": context,
        "promptTokens": _prompt_token_limit(base_url, context),
    }
