"""
AgentForge – Custom Exceptions & Handlers
==========================================
Centralised exception hierarchy used across the entire backend.
FastAPI exception handlers are registered in main.py.
"""

from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse


# ── Domain Exceptions ─────────────────────────────────────────────────────────

class AgentForgeError(Exception):
    """Base error for all AgentForge domain exceptions."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class AgentExecutionError(AgentForgeError):
    """Raised when an agent fails to produce a valid result."""

    def __init__(self, agent_name: str, reason: str, **kwargs):
        super().__init__(
            message=f"Agent '{agent_name}' failed: {reason}",
            code="AGENT_EXECUTION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"agent": agent_name, "reason": reason},
        )


class VectorStoreError(AgentForgeError):
    """Raised when FAISS retrieval or indexing fails."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"VectorStore error: {reason}",
            code="VECTOR_STORE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class GraphDatabaseError(AgentForgeError):
    """Raised when Neo4j operations fail."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Graph database error: {reason}",
            code="GRAPH_DB_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class ResearchIterationLimitError(AgentForgeError):
    """Raised when the critic forces too many research cycles."""

    def __init__(self, max_iterations: int):
        super().__init__(
            message=f"Exceeded maximum research iterations ({max_iterations})",
            code="ITERATION_LIMIT_EXCEEDED",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"max_iterations": max_iterations},
        )


class NotFoundError(AgentForgeError):
    """Resource not found."""

    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} '{identifier}' not found",
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ValidationError(AgentForgeError):
    """Input validation failed."""

    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"Validation failed for '{field}': {reason}",
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


# ── FastAPI Exception Handlers ────────────────────────────────────────────────

async def agentforge_exception_handler(
    request: Request, exc: AgentForgeError
) -> JSONResponse:
    """Convert AgentForgeError subclasses into structured JSON responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "path": str(request.url),
            }
        },
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all handler for unexpected exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "UNEXPECTED_ERROR",
                "message": "An unexpected error occurred. Please try again.",
                "path": str(request.url),
            }
        },
    )
