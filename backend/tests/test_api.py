import json

import pytest


def test_auth_flow(client):
    assert client.get("/api/auth/me").json() is None
    assert client.get("/api/workspaces").status_code == 401

    response = client.post(
        "/api/auth/signup",
        json={"name": "Ada", "email": "ada@example.com", "password": "secret1"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "ada@example.com"
    assert client.get("/api/auth/me").json()["name"] == "Ada"

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").json() is None

    response = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "secret1"})
    assert response.status_code == 200


def test_auth_rejects_bad_credentials(client):
    response = client.post(
        "/api/auth/signup",
        json={"name": "Ada", "email": "ada@example.com", "password": "secret1"},
    )
    assert response.status_code == 200
    assert (
        client.post("/api/auth/login", json={"email": "ada@example.com", "password": "nope"}).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/signup", json={"name": "Eve", "email": "ada@example.com", "password": "x"}
        ).status_code
        == 400
    )


def test_workspace_and_source_flow(auth_client):
    created = auth_client.post("/api/workspaces", json={"name": "Research"})
    assert created.status_code == 201
    workspace = created.json()
    workspace_id = workspace["id"]

    listed = auth_client.get("/api/workspaces").json()
    assert [item["id"] for item in listed] == [workspace_id]

    renamed = auth_client.patch(f"/api/workspaces/{workspace_id}", json={"name": "Renamed"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Renamed"

    source = auth_client.post(
        f"/api/workspaces/{workspace_id}/sources", json={"name": "notes", "content": "hello"}
    )
    assert source.status_code == 201
    assert source.json()["name"] == "notes.md"

    updated = auth_client.put(
        f"/api/workspaces/{workspace_id}/sources/notes.md",
        json={"content": "hello world", "note": "edit"},
    )
    assert updated.status_code == 200
    assert len(updated.json()["versions"]) == 2

    version_id = updated.json()["versions"][0]["id"]
    restored = auth_client.post(f"/api/workspaces/{workspace_id}/sources/notes.md/versions/{version_id}")
    assert restored.status_code == 200
    assert restored.json()["content"] == "hello"

    exported = auth_client.get(f"/api/workspaces/{workspace_id}/export")
    assert exported.status_code == 200
    assert exported.text.startswith("# Renamed")

    assert auth_client.delete(f"/api/workspaces/{workspace_id}").status_code == 204
    assert auth_client.get(f"/api/workspaces/{workspace_id}").status_code == 404


def test_add_videos_reports_invalid_links(auth_client, workspace):
    response = auth_client.post(
        f"/api/workspaces/{workspace['id']}/videos",
        json={"links": "not a link\nhttps://youtu.be/dQw4w9WgXcQ"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["invalid"] == ["not a link"]
    assert payload["added"][0]["id"] == "dQw4w9WgXcQ"
    assert payload["added"][0]["status"] in {"queued", "fetching_metadata"}


def test_settings_roundtrip(auth_client):
    current = auth_client.get("/api/settings/llm")
    assert current.status_code == 200
    assert current.json()["provider"] == "openai"
    assert current.json()["hasKey"] is False

    response = auth_client.put(
        "/api/settings/llm",
        json={"provider": "ollama", "baseUrl": "http://127.0.0.1:11434", "model": "llama3.2"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "ollama"
    assert payload["model"] == "llama3.2"
    assert payload["capabilities"]["contextK"] > 0


def test_session_chat_stream(auth_client, workspace, monkeypatch):
    from yt_gpt.server.routes import sessions as sessions_route

    session = auth_client.post(
        f"/api/workspaces/{workspace['id']}/sessions",
        json={"title": "First chat"},
    )
    assert session.status_code == 201
    session_id = session.json()["id"]

    async def fake_run_chat(**kwargs):
        yield {"type": "token", "text": "Hello "}
        yield {
            "type": "final",
            "content": "Hello [dQw4w9WgXcQ @ 00:03]",
            "citations": [{"videoId": "dQw4w9WgXcQ", "videoTitle": "A talk", "start": 3, "end": 9}],
        }

    monkeypatch.setattr(sessions_route, "run_chat", fake_run_chat)

    response = auth_client.post(
        f"/api/workspaces/{workspace['id']}/sessions/{session_id}/messages",
        json={"content": "What is the main idea?"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = [line[6:] for line in response.text.splitlines() if line.startswith("data: ")]
    assert json.loads(events[0]) == {"token": "Hello "}
    final = json.loads(events[1])
    assert final["message"]["role"] == "assistant"
    assert final["message"]["citations"][0]["start"] == 3
    assert events[-1] == "[DONE]"

    loaded = auth_client.get(f"/api/workspaces/{workspace['id']}/sessions/{session_id}")
    assert loaded.status_code == 200
    messages = loaded.json()["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[1]["content"].startswith("Hello")


@pytest.mark.parametrize("path", ["/api/workspaces/nope", "/api/workspaces/ws_missing"])
def test_missing_workspace_is_404(auth_client, path):
    assert auth_client.get(path).status_code == 404
