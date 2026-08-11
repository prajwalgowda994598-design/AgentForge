"""
AgentForge – Pydantic Schemas
================================
All API request/response validation models live here.
These are separate from ORM models to maintain clean layer boundaries.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Shared ─────────────────────────────────────────────────────────────────────

class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: Optional[datetime] = None


# ── Research Query ─────────────────────────────────────────────────────────────

class ResearchQueryRequest(BaseModel):
    """Incoming research query from the user."""

    query: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        examples=["What are the latest advances in quantum computing?"],
    )
    context: Optional[str] = Field(
        default=None,
        description="Optional additional context or constraints for the query",
        max_length=4000,
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of FAISS results to retrieve")
    session_id: Optional[uuid.UUID] = Field(
        default=None, description="Provide to continue an existing conversation"
    )

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace")
        return v.strip()


class ResearchQueryResponse(BaseModel):
    """Final response returned after the full agent pipeline completes."""

    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    query: str
    final_answer: str
    critic_score: float
    iterations: int
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    execution_time_ms: int
    status: str


# ── Agent Status ───────────────────────────────────────────────────────────────

class AgentStatusUpdate(BaseModel):
    """Broadcasted over WebSocket to show live agent progress."""

    session_id: str
    agent_name: str
    status: str  # starting | running | completed | failed
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Research Session ───────────────────────────────────────────────────────────

class ResearchSessionSchema(TimestampMixin):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[str]
    query: str
    status: str
    final_answer: Optional[str]
    critic_score: Optional[float]
    iterations: int
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata_")


# ── Agent Run ──────────────────────────────────────────────────────────────────

class AgentRunSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    agent_name: str
    status: str
    execution_time_ms: Optional[int]
    tokens_used: Optional[int]
    error_message: Optional[str]
    created_at: datetime


# ── Document Ingestion ─────────────────────────────────────────────────────────

class DocumentIngestRequest(BaseModel):
    """Upload a text document to the knowledge base."""

    title: str = Field(..., max_length=500)
    source: str = Field(..., max_length=1000, description="URL or filename")
    content: str = Field(..., min_length=50, max_length=100_000)
    metadata: Optional[Dict[str, Any]] = None


class DocumentIngestResponse(BaseModel):
    document_id: Optional[uuid.UUID]
    chunks_created: int
    faiss_indexed: bool
    message: str


# ── Knowledge Graph ────────────────────────────────────────────────────────────

class KnowledgeNodeCreate(BaseModel):
    node_type: str = Field(..., max_length=100)
    label: str = Field(..., max_length=500)
    properties: Optional[Dict[str, Any]] = None


class KnowledgeEdgeCreate(BaseModel):
    source_id: str
    target_id: str
    relationship: str = Field(..., max_length=100)
    properties: Optional[Dict[str, Any]] = None


# ── Health & System ────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    services: Dict[str, str]  # service_name → "ok" | "degraded" | "down"


# ── Streaming chunks (for SSE / WS) ───────────────────────────────────────────

class StreamChunk(BaseModel):
    """A single incremental streaming chunk sent to the frontend."""

    chunk_type: str  # text | agent_status | error | done
    content: Optional[str] = None
    agent_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
