from __future__ import annotations

import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./data/test_onboard_repo_copilot.db"

from fastapi.testclient import TestClient

from app import database
from app.main import app


TEST_DATABASE = Path(__file__).resolve().parents[2] / "data" / "test_onboard_repo_copilot.db"


def clear_database() -> None:
    if TEST_DATABASE.exists():
        TEST_DATABASE.unlink()


def client() -> TestClient:
    clear_database()
    return TestClient(app)


def test_health_and_github_only_validation() -> None:
    with client() as test_client:
        assert test_client.get("/health").json()["status"] == "ok"
        response = test_client.post("/projects", json={"repo_url": "https://example.com/not-allowed", "owner_name": "Maya Patel"})
        assert response.status_code == 422
        assert "github.com" in response.json()["detail"]


def test_demo_supports_project_chat_and_human_handoff() -> None:
    with client() as test_client:
        project = test_client.post("/projects/demo", json={}).json()
        assert project["name"] == "acme/payments-service"
        assert project["modules"]
        session = test_client.post(f"/projects/{project['id']}/chat-sessions").json()
        answer = test_client.post(f"/chat-sessions/{session['id']}/messages", json={"question": "How does the architecture work?"})
        assert answer.status_code == 201
        answer_data = answer.json()
        assert answer_data["citations"]
        assert answer_data["escalation_recommended"] is False
        handoff = test_client.post(f"/projects/{project['id']}/escalations", json={"question": "Who owns this?", "answer": answer_data["content"]})
        assert handoff.status_code == 201
        assert handoff.json()["assigned_to"] == "Maya Patel"


def test_public_repo_creation_has_deterministic_fallback_when_offline(monkeypatch) -> None:
    def offline(_: str):
        raise OSError("offline")

    monkeypatch.setattr("app.repository_analysis._github_json", offline)
    with client() as test_client:
        request = {"repo_url": "https://github.com/openai/openai-python", "owner_name": "Ari Engineer", "owner_contact": "ari@example.com"}
        first = test_client.post("/projects", json=request)
        assert first.status_code == 201
        assert first.json()["status"] == "degraded"
        assert first.json()["documents"][0]["source"] == "Repository URL"
        second = test_client.post("/projects", json=request)
        assert second.status_code == 201
        assert second.json()["id"] == first.json()["id"]
