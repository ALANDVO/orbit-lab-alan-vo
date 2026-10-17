"""HTTP integration tests for the runs API."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.models.run import RunState
from app.services.run import RunService


@pytest.fixture
def create_run_via_api(client: TestClient):
    """Helper to create a run via the API."""
    def _create(agent: str = "codex", prompt: str = "Fix the bug") -> dict:
        response = client.post("/api/runs/", json={
            "agent": agent,
            "repo_url": "https://github.com/user/repo",
            "prompt": prompt,
        })
        assert response.status_code == 201
        return response.json()
    return _create


class TestCreateRunAPI:
    def test_create_returns_201(self, create_run_via_api):
        run = create_run_via_api()
        assert "id" in run
        assert run["state"] == "pending"
        assert run["agent"] == "codex"
        assert run["worktree_path"]

    def test_create_includes_audit(self, create_run_via_api, client: TestClient):
        run = create_run_via_api()
        resp = client.get(f"/api/runs/{run['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["audit"]) == 1
        assert data["audit"][0]["action"] == "created"

    def test_invalid_payload_missing_prompt(self, client: TestClient):
        resp = client.post("/api/runs/", json={
            "agent": "codex",
            "repo_url": "https://github.com/user/repo",
        })
        assert resp.status_code == 422

    def test_invalid_payload_empty_agent(self, client: TestClient):
        resp = client.post("/api/runs/", json={
            "agent": "",
            "repo_url": "https://github.com/user/repo",
            "prompt": "test",
        })
        assert resp.status_code == 422

    def test_extra_field_rejected(self, client: TestClient):
        resp = client.post("/api/runs/", json={
            "agent": "codex",
            "repo_url": "https://github.com/user/repo",
            "prompt": "test",
            "extra": "field",
        })
        assert resp.status_code == 422


class TestListRunsAPI:
    def test_list_empty(self, client: TestClient):
        resp = client.get("/api/runs/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["runs"] == []
        assert data["total"] == 0

    def test_list_after_create(self, create_run_via_api, client: TestClient):
        create_run_via_api()
        resp = client.get("/api/runs/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["runs"]) == 1
        assert data["total"] == 1

    def test_list_with_pagination(self, client: TestClient):
        for i in range(5):
            client.post("/api/runs/", json={
                "agent": "codex",
                "repo_url": "https://github.com/user/repo",
                "prompt": f"prompt {i}",
            })
        resp = client.get("/api/runs/?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["runs"]) == 2
        assert data["total"] == 5
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_filter_by_state(self, create_run_via_api, client: TestClient):
        run = create_run_via_api()
        # Start and complete the run
        client.post(f"/api/runs/{run['id']}/start")
        client.post(f"/api/runs/{run['id']}/complete")

        resp = client.get("/api/runs/?state=running")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["runs"]) == 0

        resp = client.get("/api/runs/?state=completed")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["runs"]) == 1

    def test_filter_by_agent(self, create_run_via_api, client: TestClient):
        create_run_via_api(agent="codex")
        create_run_via_api(agent="claude-code")

        resp = client.get("/api/runs/?agent=codex")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["runs"]) == 1
        assert data["runs"][0]["agent"] == "codex"


class TestGetRunAPI:
    def test_get_existing(self, create_run_via_api, client: TestClient):
        run = create_run_via_api()
        resp = client.get(f"/api/runs/{run['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run"]["id"] == run["id"]
        assert len(data["audit"]) == 1
        assert data["audit"][0]["action"] == "created"

    def test_get_unknown_returns_404(self, client: TestClient):
        resp = client.get("/api/runs/nonexistent-id")
        assert resp.status_code == 404


class TestLifecycleAPI:
    def test_start_then_complete(self, create_run_via_api, client: TestClient):
        run = create_run_via_api()
        resp = client.post(f"/api/runs/{run['id']}/start")
        assert resp.status_code == 200
        assert resp.json()["state"] == "running"

        resp = client.post(f"/api/runs/{run['id']}/complete")
        assert resp.status_code == 200
        assert resp.json()["state"] == "completed"

    def test_start_twice_returns_409(self, create_run_via_api, client: TestClient):
        run = create_run_via_api()
        client.post(f"/api/runs/{run['id']}/start")
        resp = client.post(f"/api/runs/{run['id']}/start")
        assert resp.status_code == 409

    def test_cancel_run(self, create_run_via_api, client: TestClient):
        run = create_run_via_api()
        resp = client.delete(f"/api/runs/{run['id']}")
        assert resp.status_code == 200
        assert resp.json()["state"] == "cancelled"

    def test_cancel_terminal_returns_409(self, create_run_via_api, client: TestClient):
        run = create_run_via_api()
        client.post(f"/api/runs/{run['id']}/start")
        client.post(f"/api/runs/{run['id']}/complete")
        resp = client.delete(f"/api/runs/{run['id']}")
        assert resp.status_code == 409

    def test_fail_run(self, create_run_via_api, client: TestClient):
        run = create_run_via_api()
        client.post(f"/api/runs/{run['id']}/start")
        resp = client.post(f"/api/runs/{run['id']}/fail?error_message=Agent%20crashed")
        assert resp.status_code == 200
        assert resp.json()["state"] == "failed"
        assert resp.json()["error_message"] == "Agent crashed"

    def test_health_check(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "orbit-lab"


class TestRunLifecycleAudit:
    def test_audit_recorded_on_state_change(self, create_run_via_api, client: TestClient):
        run = create_run_via_api()
        client.post(f"/api/runs/{run['id']}/start")
        client.post(f"/api/runs/{run['id']}/complete")

        resp = client.get(f"/api/runs/{run['id']}")
        data = resp.json()
        actions = [entry["action"] for entry in data["audit"]]
        assert "created" in actions
        assert "state_changed" in actions
        assert len(actions) == 3  # created, started, completed

    def test_audit_recorded_on_cancel(self, create_run_via_api, client: TestClient):
        run = create_run_via_api()
        client.delete(f"/api/runs/{run['id']}")

        resp = client.get(f"/api/runs/{run['id']}")
        data = resp.json()
        actions = [entry["action"] for entry in data["audit"]]
        assert "created" in actions
        assert "cancelled" in actions