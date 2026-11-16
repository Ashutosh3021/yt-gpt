from __future__ import annotations

import os

import pytest


@pytest.fixture()
def home(tmp_path, monkeypatch):
    root = tmp_path / "home"
    monkeypatch.setenv("YT_GPT_HOME", str(root))
    monkeypatch.setenv("YT_GPT_SECRET", "test-secret")
    root.mkdir()
    return root


@pytest.fixture()
def client(home):
    from fastapi.testclient import TestClient

    from yt_gpt.server.app import create_app

    app = create_app()
    with TestClient(app, base_url="http://127.0.0.1:8765") as test_client:
        yield test_client


@pytest.fixture()
def auth_client(client):
    response = client.post(
        "/api/auth/signup",
        json={"name": "Ada", "email": "ada@example.com", "password": "secret1"},
    )
    assert response.status_code == 200, response.text
    return client


@pytest.fixture()
def workspace(auth_client):
    response = auth_client.post("/api/workspaces", json={"name": "Research"})
    assert response.status_code == 201, response.text
    return response.json()


def pytest_configure(config):
    os.environ.setdefault("YT_GPT_WHISPER_MODEL", "tiny")
