"""
AgentForge – ORM Models
=========================
Six tables drive the persistence layer:

  users              – registered accounts (email + bcrypt password hash)
  research_sessions  – one row per user query / conversation
  agent_runs         – individual agent execution records (child of session)
  audit_logs         – immutable event log for compliance
  documents          – ingested knowledge-base chunks
  knowledge_nodes    – Neo4j sync mirror (metadata only, edges live in Neo4j)

NOTE: Uses sqlalchemy.types.Uuid (SQLAlchemy 2.0+) which is dialect-agnostic
      — works with both SQLite (local dev) and PostgreSQL (production).
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,          # dialect-agnostic UUID — works for SQLite + PostgreSQL
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentforge.backend.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── User ───────────────────────────────────────────────────────────────────────

class User(Base):
    """Registered user account. Password stored as a bcrypt hash."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<User email={self.email} active={self.is_active}>"


# ── Research Session ───────────────────────────────────────────────────────────

class ResearchSession(Base):
    """Represents a single research request from a user."""

    __tablename__ = "research_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # pending | running | completed | failed
    final_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    critic_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    iterations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    agent_runs: Mapped[List["AgentRun"]] = relationship(
        "AgentRun", back_populates="session", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ResearchSession id={self.id} status={self.status}>"


# ── Agent Run ──────────────────────────────────────────────────────────────────

class AgentRun(Base):
    """Records a single agent execution within a research session."""

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    session: Mapped["ResearchSession"] = relationship("ResearchSession", back_populates="agent_runs")

    def __repr__(self) -> str:
        return f"<AgentRun agent={self.agent_name} status={self.status}>"


# ── Audit Log ──────────────────────────────────────────────────────────────────

class AuditLog(Base):
    """Immutable event log for compliance and debugging."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research_sessions.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    # Relationships
    session: Mapped[Optional["ResearchSession"]] = relationship(
        "ResearchSession", back_populates="audit_logs"
    )

    def __repr__(self) -> str:
        return f"<AuditLog event={self.event_type} at={self.created_at}>"


# ── Document (Knowledge Base Chunk) ───────────────────────────────────────────

class Document(Base):
    """A chunk of ingested text stored in the knowledge base."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(1000), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_total: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    faiss_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSON, nullable=True
    )
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("content_hash", "chunk_index", name="uq_document_chunk"),
    )

    def __repr__(self) -> str:
        return f"<Document title={self.title[:40]} chunk={self.chunk_index}/{self.chunk_total}>"


# ── Knowledge Node (Neo4j mirror) ─────────────────────────────────────────────

class KnowledgeNode(Base):
    """
    Lightweight mirror of Neo4j nodes so SQL queries can reference them.
    Full relationship data lives in Neo4j; only core metadata is here.
    """

    __tablename__ = "knowledge_nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    neo4j_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    node_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    properties: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<KnowledgeNode type={self.node_type} label={self.label[:40]}>"
