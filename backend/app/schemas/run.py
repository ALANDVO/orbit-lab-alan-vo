"""Pydantic schemas for API request/response validation."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.run import RunState


class RunCreate(BaseModel):
    """Request to create a new agent run."""

    model_config = ConfigDict(extra="forbid")

    agent: str = Field(..., min_length=1, max_length=64, description="Agent identifier (e.g. 'codex', 'claude-code')")
    repo_url: str = Field(..., min_length=1, max_length=512, description="Git repository URL or local path")
    prompt: str = Field(..., min_length=1, max_length=16384, description="Prompt sent to the agent")
    branch: Optional[str] = Field(default=None, max_length=128, description="Git branch to check out")


class RunRead(BaseModel):
    """Public representation of a run."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    agent: str
    repo_url: str
    branch: Optional[str]
    prompt: str
    worktree_path: str
    state: RunState
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    updated_at: datetime


class AuditEntryRead(BaseModel):
    """Public representation of an audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    action: str
    actor: str
    detail: Optional[str] = None
    timestamp: datetime


class RunDetail(BaseModel):
    """Detailed run view including audit history."""

    model_config = ConfigDict(from_attributes=True)

    run: RunRead
    audit: list[AuditEntryRead]


class RunListResponse(BaseModel):
    """Paginated list of runs."""

    model_config = ConfigDict(from_attributes=True)

    runs: list[RunRead]
    limit: int
    offset: int
    total: int


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str