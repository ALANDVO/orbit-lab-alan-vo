"""Tests for the execution service."""
from __future__ import annotations

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.run import RunState
from app.services.execution import ExecutionService
from app.services.run import RunService


@pytest.fixture
def exec_service(db_session: Session) -> ExecutionService:
    return ExecutionService(db_session)


@pytest.fixture
def sample_run(db_session: Session, exec_service: ExecutionService):
    """Create a sample run via RunService."""
    run_service = RunService(db_session)
    return run_service.create_run(
        agent="codex",
        repo_url="https://github.com/test/repo",
        prompt="Fix the bug",
        branch="main",
    )


class TestExecutionService:
    def test_prepare_worktree_creates_path(self, sample_run, exec_service: ExecutionService):
        """Test that prepare_worktree allocates a worktree path."""
        path = exec_service.prepare_worktree(sample_run)
        assert path is not None
        assert path.startswith("/tmp/orbit-worktrees/")
        # The run should now have a worktree_path
        assert sample_run.worktree_path == path

    def test_prepare_worktree_idempotent(self, sample_run, exec_service: ExecutionService):
        """Calling prepare_worktree twice returns the same path."""
        path1 = exec_service.prepare_worktree(sample_run)
        path2 = exec_service.prepare_worktree(sample_run)
        assert path1 == path2

    @pytest_asyncio.fixture
    async def mock_process(self):
        """Mock asyncio subprocess."""
        process = AsyncMock()
        process.pid = 12345
        process.stdout = AsyncMock()
        process.stderr = AsyncMock()
        process.stdout.readline = AsyncMock(side_effect=[b"hello\n", b"world\n", b""])
        process.stderr.readline = AsyncMock(side_effect=[b""])
        process.wait = AsyncMock(return_value=0)
        return process

    @pytest.mark.asyncio
    async def test_execute_run_success(self, sample_run, exec_service: ExecutionService, mock_process):
        """Test successful execution of a run."""
        with patch("app.services.execution.asyncio.create_subprocess_exec", return_value=mock_process):
            output_lines = []
            def capture_output(stream: str, line: str):
                output_lines.append((stream, line))

            run = await exec_service.execute_run(sample_run.id, on_output=capture_output)

            assert run.state == RunState.COMPLETED
            assert run.exit_code == "0"
            assert run.duration_seconds is not None
            assert run.duration_seconds >= 0
            assert run.pid == "12345"
            assert len(output_lines) == 2
            assert output_lines[0] == ("stdout", "hello")
            assert output_lines[1] == ("stdout", "world")

    @pytest.mark.asyncio
    async def test_execute_run_failure(self, sample_run, exec_service: ExecutionService):
        """Test failed execution of a run."""
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=[b"error\n", b""])
        mock_process.stderr.readline = AsyncMock(side_effect=[b"stderr output\n", b""])
        mock_process.wait = AsyncMock(return_value=1)

        with patch("app.services.execution.asyncio.create_subprocess_exec", return_value=mock_process):
            run = await exec_service.execute_run(sample_run.id)

            assert run.state == RunState.FAILED
            assert run.exit_code == "1"
            assert run.error_message is not None
            assert "exited with code 1" in run.error_message.lower()

    def test_cancel_run(self, sample_run, exec_service: ExecutionService):
        """Test cancelling a running run."""
        # First set the run to RUNNING state with started_at
        sample_run.state = RunState.RUNNING
        sample_run.started_at = datetime.now(timezone.utc)
        db_session = exec_service._db
        db_session.commit()

        run = exec_service.cancel_run(sample_run.id)

        assert run.state == RunState.CANCELLED
        assert run.finished_at is not None
        assert run.duration_seconds is not None

    def test_cancel_non_running_raises(self, sample_run, exec_service: ExecutionService):
        """Test that cancelling a non-RUNNING run raises."""
        with pytest.raises(ValueError, match="Only RUNNING runs can be cancelled"):
            exec_service.cancel_run(sample_run.id)

    def test_execute_invalid_state_raises(self, sample_run, exec_service: ExecutionService):
        """Test that executing a non-PENDING run raises."""
        sample_run.state = RunState.COMPLETED
        db_session = exec_service._db
        db_session.commit()

        with pytest.raises(ValueError, match="Cannot transition from"):
            import asyncio
            asyncio.run(exec_service.execute_run(sample_run.id))

    def test_execute_not_found_raises(self, exec_service: ExecutionService):
        """Test that executing unknown run raises."""
        with pytest.raises(ValueError, match="Run not found"):
            import asyncio
            asyncio.run(exec_service.execute_run("nonexistent-id"))


class TestExecuteAPI:
    """Integration tests for the execute API endpoint."""
    
    def test_execute_endpoint_placeholder(self, client):
        """Placeholder for execute API test."""
        pass
