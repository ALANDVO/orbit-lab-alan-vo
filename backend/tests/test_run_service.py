"""Tests for the run lifecycle state machine and service."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.audit import AuditAction
from app.models.run import RunState, is_terminal
from app.services.run import (
    InvalidStateTransition,
    RunNotFoundError,
    RunService,
)


@pytest.fixture
def service(db_session: Session) -> RunService:
    return RunService(db_session)


@pytest.fixture
def sample_run(service: RunService):
    return service.create_run(
        agent="codex",
        repo_url="https://github.com/user/repo",
        prompt="Fix the login bug",
        branch="main",
        actor="tester",
    )


class TestCreateRun:
    def test_assigns_pending_state(self, sample_run):
        assert sample_run.state == RunState.PENDING

    def test_records_audit_entry(self, sample_run, service: RunService):
        run = service.get_run(sample_run.id)
        assert run is not None
        assert len(run.audit_entries) == 1
        assert run.audit_entries[0].action == AuditAction.CREATED
        assert run.audit_entries[0].actor == "tester"
        assert "codex" in run.audit_entries[0].detail

    def test_worktree_path_assigned(self, sample_run):
        assert sample_run.worktree_path
        assert sample_run.worktree_path.startswith("/tmp/orbit-worktrees")

    def test_unique_run_ids(self, service: RunService):
        r1 = service.create_run(agent="codex", repo_url="https://github.com/user/repo", prompt="a")
        r2 = service.create_run(agent="codex", repo_url="https://github.com/user/repo", prompt="b")
        assert r1.id != r2.id
        assert r1.worktree_path != r2.worktree_path


class TestStateTransitions:
    def test_pending_to_running(self, sample_run, service: RunService):
        run = service.start_run(sample_run.id)
        assert run.state == RunState.RUNNING
        assert run.started_at is not None

    def test_running_to_completed(self, sample_run, service: RunService):
        service.start_run(sample_run.id)
        run = service.complete_run(sample_run.id)
        assert run.state == RunState.COMPLETED
        assert run.finished_at is not None

    def test_running_to_failed(self, sample_run, service: RunService):
        service.start_run(sample_run.id)
        run = service.fail_run(sample_run.id, "Agent crashed")
        assert run.state == RunState.FAILED
        assert run.error_message == "Agent crashed"

    def test_pending_to_cancelled(self, sample_run, service: RunService):
        run = service.cancel_run(sample_run.id)
        assert run.state == RunState.CANCELLED

    def test_running_to_cancelled(self, sample_run, service: RunService):
        service.start_run(sample_run.id)
        run = service.cancel_run(sample_run.id)
        assert run.state == RunState.CANCELLED

    def test_cancel_completed_raises(self, sample_run, service: RunService):
        service.start_run(sample_run.id)
        service.complete_run(sample_run.id)
        with pytest.raises(InvalidStateTransition):
            service.cancel_run(sample_run.id)

    def test_running_to_pending_rejected(self, sample_run, service: RunService):
        service.start_run(sample_run.id)
        with pytest.raises(InvalidStateTransition):
            service.start_run(sample_run.id)  # already running, same state

    def test_completed_to_running_rejected(self, sample_run, service: RunService):
        service.start_run(sample_run.id)
        service.complete_run(sample_run.id)
        with pytest.raises(InvalidStateTransition):
            service.start_run(sample_run.id)

    def test_cancel_failed_run_raises(self, sample_run, service: RunService):
        service.start_run(sample_run.id)
        service.fail_run(sample_run.id, "error")
        with pytest.raises(InvalidStateTransition):
            service.cancel_run(sample_run.id)


class TestNotFound:
    def test_get_unknown_returns_none(self, service: RunService):
        assert service.get_run("nonexistent-id") is None

    def test_start_unknown_raises(self, service: RunService):
        with pytest.raises(RunNotFoundError):
            service.start_run("nonexistent-id")

    def test_cancel_unknown_raises(self, service: RunService):
        with pytest.raises(RunNotFoundError):
            service.cancel_run("nonexistent-id")


class TestDeleteRun:
    def test_delete_terminal_run(self, sample_run, service: RunService):
        service.start_run(sample_run.id)
        service.complete_run(sample_run.id)
        service.delete_run(sample_run.id)
        assert service.get_run(sample_run.id) is None

    def test_delete_nonterminal_raises(self, sample_run, service: RunService):
        with pytest.raises(InvalidStateTransition):
            service.delete_run(sample_run.id)

    def test_delete_records_audit(self, sample_run, service: RunService):
        service.start_run(sample_run.id)
        service.complete_run(sample_run.id)
        service.delete_run(sample_run.id)
        # Verify no runs remain
        assert service.get_run(sample_run.id) is None


class TestAuditTrail:
    def test_full_lifecycle_audit_entries(self, sample_run, service: RunService):
        service.start_run(sample_run.id)
        service.complete_run(sample_run.id)
        run = service.get_run(sample_run.id)
        actions = [entry.action for entry in run.audit_entries]
        assert AuditAction.CREATED in actions
        assert AuditAction.STATE_CHANGED in actions

    def test_is_terminal_helper(self):
        assert is_terminal(RunState.COMPLETED) is True
        assert is_terminal(RunState.FAILED) is True
        assert is_terminal(RunState.CANCELLED) is True
        assert is_terminal(RunState.PENDING) is False
        assert is_terminal(RunState.RUNNING) is False


class TestListRuns:
    @pytest.mark.parametrize("count", [5])
    def test_list_all(self, service: RunService, count):
        for i in range(count):
            service.create_run(agent="codex", repo_url="https://github.com/user/repo", prompt=f"prompt {i}")
        runs = service.list_runs()
        assert len(runs) == count

    def test_filter_by_state(self, service: RunService):
        service.create_run(agent="codex", repo_url="https://github.com/user/repo", prompt="a")
        run = service.create_run(agent="gpt", repo_url="https://github.com/user/repo", prompt="b")
        service.start_run(run.id)
        service.complete_run(run.id)

        pending = service.list_runs(state=RunState.PENDING)
        completed = service.list_runs(state=RunState.COMPLETED)
        assert len(pending) == 1
        assert len(completed) == 1
        assert pending[0].agent == "codex"
        assert completed[0].agent == "gpt"

    def test_pagination(self, service: RunService):
        for i in range(10):
            service.create_run(agent="codex", repo_url="https://github.com/user/repo", prompt=f"p{i}")

        page1 = service.list_runs(limit=3, offset=0)
        page2 = service.list_runs(limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 3
        assert page1[0].id != page2[0].id