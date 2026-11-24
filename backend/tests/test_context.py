from yt_gpt.llm.context import build_messages, message_tokens, prompt_token_budget, trim_messages
from yt_gpt.llm.provider import LlmConfig


class FakeRetriever:
    has_dense = False

    def search(self, query, *, k=8, video_ids=None):
        return [
            {"video_id": "vid00000001", "start": index * 30, "text": "word " * 900, "tokens": 900}
            for index in range(20)
        ]


def groq_config() -> LlmConfig:
    return LlmConfig(
        provider="custom",
        base_url="https://api.groq.com/openai/v1",
        model="qwen/qwen3.8-27b",
        embedding_model="",
        api_key="test",
    )


def test_groq_gets_a_tight_prompt_budget():
    assert prompt_token_budget(groq_config()) == 5500


def test_build_messages_respects_the_prompt_budget():
    workspace = {
        "name": "Test",
        "videos": [
            {"id": "vid00000001", "status": "ready", "title": "Video", "tokens": 100000},
            {"id": "vid00000002", "status": "ready", "title": "Video 2", "tokens": 100000},
        ],
        "sources": [],
    }
    session = {"settings": {"grounding": "strict"}, "messages": []}

    messages, chunks, full_context = build_messages(
        store=None,
        ws_dir=None,
        workspace=workspace,
        session=session,
        config=groq_config(),
        query="What happened?",
        retriever=FakeRetriever(),
        reserve_tokens=1500,
    )

    assert chunks
    assert full_context is False
    assert messages[-1] == {"role": "user", "content": "What happened?"}
    assert sum(message_tokens(message) for message in messages) <= 5500


def test_trim_messages_drops_history_and_truncates_evidence():
    messages = [
        {"role": "system", "content": "rules " * 2000},
        {"role": "user", "content": "old question " * 800},
        {"role": "assistant", "content": "old answer " * 800},
        {"role": "user", "content": "new question"},
        {"role": "tool", "tool_call_id": "call_1", "content": "tool result " * 2000},
    ]

    trimmed = trim_messages(messages, 1000)

    assert sum(message_tokens(message) for message in trimmed) <= 1000
    assert {"role": "user", "content": "new question"} in trimmed
    assert len(trimmed) < len(messages)
