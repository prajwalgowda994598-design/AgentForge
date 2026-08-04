"""
AgentForge – FastAPI Dependencies
===================================
Provides injectable dependencies used across all API routes:
  • Database session
  • Redis client
  • Current authenticated user
  • Settings
"""

from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.backend.core.config import settings
from agentforge.backend.core.logging import get_logger
from agentforge.backend.database.session import AsyncSessionLocal
from agentforge.backend.services.redis_service import get_redis_client

logger = get_logger(__name__)


# ── Database ──────────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async SQLAlchemy session for the duration of a request.
    The session is committed on success and rolled back on exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Redis ─────────────────────────────────────────────────────────────────────

async def get_redis():
    """Return the shared Redis client pool."""
    return await get_redis_client()


# ── Authentication ────────────────────────────────────────────────────────────

async def get_current_user(
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """
    Validate the Bearer JWT token from the Authorization header.
    Returns the decoded token payload (sub, email, roles).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if authorization is None or not authorization.startswith("Bearer "):
        raise credentials_exception

    token = authorization.split(" ", 1)[1]

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError as exc:
        logger.warning("jwt_validation_failed", error=str(exc))
        raise credentials_exception

    return {"user_id": user_id, "email": payload.get("email"), "roles": payload.get("roles", [])}


async def get_optional_user(
    authorization: Optional[str] = Header(default=None),
) -> Optional[dict]:
    """Same as get_current_user but returns None instead of raising 401."""
    try:
        return await get_current_user(authorization=authorization)
    except HTTPException:
        return None


# ── Settings ──────────────────────────────────────────────────────────────────

def get_app_settings():
    """Inject application settings as a dependency."""
    return settings
