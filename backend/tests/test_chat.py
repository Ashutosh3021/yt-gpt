from yt_gpt.llm.chat import extract_citations, filter_citations, run_chat
from yt_gpt.llm.provider import LlmConfig
from yt_gpt.workspace.store import WorkspaceStore


def test_extracts_and_deduplicates_citations():
    text = "One [dQw4w9WgXcQ @ 01:02] and [[cite:dQw4w9WgXcQ:62]] and [abc123def @ 2:03]."
    assert extract_citations(text) == [
        {"videoId": "dQw4w9WgXcQ", "start": 62},
        {"videoId": "abc123def", "start": 123},
    ]


def test_filters_unready_videos():
    workspace = {
        "videos": [
            {"id": "readyVid001", "status": "ready"},
            {"id": "queuedVid01", "status": "queued"},
        ]
    }
    citations = [{"videoId": "readyVid001", "start": 1}, {"videoId": "queuedVid01", "start": 2}]
    assert filter_citations(citations, workspace) == [{"videoId": "readyVid001", "start": 1}]


async def test_chat_runs_one_tool_round(home, monkeypatch):
    from yt_gpt.llm import chat as chat_module

    store = WorkspaceStore("u_test")
    workspace = store.create_workspace("Research")
    ws_dir = store.resolve(workspace["id"])
    store.add_video(ws_dir, "dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    store.write_segments(ws_dir, "dQw4w9WgXcQ", [{"start": 0, "end": 5, "text": "Attention matters."}])
    store.rebuild_derived(ws_dir)
    loaded = store.get_workspace(workspace["id"])
    session = store.load_session(ws_dir, loaded["sessions"][0]["id"])

    calls: list[list[dict]] = []

    async def fake_stream(config, messages, *, tools=None):
        calls.append(list(messages))
        if len(calls) == 1:
            yield {"type": "token", "text": "Let me check. "}
            yield {
                "type": "tool_calls",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "search_transcripts", "arguments": '{"query":"attention"}'},
                    }
                ],
            }
        else:
            yield {"type": "token", "text": "Attention routes tokens [dQw4w9WgXcQ @ 00:03]."}

    async def fake_tool(name, arguments, context):
        return "evidence: attention matters"

    monkeypatch.setattr(chat_module, "stream_chat", fake_stream)
    monkeypatch.setattr(chat_module, "execute_tool", fake_tool)

    events = [
        event
        async for event in run_chat(
            store=store,
            ws_dir=ws_dir,
            workspace=loaded,
            session=session,
            query="What matters?",
            config=LlmConfig(
                provider="openai",
                base_url="https://api.openai.com/v1",
                model="gpt-4.1-mini",
                embedding_model="text-embedding-3-small",
                api_key="test",
            ),
        )
    ]

    assert calls[1][-1] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": "evidence: attention matters",
    }
    assert events[-1]["type"] == "final"
    assert events[-1]["citations"] == [{"videoId": "dQw4w9WgXcQ", "start": 3}]
    assert "Let me check." in events[-1]["content"]
