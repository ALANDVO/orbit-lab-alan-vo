"""Run state enumeration and Run ORM model."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class RunState(str, enum.Enum):
    """Lifecycle states for an agent run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Valid state transitions: current -> set of allowed next states
VALID_TRANSITIONS: dict[RunState, frozenset[RunState]] = {
    RunState.PENDING: frozenset({RunState.RUNNING, RunState.CANCELLED, RunState.FAILED}),
    RunState.RUNNING: frozenset({RunState.COMPLETED, RunState.FAILED, RunState.CANCELLED}),
    RunState.COMPLETED: frozenset(),
    RunState.FAILED: frozenset(),
    RunState.CANCELLED: frozenset(),
}


class Run(Base):
    """An agent run — a single coding-agent invocation on a repository."""

    __tablename__ = "runs"

    id = Column(String(36), primary_key=True, index=True)
    agent = Column(String(64), nullable=False, index=True)
    repo_url = Column(String(512), nullable=False)
    branch = Column(String(128), nullable=True)
    prompt = Column(Text, nullable=False)
    worktree_path = Column(String(512), nullable=False, unique=True)
    state = Column(Enum(RunState), nullable=False, default=RunState.PENDING, index=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    audit_entries = relationship("AuditLog", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Run id={self.id} agent={self.agent} state={self.state}>"


def can_transition(current: RunState, target: RunState) -> bool:
    """Check whether a state transition is valid."""
    if current == target:
        return False
    return target in VALID_TRANSITIONS.get(current, frozenset())


def is_terminal(state: RunState) -> bool:
    """Whether a state is terminal (no further transitions)."""
    return state in (RunState.COMPLETED, RunState.FAILED, RunState.CANCELLED)