"""Agent execution service.

Spawns isolated git worktrees, runs agent processes, and streams output via WebSocket.
"""
from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditAction, AuditLog
from app.models.run import Run, RunState, can_transition, is_terminal
from app.services.worktree import allocate_worktree_path, validate_worktree_path


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware in UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class ExecutionService:
    """Service for executing agent runs in isolated worktrees."""

    def __init__(self, db: Session):
        self._db = db
        self._running_processes: dict[str, asyncio.subprocess.Process] = {}

    def _configure_git(self, cwd: str) -> None:
        """Configure git user for commits in the given directory."""
        subprocess.run(["git", "config", "user.email", "test@orbit-lab.local"], cwd=cwd, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Orbit Lab Test"], cwd=cwd, capture_output=True)

    def prepare_worktree(self, run: Run) -> str:
        """Create and prepare the git worktree for a run."""
        # Allocate worktree path if not already set
        if not run.worktree_path:
            existing = set()
            run.worktree_path = allocate_worktree_path(run.id, run.repo_url, existing)
            self._db.commit()

        worktree_path = run.worktree_path
        if not validate_worktree_path(worktree_path):
            raise ValueError(f"Invalid worktree path: {worktree_path}")

        # Create the worktree directory
        Path(worktree_path).mkdir(parents=True, exist_ok=True)

        # Initialize git worktree
        repo_url = run.repo_url
        branch = run.branch or "main"

        # Check if it's a local path or remote URL
        if os.path.exists(repo_url) and os.path.isdir(repo_url):
            # Local repository - add worktree
            self._run_git(["worktree", "add", "-b", f"orbit-{run.id[:8]}", worktree_path, branch], cwd=repo_url)
        else:
            # Remote repository - clone then add worktree
            # For testing, create a local bare repo instead of cloning
            bare_path = Path(worktree_path).parent / f".bare-{run.id[:8]}"
            if not bare_path.exists():
                # Create a bare repo locally for testing
                self._run_git(["init", "--bare", str(bare_path)])
                # Add a dummy commit so worktree can be created
                temp_dir = Path(worktree_path).parent / f".temp-{run.id[:8]}"
                self._run_git(["clone", str(bare_path), str(temp_dir)])
                self._configure_git(str(temp_dir))
                (temp_dir / "README.md").write_text("# Test Repo\n")
                self._run_git(["add", "README.md"], cwd=str(temp_dir))
                self._run_git(["commit", "-m", "Initial commit"], cwd=str(temp_dir))
                # Push to bare repo using the correct branch name
                self._run_git(["push", "origin", "HEAD:main"], cwd=str(temp_dir))
                # Clean up temp dir
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            # Check if worktree already exists
            try:
                self._run_git(["worktree", "add", "-b", f"orbit-{run.id[:8]}", worktree_path, branch], cwd=str(bare_path))
            except RuntimeError as e:
                if "already exists" in str(e):
                    # Worktree already exists, try to use existing
                    pass
                else:
                    raise

        return worktree_path

    def _run_git(self, args: list[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        """Run a git command."""
        cmd = ["git"] + args
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{result.stderr}")
        return result

    async def execute_run(
        self,
        run_id: str,
        on_output: Optional[Callable[[str, str], None]] = None,
        actor: str = "system",
    ) -> Run:
        """Execute an agent run, streaming output via callback."""
        run = self._db.get(Run, run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")

        if not can_transition(run.state, RunState.RUNNING):
            raise ValueError(f"Cannot transition from {run.state} to RUNNING")

        # Prepare worktree
        worktree_path = self.prepare_worktree(run)

        # Transition to RUNNING
        run.state = RunState.RUNNING
        run.started_at = datetime.now(timezone.utc)
        run.pid = str(os.getpid())  # Will be updated with actual child PID
        self._audit(run_id, AuditAction.STATE_CHANGED, actor, f"Started execution in {worktree_path}")
        self._db.commit()

        # Build agent command
        cmd = self._build_agent_command(run.agent, run.prompt, worktree_path)

        # Start process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=worktree_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        run.pid = str(process.pid)
        self._running_processes[run_id] = process
        self._db.commit()

        # Stream output
        stdout_lines = []
        stderr_lines = []

        async def read_stream(stream: asyncio.StreamReader, stream_name: str):
            while True:
                line = await stream.readline()
                if not line:
                    break
                decoded = line.decode(errors="replace").rstrip()
                if stream_name == "stdout":
                    stdout_lines.append(decoded)
                else:
                    stderr_lines.append(decoded)
                if on_output:
                    on_output(stream_name, decoded)

        await asyncio.gather(
            read_stream(process.stdout, "stdout"),
            read_stream(process.stderr, "stderr"),
        )

        # Wait for completion
        exit_code = await process.wait()

        # Calculate duration
        finished_at = datetime.now(timezone.utc)
        started_at = _ensure_utc(run.started_at) if run.started_at else finished_at
        duration = (finished_at - started_at).total_seconds()

        # Update run state
        if exit_code == 0:
            run.state = RunState.COMPLETED
            action = AuditAction.STATE_CHANGED
        else:
            run.state = RunState.FAILED
            run.error_message = f"Agent exited with code {exit_code}"
            action = AuditAction.STATE_CHANGED

        run.finished_at = finished_at
        run.exit_code = str(exit_code)
        run.duration_seconds = duration
        run.pid = str(process.pid)

        detail = f"Exited with code {exit_code} in {duration:.1f}s"
        self._audit(run_id, action, actor, detail)
        self._db.commit()

        # Cleanup
        self._running_processes.pop(run_id, None)

        return run

    def _build_agent_command(self, agent: str, prompt: str, worktree_path: str) -> list[str]:
        """Build the command to run the specified agent."""
        # For now, use a simple echo command as placeholder
        # In production, this would invoke the actual agent CLI
        return ["sh", "-c", f'echo "Running {agent} with prompt: {prompt}" && sleep 2 && echo "Done"']

    def cancel_run(self, run_id: str, actor: str = "system") -> Run:
        """Cancel a running execution."""
        run = self._db.get(Run, run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")

        if run.state != RunState.RUNNING:
            raise ValueError(f"Only RUNNING runs can be cancelled, current state: {run.state}")

        # Kill the process if running
        process = self._running_processes.get(run_id)
        if process and process.pid:
            try:
                os.kill(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

        run.state = RunState.CANCELLED
        run.finished_at = datetime.now(timezone.utc)
        started_at = _ensure_utc(run.started_at) if run.started_at else run.finished_at
        run.duration_seconds = (run.finished_at - started_at).total_seconds()
        self._audit(run_id, AuditAction.CANCELLED, actor, "Cancelled by user")
        self._db.commit()

        self._running_processes.pop(run_id, None)
        return run

    def _audit(self, run_id: str, action: AuditAction, actor: str, detail: Optional[str] = None) -> None:
        """Record an audit log entry."""
        entry = AuditLog(
            id=str(uuid.uuid4()),
            run_id=run_id,
            action=action.value,
            actor=actor,
            detail=detail,
        )
        self._db.add(entry)


def get_execution_service(db: Session) -> ExecutionService:
    """Dependency that provides an ExecutionService instance."""
    return ExecutionService(db)
