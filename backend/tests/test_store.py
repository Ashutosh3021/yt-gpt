from yt_gpt.workspace.store import NotFound, WorkspaceStore

SEGMENTS = [
    {"start": 0.0, "end": 3.0, "text": "First sentence about attention."},
    {"start": 3.0, "end": 6.0, "text": "Second sentence about tokens."},
]


def test_workspace_video_lifecycle(home):
    store = WorkspaceStore("u_test")
    workspace = store.create_workspace("Research")
    ws_dir = store.resolve(workspace["id"])

    video = store.add_video(ws_dir, "dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert video is not None
    assert video["status"] == "queued"
    assert store.add_video(ws_dir, "dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ") is None

    store.write_segments(ws_dir, "dQw4w9WgXcQ", SEGMENTS)
    store.update_video_meta(ws_dir, "dQw4w9WgXcQ", {"title": "A talk", "duration_s": 6})
    count = store.rebuild_derived(ws_dir)
    assert count == 1

    video = store.get_video(ws_dir, "dQw4w9WgXcQ")
    assert video["status"] == "ready"
    assert video["tokens"] > 0
    assert video["title"] == "A talk"
    assert video["segments"] == SEGMENTS
    assert len(store.all_chunks(ws_dir)) == 1
    assert "A talk" in store.read_transcripts(ws_dir)

    store.remove_video(ws_dir, "dQw4w9WgXcQ")
    assert store.get_workspace(workspace["id"])["videos"] == []


def test_source_versions_and_restore(home):
    store = WorkspaceStore("u_test")
    workspace = store.create_workspace("Docs")
    ws_dir = store.resolve(workspace["id"])

    created = store.create_source(ws_dir, "notes", "# Notes\n")
    assert created["name"] == "notes.md"
    updated = store.update_source(ws_dir, "notes.md", "# Notes\n\nBody", "Added body")
    assert len(updated["versions"]) == 2

    version_id = updated["versions"][0]["id"]
    restored = store.restore_version(ws_dir, "notes.md", version_id)
    assert restored["content"] == "# Notes\n"
    assert len(restored["versions"]) == 3

    store.delete_source(ws_dir, "notes.md")
    try:
        store.get_source(ws_dir, "notes.md")
    except NotFound:
        pass
    else:
        raise AssertionError("source should be gone")


def test_sessions_and_rename(home):
    store = WorkspaceStore("u_test")
    workspace = store.create_workspace("Original")
    ws_dir = store.resolve(workspace["id"])

    session = store.create_session(ws_dir, "Chat")
    store.append_message(ws_dir, session["id"], {"id": "m_1", "role": "user", "content": "hi", "ts": "now"})
    loaded = store.get_session(ws_dir, session["id"])
    assert loaded["messages"][0]["content"] == "hi"

    renamed = store.rename_workspace(workspace["id"], "Renamed")
    assert renamed["name"] == "Renamed"
    assert store.resolve(renamed["id"]) == store.resolve(renamed["slug"])

    store.delete_workspace(renamed["id"])
    try:
        store.resolve(renamed["id"])
    except NotFound:
        pass
    else:
        raise AssertionError("workspace should be gone")
