"""LiteLLM wrapper with a uniform streaming interface."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from .. import settings_store
from .capabilities import model_capabilities

try:
    import litellm
except Exception:  # pragma: no cover - broken install
    litellm = None  # type: ignore[assignment]


class LlmError(Exception):
    """A user-facing provider failure."""


def litellm_model(provider: str, model: str) -> str:
    model = (model or "").strip()
    if provider == "anthropic":
        return model if model.startswith("anthropic/") else f"anthropic/{model}"
    if provider == "google":
        return model if model.startswith("gemini/") else f"gemini/{model}"
    if provider == "openrouter":
        return model if model.startswith("openrouter/") else f"openrouter/{model}"
    if provider == "ollama":
        if model.startswith(("ollama/", "ollama_chat/")):
            return model
        return f"ollama_chat/{model}"
    if provider == "custom":
        return model if model.startswith("openai/") else f"openai/{model}"
    return model


def litellm_embedding_model(provider: str, model: str) -> str:
    model = (model or "").strip()
    if not model:
        raise LlmError("Choose an embedding model in Settings.")
    if provider == "anthropic":
        raise LlmError(
            "Anthropic does not provide a text embedding endpoint. Pick another provider for embeddings."
        )
    if provider == "google":
        return model if model.startswith(("gemini/", "vertex_ai/")) else f"gemini/{model}"
    if provider == "openrouter":
        return model if model.startswith("openrouter/") else f"openrouter/{model}"
    if provider == "ollama":
        return model if model.startswith("ollama/") else f"ollama/{model}"
    if provider == "custom":
        return model if model.startswith("openai/") else f"openai/{model}"
    return model


def friendly_error(exc: BaseException) -> str:
    text = str(exc) or exc.__class__.__name__
    lower = text.lower()
    if "api key" in lower or "authentication" in lower or "401" in lower or "unauthorized" in lower:
        return "The API key was rejected. Check the key in Settings."
    if "rate limit" in lower or "429" in lower or "quota" in lower:
        return "The provider rate-limited or ran out of quota. Wait and retry, or change models."
    if "context" in lower and ("length" in lower or "window" in lower):
        return "The conversation is larger than this model's context window. Start a new session or pick a larger model."
    if "not found" in lower or "404" in lower or "does not exist" in lower:
        return "That model id was not found at the provider. Check the model in Settings."
    if "connect" in lower or "timeout" in lower or "unreachable" in lower:
        return "The provider could not be reached. Check your network or the base URL."
    return f"The model call failed: {text[:260]}"


@dataclass(slots=True)
class LlmConfig:
    provider: str
    base_url: str
    model: str
    embedding_model: str
    api_key: str | None

    @property
    def resolved_model(self) -> str:
        return litellm_model(self.provider, self.model)

    @property
    def capabilities(self) -> dict[str, Any]:
        return model_capabilities(self.provider, self.model)

    @classmethod
    def for_user(cls, user_id: str) -> LlmConfig:
        stored = settings_store.read_llm(user_id)
        return cls(
            provider=stored["provider"],
            base_url=stored["base_url"],
            model=stored["model"],
            embedding_model=stored["embedding_model"],
            api_key=settings_store.get_api_key(user_id),
        )

    def litellm_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.resolved_model,
            "timeout": 120,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        elif self.provider in {"ollama", "custom"}:
            kwargs["api_key"] = "not-needed"
        if self.provider in {"openai", "openrouter", "ollama", "custom"} and self.base_url:
            base = self.base_url.rstrip("/")
            if self.provider == "ollama" and base.endswith("/v1"):
                base = base[:-3]
            kwargs["api_base"] = base
        return kwargs


def _require() -> Any:
    if litellm is None:  # pragma: no cover
        raise LlmError("LiteLLM is not installed. Reinstall yt-gpt.")
    return litellm


def _delta_event(delta: Any) -> tuple[str, list[dict[str, Any]]]:
    text = getattr(delta, "content", None)
    content = text if isinstance(text, str) else ""

    buffer: dict[int, dict[str, Any]] = {}
    for call in getattr(delta, "tool_calls", None) or []:
        index = getattr(call, "index", 0) or 0
        slot = buffer.setdefault(index, {"index": index, "id": "", "name": "", "arguments": ""})
        if getattr(call, "id", None):
            slot["id"] = call.id
        function = getattr(call, "function", None)
        if function is not None:
            if getattr(function, "name", None):
                slot["name"] = function.name
            if getattr(function, "arguments", None):
                slot["arguments"] += function.arguments
    return content, [buffer[index] for index in sorted(buffer)]


async def stream_chat(
    config: LlmConfig,
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1400,
) -> AsyncIterator[dict[str, Any]]:
    module = _require()
    kwargs = config.litellm_kwargs()
    kwargs.update(
        {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
    )
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    try:
        stream = await module.acompletion(**kwargs)
        pending: dict[int, dict[str, Any]] = {}
        async for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            choice = choices[0]
            delta = getattr(choice, "delta", None)
            content, calls = _delta_event(delta)
            if content:
                yield {"type": "token", "text": content}
            for call in calls:
                index = call.get("index", 0)
                target = pending.setdefault(
                    index, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                )
                if call.get("id"):
                    target["id"] = call["id"]
                if call.get("name"):
                    target["function"]["name"] = call["name"]
                if call.get("arguments"):
                    target["function"]["arguments"] += call["arguments"]
            finish = getattr(choice, "finish_reason", None)
            if finish:
                yield {"type": "finish", "reason": finish}
        if pending:
            tool_calls = []
            for index in sorted(pending):
                call = pending[index]
                tool_calls.append(
                    {
                        "id": call.get("id") or f"call_{index}",
                        "type": "function",
                        "function": {
                            "name": call["function"]["name"],
                            "arguments": call["function"]["arguments"] or "{}",
                        },
                    }
                )
            yield {"type": "tool_calls", "tool_calls": tool_calls}
    except Exception as exc:
        raise LlmError(friendly_error(exc)) from exc


async def complete(
    config: LlmConfig,
    messages: list[dict[str, Any]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 600,
) -> str:
    module = _require()
    kwargs = config.litellm_kwargs()
    kwargs.update({"messages": messages, "temperature": temperature, "max_tokens": max_tokens})
    try:
        response = await module.acompletion(**kwargs)
    except Exception as exc:
        raise LlmError(friendly_error(exc)) from exc
    try:
        choice = response.choices[0]
        content = choice.message.content
    except Exception as exc:  # pragma: no cover - defensive
        raise LlmError("The provider returned an unexpected response.") from exc
    return content if isinstance(content, str) else ""


async def embed_texts(config: LlmConfig, texts: list[str], *, batch_size: int = 32) -> list[list[float]]:
    if not texts:
        return []
    module = _require()
    kwargs = config.litellm_kwargs()
    kwargs["model"] = litellm_embedding_model(config.provider, config.embedding_model)
    vectors: list[list[float]] = []
    for offset in range(0, len(texts), max(1, batch_size)):
        batch = [text or " " for text in texts[offset : offset + batch_size]]
        try:
            response = await module.aembedding(input=batch, **kwargs)
        except Exception as exc:
            raise LlmError(friendly_error(exc)) from exc
        rows = getattr(response, "data", None)
        if rows is None and isinstance(response, dict):
            rows = response.get("data")
        if not isinstance(rows, list) or len(rows) != len(batch):
            raise LlmError("The embedding provider returned an unexpected response.")
        for row in rows:
            value = getattr(row, "embedding", None)
            if value is None and isinstance(row, dict):
                value = row.get("embedding")
            if not isinstance(value, list) or not value:
                raise LlmError("The embedding provider returned an empty vector.")
            vectors.append([float(number) for number in value])
    return vectors


async def test_connection(config: LlmConfig) -> tuple[bool, str]:
    if not config.model:
        return False, "Choose a model first."
    if config.provider not in {"ollama", "custom"} and not config.api_key:
        return False, "Add an API key for this provider."
    module = _require()
    kwargs = config.litellm_kwargs()
    kwargs.update(
        {
            "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
            "temperature": 0,
            "max_tokens": 8,
        }
    )
    try:
        response = await module.acompletion(**kwargs)
        text = response.choices[0].message.content or ""
    except Exception as exc:
        return False, friendly_error(exc)
    preview = json.dumps(str(text))[:80]
    return True, f"Connected to {config.model}. Reply: {preview}"
