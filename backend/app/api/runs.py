"""API endpoints for agent run management."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
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
from app.services.execution import ExecutionService

router = APIRouter(prefix="/api/runs", tags=["runs"])


def get_service(db: Session = Depends(get_db)) -> RunService:
    """Dependency that provides a RunService instance."""
    return RunService(db)


def get_exec_service() -> ExecutionService:
    """Dependency that provides an ExecutionService instance."""
    db = SessionLocal()
    try:
        return ExecutionService(db)
    finally:
        db.close()


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


# Execution endpoints

@router.post("/{run_id}/execute", response_model=RunRead)
async def execute_run(
    run_id: str,
    exec_service: ExecutionService = Depends(get_exec_service),
):
    """Execute an agent run (spawns worktree, runs agent, updates state)."""
    try:
        run = await exec_service.execute_run(run_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
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


@router.websocket("/{run_id}/stream")
async def stream_run(
    websocket: WebSocket,
    run_id: str,
):
    """WebSocket endpoint for streaming run output."""
    db = SessionLocal()
    try:
        await websocket.accept()
        
        exec_service = ExecutionService(db)
        
        async def on_output(stream: str, line: str):
            await websocket.send_json({
                "stream": stream,
                "line": line,
            })
        
        await exec_service.execute_run(run_id, on_output=on_output)
        await websocket.send_json({"event": "completed"})
    except ValueError as e:
        await websocket.send_json({"event": "error", "detail": str(e)})
    except RunNotFoundError:
        await websocket.send_json({"event": "error", "detail": f"Run not found: {run_id}"})
    except InvalidStateTransition as e:
        await websocket.send_json({"event": "error", "detail": str(e)})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"event": "error", "detail": f"Execution failed: {str(e)}"})
    finally:
        db.close()
        await websocket.close()
