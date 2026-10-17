"""Run lifecycle management service.

Implements the state machine for agent runs: enforces valid state transitions,
records audit log entries for every mutation, and coordinates with the
worktree allocation engine.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditAction, AuditLog
from app.models.run import Run, RunState, can_transition, is_terminal
from app.services.worktree import allocate_worktree_path


class RunService:
    """Service for managing agent runs and their lifecycle."""

    def __init__(self, db: Session):
        self._db = db

    # --- Creation ---

    def create_run(
        self,
        agent: str,
        repo_url: str,
        prompt: str,
        branch: Optional[str] = None,
        actor: str = "system",
    ) -> Run:
        """Create a new agent run in PENDING state.

        Allocates a deterministic worktree path and records an audit entry.
        """
        run_id = str(uuid.uuid4())
        # Collect existing worktree paths to avoid collisions
        existing_paths = self._existing_worktree_paths()

        worktree_path = allocate_worktree_path(run_id, repo_url, existing=existing_paths)

        run = Run(
            id=run_id,
            agent=agent,
            repo_url=repo_url,
            branch=branch,
            prompt=prompt,
            worktree_path=worktree_path,
            state=RunState.PENDING,
        )
        self._db.add(run)
        self._db.flush()  # Ensure run is in DB for audit FK

        self._audit(
            run_id=run_id,
            action=AuditAction.CREATED,
            actor=actor,
            detail=f"agent={agent} repo={repo_url} branch={branch or 'default'}",
        )

        self._db.commit()
        self._db.refresh(run)
        return run

    # --- Queries ---

    def get_run(self, run_id: str) -> Optional[Run]:
        """Fetch a single run by ID."""
        return self._db.get(Run, run_id)

    def list_runs(
        self,
        state: Optional[RunState] = None,
        agent: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Run]:
        """List runs with optional filtering and pagination."""
        query = select(Run).order_by(Run.created_at.desc())

        if state is not None:
            query = query.where(Run.state == state)
        if agent is not None:
            query = query.where(Run.agent == agent)

        query = query.offset(offset).limit(limit)
        return list(self._db.scalars(query))

    def count_runs(
        self,
        state: Optional[RunState] = None,
        agent: Optional[str] = None,
    ) -> int:
        """Count runs matching the given filters."""
        count_query = select(func.count()).select_from(Run)
        if state is not None:
            count_query = count_query.where(Run.state == state)
        if agent is not None:
            count_query = count_query.where(Run.agent == agent)
        return self._db.scalar(count_query)  # noqa: E501

    # --- Lifecycle ---

    def start_run(self, run_id: str, actor: str = "system") -> Run:
        """Transition a run from PENDING to RUNNING."""
        run = self.get_run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        if not can_transition(run.state, RunState.RUNNING):
            raise InvalidStateTransition(run_id, run.state, RunState.RUNNING)

        run.state = RunState.RUNNING
        run.started_at = datetime.now(timezone.utc)
        self._record_state_change(run, run.state, actor)
        self._db.commit()
        self._db.refresh(run)
        return run

    def complete_run(self, run_id: str, actor: str = "system") -> Run:
        """Transition a RUNNING run to COMPLETED."""
        return self._transition(run_id, RunState.COMPLETED, actor)

    def fail_run(self, run_id: str, error_message: str, actor: str = "system") -> Run:
        """Transition a run to FAILED with an error message."""
        run = self._transition(run_id, RunState.FAILED, actor)
        run.error_message = error_message
        self._db.commit()
        self._db.refresh(run)
        return run

    def cancel_run(self, run_id: str, actor: str = "system") -> Run:
        """Cancel a run. Only PENDING or RUNNING runs can be cancelled."""
        run = self.get_run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        if is_terminal(run.state):
            raise InvalidStateTransition(run_id, run.state, RunState.CANCELLED)

        if not can_transition(run.state, RunState.CANCELLED):
            raise InvalidStateTransition(run_id, run.state, RunState.CANCELLED)

        run.state = RunState.CANCELLED
        run.finished_at = datetime.now(timezone.utc)
        self._audit(
            run_id=run_id,
            action=AuditAction.CANCELLED,
            actor=actor,
            detail=f"cancelled from {run.state.value}",
        )
        self._db.commit()
        self._db.refresh(run)
        return run

    def delete_run(self, run_id: str, actor: str = "system") -> None:
        """Delete a run (only terminal runs can be deleted)."""
        run = self.get_run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        if not is_terminal(run.state):
            raise InvalidStateTransition(run_id, run.state, None)  # type: ignore[arg-type]

        # Record deletion audit BEFORE deleting (run_id is preserved in AuditLog FK)
        self._audit(
            run_id=run_id,
            action=AuditAction.DELETED,
            actor=actor,
            detail=f"deleted run in state {run.state.value}",
        )
        self._db.delete(run)
        self._db.commit()

    # --- Internals ---

    def _transition(self, run_id: str, target: RunState, actor: str) -> Run:
        run = self.get_run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        if not can_transition(run.state, target):
            raise InvalidStateTransition(run_id, run.state, target)

        run.state = target
        run.finished_at = datetime.now(timezone.utc)
        self._record_state_change(run, target, actor)
        self._db.commit()
        self._db.refresh(run)
        return run

    def _record_state_change(self, run: Run, new_state: RunState, actor: str) -> None:
        self._audit(
            run_id=run.id,
            action=AuditAction.STATE_CHANGED,
            actor=actor,
            detail=f"state -> {new_state.value}",
        )

    def _audit(self, run_id: str, action: AuditAction, actor: str, detail: Optional[str] = None) -> None:
        entry = AuditLog(
            id=str(uuid.uuid4()),
            run_id=run_id,
            action=action,
            actor=actor,
            detail=detail,
        )
        self._db.add(entry)

    def _existing_worktree_paths(self) -> set[str]:
        """Fetch set of worktree paths already in use."""
        result = self._db.scalars(select(Run.worktree_path))
        return set(result)


class RunNotFoundError(Exception):
    """Raised when a run ID does not exist."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        super().__init__(f"Run not found: {run_id}")


class InvalidStateTransition(Exception):
    """Raised when a state transition is not allowed."""

    def __init__(self, run_id: str, current: RunState, target: RunState | None):
        self.run_id = run_id
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid state transition for run {run_id}: {current.value} -> {target.value if target else 'none'}"
        )