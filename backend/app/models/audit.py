"""AuditLog ORM model for tracking all state mutations."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditAction(str, enum.Enum):
    """Actions recorded in the audit log."""

    CREATED = "created"
    STATE_CHANGED = "state_changed"
    CANCELLED = "cancelled"
    DELETED = "deleted"


class AuditLog(Base):
    """Audit trail entry for run state mutations."""

    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, index=True)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False, index=True)
    action = Column(Enum(AuditAction), nullable=False, index=True)
    actor = Column(String(64), nullable=False, default="system")
    detail = Column(Text, nullable=True)

    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    run = relationship("Run", back_populates="audit_entries")

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} run_id={self.run_id} action={self.action}>"