"""Orbit Lab — AI orchestrator for a fleet of coding agents.

FastAPI application factory with SQLite persistence, agent run management,
and an audit-logged state machine for run lifecycles.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.models.audit import AuditLog  # noqa: F401  (import for model registration)
from app.models.run import Run  # noqa: F401  (import for model registration)

__version__ = "1.0.0"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Ensure tables exist before first request
    init_db()

    app = FastAPI(
        title="Orbit Lab",
        description="AI orchestrator for a fleet of coding agents.",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS (for development; production should restrict)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    from app.api.runs import router as run_router

    app.include_router(run_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "orbit-lab", "version": __version__}

    @app.get("/")
    def root() -> dict[str, str]:
        return {"name": "orbit-lab", "version": __version__, "docs": "/docs"}

    return app


# Module-level app instance for uvicorn
app = create_app()