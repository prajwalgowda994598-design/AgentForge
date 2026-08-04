"""
AgentForge – Authentication Routes
=====================================
POST /api/v1/auth/register  – Create a new account
POST /api/v1/auth/token     – Login and receive a JWT bearer token

Both endpoints work without any prior authentication.
The returned token must be passed as  Authorization: Bearer <token>
on every endpoint that requires authentication (e.g. GET /research).

Swagger UI: click the 🔒 "Authorize" button, paste the token, and all
subsequent "Try it out" requests will include the header automatically.
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.backend.core.dependencies import get_db
from agentforge.backend.core.exceptions import AgentForgeError
from agentforge.backend.core.logging import get_logger
from agentforge.backend.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


# ── Request / response schemas (auth-specific, kept local) ────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")


class TokenRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
    response_model=dict,
)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Create a new user account. Returns the new user's ID and email."""
    from agentforge.backend.core.config import settings

    svc = AuthService(db)
    try:
        user = await svc.register(body.email, body.password)
    except AuthError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return {"user_id": str(user.id), "email": user.email, "message": "Account created."}


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Login — obtain a JWT bearer token",
)
async def login(body: TokenRequest, db: AsyncSession = Depends(get_db)):
    """
    Verify credentials and return a signed JWT.
    Use the token in the  Authorization: Bearer <token>  header.
    """
    from agentforge.backend.core.config import settings

    svc = AuthService(db)
    try:
        user = await svc.authenticate(body.email, body.password)
    except AuthError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    token = svc.create_access_token(str(user.id), user.email)
    logger.info("user_logged_in", email=body.email, user_id=str(user.id))

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
