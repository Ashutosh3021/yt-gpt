"""Conservative capability guesses plus a live probe for ``test``."""

from __future__ import annotations

from typing import Any

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


def model_capabilities(provider: str, model: str) -> dict[str, Any]:
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
    }
