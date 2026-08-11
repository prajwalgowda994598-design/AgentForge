"""
AgentForge – Base Agent
=========================
All five agents inherit from BaseAgent.

LLM routing:
  LLM_PROVIDER=openrouter (default)
    → ChatOpenAI pointed at https://openrouter.ai/api/v1
    → model: nvidia/nemotron-3-super-120b-a12b:free (or any free OpenRouter model)
    → X-Title / HTTP-Referer headers injected so the call shows in your
      OpenRouter dashboard

  LLM_PROVIDER=openai
    → ChatOpenAI pointed at https://api.openai.com/v1 as usual

LangChain's ChatOpenAI accepts base_url + api_key, making this a true
drop-in swap with zero additional dependencies.

Thread-safety note:
  The pipeline runs inside asyncio.run() in a dedicated ThreadPoolExecutor thread
  (see research.py _run_pipeline_in_thread).  The OpenAI SDK v2 uses
  asyncio.to_thread() / loop.run_in_executor(None, ...) on the first HTTP call to
  detect the platform.  When the event loop created by asyncio.run() is torn down,
  Python shuts down the *default* ThreadPoolExecutor first, which causes:
    RuntimeError: cannot schedule new futures after interpreter shutdown
  Fix: pass a pre-created httpx.AsyncClient with its own connection pool to
  ChatOpenAI via http_async_client=.  This bypasses the SDK's internal
  platform-detection thread entirely.
"""

import asyncio
import concurrent.futures
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx
from langchain_openai import ChatOpenAI
from openai import APIConnectionError, APITimeoutError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from agentforge.backend.core.config import settings
from agentforge.backend.core.exceptions import AgentExecutionError
from agentforge.backend.core.logging import get_logger

# All transient network exception types that warrant an automatic retry.
# Covers: Python builtins, httpx transport errors, and OpenAI SDK wrappers.
_RETRYABLE_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.RemoteProtocolError,
    APIConnectionError,
    APITimeoutError,
)

# Placeholder values that mean "not yet configured"
_PLACEHOLDER_PREFIXES = ("sk-or-v1-REPLACE", "sk-REPLACE", "REPLACE", "")

# Dedicated thread pool used by the httpx async client so it never touches
# the default executor that Python shuts down at interpreter exit.
_HTTP_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="http_client"
)


def _validate_api_key(key: str, provider: str) -> str:
    """
    Raise a clear AgentExecutionError if the key is empty or still a placeholder,
    rather than letting the OpenAI SDK raise a cryptic credential error.
    """
    if not key or any(key.startswith(p) for p in _PLACEHOLDER_PREFIXES if p):
        if provider == "openrouter":
            raise AgentExecutionError(
                "llm_init",
                "OPENROUTER_API_KEY is not set.\n\n"
                "  Steps to get a FREE key (no credit card):\n"
                "    1. Go to  https://openrouter.ai\n"
                "    2. Sign up\n"
                "    3. Go to  https://openrouter.ai/keys  → Create Key\n"
                "    4. Open agentforge\\.env  and set:\n"
                "         OPENROUTER_API_KEY=sk-or-v1-your-key-here\n"
                "    5. Restart the server with  .\\run_backend.bat",
            )
        raise AgentExecutionError(
            "llm_init",
            "OPENAI_API_KEY is not set.\n"
            "  Add it to agentforge\\.env:\n"
            "    OPENAI_API_KEY=sk-your-key-here",
        )
    return key


def build_llm(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> ChatOpenAI:
    """
    Build a ChatOpenAI instance routed to either OpenRouter or OpenAI,
    depending on the LLM_PROVIDER setting.

    We pass a pre-created httpx.AsyncClient so the OpenAI SDK never needs to
    call asyncio.to_thread() / run_in_executor(None, ...) for platform detection.
    This prevents the "cannot schedule new futures after interpreter shutdown"
    crash that occurs when the pipeline runs inside a secondary asyncio.run() loop.
    """
    effective_model       = model       or settings.LLM_MODEL
    effective_temperature = temperature if temperature is not None else settings.OPENAI_TEMPERATURE
    effective_max_tokens  = max_tokens  or settings.OPENAI_MAX_TOKENS

    # Validate before passing to ChatOpenAI so the error is human-readable
    validated_key = _validate_api_key(settings.LLM_API_KEY, settings.LLM_PROVIDER)

    # Pre-create an httpx.AsyncClient so the SDK uses it directly instead of
    # spawning internal threads for platform detection on the first request.
    async_http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=5.0),
        follow_redirects=True,
    )

    common_kwargs: Dict[str, Any] = dict(
        model              = effective_model,
        temperature        = effective_temperature,
        max_tokens         = effective_max_tokens,
        api_key            = validated_key,
        base_url           = settings.LLM_BASE_URL,
        http_async_client  = async_http_client,
    )

    # OpenRouter requires these headers to identify your app in their dashboard
    # and for per-model rate limiting on the free tier.
    if settings.LLM_PROVIDER == "openrouter":
        common_kwargs["default_headers"] = {
            "HTTP-Referer": settings.OPENROUTER_SITE_URL,
            "X-Title":      settings.OPENROUTER_SITE_NAME,
        }

    return ChatOpenAI(**common_kwargs)


class BaseAgent(ABC):
    """
    Abstract base class shared by all AgentForge agents.

    Subclasses implement _execute().
    Callers invoke run() which wraps execution with retry, timing, and logging.
    """

    agent_name: str = "base_agent"

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        self.logger = get_logger(f"agent.{self.agent_name}")
        self._llm = build_llm(model, temperature, max_tokens)

        self.logger.info(
            "agent_llm_configured",
            agent    = self.agent_name,
            provider = settings.LLM_PROVIDER,
            model    = self._llm.model_name,
            base_url = settings.LLM_BASE_URL,
        )

    async def _call_llm(self, messages: list) -> str:
        """
        Invoke the LLM and return the plain-text response string.

        Wraps the call so that transient network failures
        (httpx.ConnectError, APIConnectionError, timeouts, etc.) are caught,
        logged with a clear message, and re-raised as AgentExecutionError so
        the caller's retry loop and the background task's error handler both
        see a consistent exception type.
        """
        try:
            response = await self._llm.ainvoke(messages)
        except _RETRYABLE_EXCEPTIONS as exc:
            # These are transient — let the run() retry loop handle them.
            self.logger.warning(
                "llm_network_error",
                agent=self.agent_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise  # re-raise so tenacity can retry
        except Exception as exc:
            # Non-retryable (auth error, bad request, etc.) — wrap immediately.
            self.logger.error(
                "llm_call_failed",
                agent=self.agent_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise AgentExecutionError(
                self.agent_name,
                f"LLM call failed ({type(exc).__name__}): {exc}",
            ) from exc

        raw = str(response.content) if hasattr(response, "content") else str(response)
        # Normalise Unicode punctuation that some LLMs emit (non-breaking hyphens,
        # curly quotes, en/em dashes) to their plain ASCII equivalents so they
        # render cleanly in the frontend Markdown view.
        _UNICODE_MAP = str.maketrans({
            "\u2011": "-",   # non-breaking hyphen
            "\u2012": "-",   # figure dash
            "\u2013": "-",   # en dash
            "\u2014": "-",   # em dash
            "\u2018": "'",   # left single quote
            "\u2019": "'",   # right single quote
            "\u201c": '"',   # left double quote
            "\u201d": '"',   # right double quote
            "\u00a0": " ",   # non-breaking space
            "\u2026": "...", # ellipsis
        })
        return raw.translate(_UNICODE_MAP)

    @abstractmethod
    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Core agent logic. Receives shared LangGraph state, returns updated state."""
        ...

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Public entry point — wraps _execute() with:
          • 3-attempt retry with exponential back-off (network errors only)
          • Per-agent wall-clock timeout
          • Structured log on start / complete / fail
        """
        start = time.perf_counter()
        self.logger.info("agent_starting", agent=self.agent_name)

        try:
            async for attempt in AsyncRetrying(
                stop     = stop_after_attempt(3),
                wait     = wait_exponential(multiplier=1, min=1, max=10),
                retry    = retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
                reraise  = True,
            ):
                with attempt:
                    result = await asyncio.wait_for(
                        self._execute(state),
                        timeout=settings.AGENT_TIMEOUT_SECONDS,
                    )
        except asyncio.TimeoutError as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            self.logger.error("agent_timeout", agent=self.agent_name, elapsed_ms=elapsed)
            raise AgentExecutionError(
                self.agent_name, f"timed out after {settings.AGENT_TIMEOUT_SECONDS}s"
            ) from exc
        except AgentExecutionError:
            raise
        except Exception as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            self.logger.error(
                "agent_failed", agent=self.agent_name,
                error=str(exc), elapsed_ms=elapsed,
            )
            raise AgentExecutionError(self.agent_name, str(exc)) from exc

        elapsed = int((time.perf_counter() - start) * 1000)
        self.logger.info("agent_completed", agent=self.agent_name, elapsed_ms=elapsed)
        result.setdefault("agent_timings", {})[self.agent_name] = elapsed
        return result
