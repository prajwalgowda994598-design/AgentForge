"""
AgentForge – Authentication Service
=====================================
Handles password hashing, JWT creation, and JWT decoding.
Kept deliberately thin — all state lives in the database and the token.

Usage:
    service = AuthService(db_session)
    user    = await service.register("alice@example.com", "s3cr3t!")
    token   = service.create_access_token(str(user.id), user.email)
    payload = AuthService.decode_token(token)   # → {"sub": ..., "email": ...}
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.backend.core.config import settings
from agentforge.backend.core.exceptions import AgentForgeError
from agentforge.backend.core.logging import get_logger
from agentforge.backend.database.models import User

logger = get_logger(__name__)


class AuthError(AgentForgeError):
    """Raised for authentication / authorisation failures."""

    def __init__(self, reason: str, status_code: int = 401):
        from fastapi import status as http_status
        super().__init__(
            message=reason,
            code="AUTH_ERROR",
            status_code=status_code,
        )


class AuthService:
    def __init__(self, db: AsyncSession):
        self._db = db

    # ── Password helpers ──────────────────────────────────────────────────────

    @staticmethod
    def hash_password(plain: str) -> str:
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())

    # ── JWT helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def create_access_token(user_id: str, email: str) -> str:
        """Return a signed JWT valid for ACCESS_TOKEN_EXPIRE_MINUTES minutes."""
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        payload = {"sub": user_id, "email": email, "exp": expire}
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and verify a JWT. Raises AuthError on failure."""
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError as exc:
            raise AuthError(f"Invalid or expired token: {exc}") from exc

    # ── Database operations ───────────────────────────────────────────────────

    async def register(self, email: str, password: str) -> User:
        """Create a new user. Raises AuthError(409) if email is taken."""
        existing = await self._db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise AuthError(f"Email '{email}' is already registered.", status_code=409)

        user = User(email=email, hashed_password=self.hash_password(password))
        self._db.add(user)
        await self._db.flush()   # populate user.id without committing
        logger.info("user_registered", email=email, user_id=str(user.id))
        return user

    async def authenticate(self, email: str, password: str) -> User:
        """Verify credentials. Raises AuthError(401) on failure."""
        result = await self._db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not self.verify_password(password, user.hashed_password):
            raise AuthError("Incorrect email or password.")
        if not user.is_active:
            raise AuthError("Account is disabled.")
        return user
