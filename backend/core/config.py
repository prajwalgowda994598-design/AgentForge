"""
AgentForge – Core Configuration
================================
All settings loaded from environment variables via Pydantic BaseSettings.

LLM Provider:
  LLM_PROVIDER=openrouter  (default) → uses OpenRouter free tier
  LLM_PROVIDER=openai               → uses OpenAI directly

LOCAL_DEV=true  (default) → SQLite + FakeRedis + Neo4j disabled
LOCAL_DEV=false           → Full production stack (PostgreSQL + Redis + Neo4j)
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    APP_NAME: str = "AgentForge"
    APP_VERSION: str = "1.0.0"
    APP_DEBUG: bool = True       # renamed from DEBUG to avoid Windows env var collision
    ENVIRONMENT: str = "development"

    # ── Local dev flag — set false only when running with full Docker stack ────
    LOCAL_DEV: bool = True

    # ── API Server ─────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    API_PREFIX: str = "/api/v1"

    # ── Security ───────────────────────────────────────────────────────────────
    SECRET_KEY: str = "dev-secret-key-change-in-production-please"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    # Store as a raw comma-separated string; parsed into a list by the property below
    CORS_ORIGINS_STR: str = "http://localhost:3000,http://localhost:5173"

    # ── LLM Provider ───────────────────────────────────────────────────────────
    # Set LLM_PROVIDER=openai to use OpenAI directly instead of OpenRouter
    LLM_PROVIDER: str = "openrouter"

    # ── OpenRouter (default — free tier, no credit card required) ──────────────
    # Sign up at https://openrouter.ai  →  Keys  →  Create Key
    OPENROUTER_API_KEY: str = Field(default="", description="OpenRouter API key (sk-or-v1-...)")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    # Free models on OpenRouter — verified working Aug 2026
    # Run python find_working_models.py to refresh this list
    # Primary model — override via OPENROUTER_MODEL env var on Render
    OPENROUTER_MODEL: str = "google/gemma-4-26b-a4b-it:free"
    # Comma-separated fallback chain tried in order when primary times out / errors
    OPENROUTER_FALLBACK_MODELS: str = (
        "nvidia/nemotron-3-super-120b-a12b:free,"
        "nvidia/nemotron-3-ultra-550b-a55b:free,"
        "openai/gpt-oss-20b:free"
    )
    OPENROUTER_SITE_URL: str = "http://localhost:3000"   # shown in OpenRouter dashboard
    OPENROUTER_SITE_NAME: str = "AgentForge"

    # ── OpenAI (used when LLM_PROVIDER=openai) ─────────────────────────────────
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key (only if LLM_PROVIDER=openai)")
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TEMPERATURE: float = 0.1
    OPENAI_MAX_TOKENS: int = 4096

    # ── Embeddings ─────────────────────────────────────────────────────────────
    # OpenRouter does NOT support embeddings — always uses OpenAI for FAISS.
    # If you have no OpenAI key, set EMBEDDING_PROVIDER=local to use a free
    # sentence-transformers model (slower but zero-cost).
    EMBEDDING_PROVIDER: str = "openai"          # openai | local
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ── Computed helpers (read-only properties) ────────────────────────────────
    @property
    def LLM_API_KEY(self) -> str:
        """Return the active LLM API key based on LLM_PROVIDER."""
        if self.LLM_PROVIDER == "openai":
            return self.OPENAI_API_KEY
        return self.OPENROUTER_API_KEY

    @property
    def LLM_BASE_URL(self) -> str:
        """Return the active LLM base URL based on LLM_PROVIDER."""
        if self.LLM_PROVIDER == "openai":
            return self.OPENAI_BASE_URL
        return self.OPENROUTER_BASE_URL

    @property
    def LLM_MODEL(self) -> str:
        """Return the active model name based on LLM_PROVIDER."""
        if self.LLM_PROVIDER == "openai":
            return self.OPENAI_MODEL
        return self.OPENROUTER_MODEL

    # ── PostgreSQL (only used when LOCAL_DEV=false) ────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "agentforge"
    POSTGRES_USER: str = "agentforge"
    POSTGRES_PASSWORD: str = ""

    # ── Redis (only used when LOCAL_DEV=false) ─────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_TTL: int = 3600

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ── Neo4j (only used when LOCAL_DEV=false) ─────────────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # ── FAISS / Vector Store ───────────────────────────────────────────────────
    FAISS_INDEX_PATH: str = "./vectorstore/faiss_index"
    # Dimension is set by the embedding model:
    #   openai  → 1536  (text-embedding-3-small)
    #   local   → 384   (all-MiniLM-L6-v2)
    FAISS_DIMENSION: int = 384
    FAISS_TOP_K: int = 5

    # ── Agent Orchestration ────────────────────────────────────────────────────
    CRITIC_PASS_THRESHOLD: float = 0.7
    MAX_RESEARCH_ITERATIONS: int = 3
    AGENT_TIMEOUT_SECONDS: int = 300  # 4 fallback models × 55s each + retry headroom

    # ── Logging ────────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Parse the comma-separated CORS_ORIGINS_STR into a list."""
        raw = self.CORS_ORIGINS_STR.split("#")[0].strip()  # strip inline comments
        if not raw:
            return ["http://localhost:3000", "http://localhost:5173"]
        return [o.strip() for o in raw.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()


settings = get_settings()
