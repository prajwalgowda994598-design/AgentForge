"""
AgentForge – Audit Logging Service
=====================================
Writes immutable audit log entries to PostgreSQL.
Used by agents, the API, and the WebSocket manager.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.backend.core.logging import get_logger
from agentforge.backend.database.models import AuditLog

logger = get_logger(__name__)


class AuditService:
    """Writes structured audit events to the audit_logs table."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def log(
        self,
        event_type: str,
        actor: Optional[str] = None,
        session_id: Optional[UUID] = None,
        payload: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """
        Persist an audit event.  The session is NOT committed here;
        the caller (or the request lifecycle) commits.
        """
        entry = AuditLog(
            event_type=event_type,
            actor=actor,
            session_id=session_id,
            payload=payload or {},
            ip_address=ip_address,
        )
        self._db.add(entry)
        await self._db.flush()  # assign ID without committing

        logger.info(
            "audit_event",
            event_type=event_type,
            actor=actor,
            session_id=str(session_id) if session_id else None,
        )
        return entry
