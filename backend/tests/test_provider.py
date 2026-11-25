from types import SimpleNamespace

import pytest

from yt_gpt.llm.provider import (
    LlmConfig,
    LlmError,
    friendly_error,
    litellm_embedding_model,
    litellm_model,
    retry_after_seconds,
)


def test_provider_prefixes():
    assert litellm_model("anthropic", "claude-sonnet-4") == "anthropic/claude-sonnet-4"
    assert litellm_model("google", "gemini-2.5-flash") == "gemini/gemini-2.5-flash"
    assert litellm_model("openrouter", "openai/gpt-4.1") == "openrouter/openai/gpt-4.1"
    assert litellm_model("ollama", "llama3.2") == "ollama_chat/llama3.2"
    assert litellm_model("custom", "my-model") == "openai/my-model"


def test_embedding_model_prefixes():
    assert litellm_embedding_model("openai", "text-embedding-3-small") == "text-embedding-3-small"
    assert litellm_embedding_model("google", "text-embedding-004") == "gemini/text-embedding-004"
    assert litellm_embedding_model("ollama", "nomic-embed-text") == "ollama/nomic-embed-text"
    assert litellm_embedding_model("custom", "bge-m3") == "openai/bge-m3"
    with pytest.raises(LlmError):
        litellm_embedding_model("anthropic", "claude-sonnet-4")


def test_ollama_base_url_drops_openai_suffix():
    config = LlmConfig(
        provider="ollama",
        base_url="http://127.0.0.1:11434/v1/",
        model="llama3.2",
        embedding_model="",
        api_key=None,
    )
    kwargs = config.litellm_kwargs()
    assert kwargs["api_base"] == "http://127.0.0.1:11434"
    assert kwargs["api_key"] == "not-needed"


def test_friendly_errors():
    assert "API key" in friendly_error(RuntimeError("401 unauthorized"))
    assert "rate-limited" in friendly_error(RuntimeError("429 rate limit"))
    assert "per-minute input-token limit" in friendly_error(
        RuntimeError("litellm.RateLimitError: input tokens per minute (ITPM): Limit 7000")
    )
    assert "context window" in friendly_error(RuntimeError("context length exceeded"))


def test_retry_after_uses_provider_header():
    exc = RuntimeError("429 rate limit")
    exc.response = SimpleNamespace(headers={"retry-after": "12"})  # type: ignore[attr-defined]
    assert retry_after_seconds(exc) == 12


def test_retry_after_parses_provider_message():
    assert retry_after_seconds(RuntimeError("RateLimitError: try again in 2.4s")) == 3
    assert retry_after_seconds(RuntimeError('429 {"retry_after": 7}')) == 7


def test_retry_after_defaults_for_rate_limit_only():
    assert retry_after_seconds(RuntimeError("429 rate limit")) == 60
    assert retry_after_seconds(RuntimeError("401 unauthorized")) is None
