"""Shared test fixtures for backend tests."""
from __future__ import annotations

import os

# Set test database before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "development"
os.environ["AUTH_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Override the engine in database module to use a shared in-memory DB
from app.core import database
database.engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
database.SessionLocal = sessionmaker(
    bind=database.engine, autoflush=False, autocommit=False, class_=Session
)

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# Create all tables once for the test session
Base.metadata.create_all(bind=database.engine)


@pytest.fixture
def db() -> Session:
    """Provide a clean database session for each test.

    Truncates all tables before each test so data does not leak between tests.
    """
    session = database.SessionLocal()
    # Clean any data from previous tests
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def db_session(db: Session) -> Session:
    """Alias for db fixture."""
    return db


@pytest.fixture
def client(db: Session) -> TestClient:
    """FastAPI TestClient with database dependency overridden."""

    def get_test_db() -> Session:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = get_test_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()