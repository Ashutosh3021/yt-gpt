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


async def test_chat_attaches_visual_tool_image(home, monkeypatch):
    from yt_gpt.llm import chat as chat_module
    from yt_gpt.llm.tools import ToolResult

    store = WorkspaceStore("u_test")
    workspace = store.create_workspace("Visual")
    ws_dir = store.resolve(workspace["id"])
    store.add_video(ws_dir, "dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    store.write_segments(ws_dir, "dQw4w9WgXcQ", [{"start": 0, "end": 5, "text": "Slide one."}])
    store.rebuild_derived(ws_dir)
    store.update_workspace_settings(workspace["id"], {"useVisuals": True})
    loaded = store.get_workspace(workspace["id"])
    session = loaded["sessions"][0]
    store.update_session(ws_dir, session["id"], settings={"useVisuals": True})
    session = store.get_session(ws_dir, session["id"])

    calls: list[list[dict]] = []

    async def fake_stream(config, messages, *, tools=None):
        calls.append(list(messages))
        if len(calls) == 1:
            yield {
                "type": "tool_calls",
                "tool_calls": [
                    {
                        "id": "call_visual",
                        "type": "function",
                        "function": {
                            "name": "get_contact_sheet",
                            "arguments": '{"video_id":"dQw4w9WgXcQ"}',
                        },
                    }
                ],
            }
        else:
            yield {"type": "token", "text": "The slide shows a chart."}

    async def fake_tool(name, arguments, context):
        assert context.visuals is True
        return ToolResult("sheet ready", ["data:image/jpeg;base64,AAAA"])

    monkeypatch.setattr(chat_module, "stream_chat", fake_stream)
    monkeypatch.setattr(chat_module, "execute_tool", fake_tool)

    events = [
        event
        async for event in run_chat(
            store=store,
            ws_dir=ws_dir,
            workspace=loaded,
            session=session,
            query="What does the slide show?",
            config=LlmConfig(
                provider="openai",
                base_url="https://api.openai.com/v1",
                model="gpt-4.1-mini",
                embedding_model="",
                api_key="test",
            ),
        )
    ]

    assert calls[1][-2] == {
        "role": "tool",
        "tool_call_id": "call_visual",
        "content": "sheet ready",
    }
    image_message = calls[1][-1]
    assert image_message["role"] == "user"
    assert image_message["content"][1]["image_url"]["url"] == "data:image/jpeg;base64,AAAA"
    assert events[-1]["type"] == "final"
