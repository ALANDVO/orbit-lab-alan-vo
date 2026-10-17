"""API endpoints for agent run management."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.run import Run, RunState
from app.schemas.run import (
    RunCreate,
    RunDetail,
    RunListResponse,
    RunRead,
)
from app.services.run import (
    InvalidStateTransition,
    RunNotFoundError,
    RunService,
)

router = APIRouter(prefix="/api/runs", tags=["runs"])


def get_service(db: Session = Depends(get_db)) -> RunService:
    """Dependency that provides a RunService instance."""
    return RunService(db)


@router.post("/", response_model=RunRead, status_code=status.HTTP_201_CREATED)
def create_run(payload: RunCreate, service: RunService = Depends(get_service)):
    """Create a new agent run in PENDING state."""
    run = service.create_run(
        agent=payload.agent,
        repo_url=payload.repo_url,
        prompt=payload.prompt,
        branch=payload.branch,
    )
    return run


@router.get("/", response_model=RunListResponse)
def list_runs(
    state: Optional[RunState] = Query(default=None, description="Filter by run state"),
    agent: Optional[str] = Query(default=None, description="Filter by agent"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: RunService = Depends(get_service),
):
    """List runs with optional filtering and pagination."""
    runs = service.list_runs(state=state, agent=agent, limit=limit, offset=offset)
    total = service.count_runs(state=state, agent=agent)
    return RunListResponse(runs=runs, limit=limit, offset=offset, total=total)


@router.get("/{run_id}", response_model=RunDetail)
def get_run(run_id: str, service: RunService = Depends(get_service)):
    """Get a single run with its audit history."""
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )
    return RunDetail(run=run, audit=run.audit_entries)


@router.delete("/{run_id}", response_model=RunRead)
def cancel_run(run_id: str, service: RunService = Depends(get_service)):
    """Cancel a pending or running run."""
    try:
        run = service.cancel_run(run_id)
    except RunNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )
    except InvalidStateTransition as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    return run


@router.post("/{run_id}/start", response_model=RunRead)
def start_run(run_id: str, service: RunService = Depends(get_service)):
    """Transition a run to RUNNING state."""
    try:
        run = service.start_run(run_id)
    except RunNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )
    except InvalidStateTransition as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    return run


@router.post("/{run_id}/complete", response_model=RunRead)
def complete_run(run_id: str, service: RunService = Depends(get_service)):
    """Transition a run to COMPLETED state."""
    try:
        run = service.complete_run(run_id)
    except RunNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )
    except InvalidStateTransition as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    return run


@router.post("/{run_id}/fail", response_model=RunRead)
def fail_run(
    run_id: str,
    error_message: str = Query(default="...", max_length=1024),
    service: RunService = Depends(get_service),
):
    """Transition a run to FAILED state with an error message."""
    try:
        run = service.fail_run(run_id, error_message)
    except RunNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )
    except InvalidStateTransition as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    return run