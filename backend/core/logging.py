"""
AgentForge – Structured Logging
=================================
Configures structlog for JSON-formatted, async-safe logging.
All agents and services import `get_logger` from here.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from agentforge.backend.core.config import settings


def _add_service_name(
    logger: Any, method: str, event_dict: EventDict
) -> EventDict:
    """Inject the service name into every log record."""
    event_dict["service"] = settings.APP_NAME
    event_dict["version"] = settings.APP_VERSION
    event_dict["env"] = settings.ENVIRONMENT
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog with JSON rendering in production and
    pretty-printed console output in development/debug mode.
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        _add_service_name,
    ]

    if settings.LOG_JSON:
        # Production: machine-readable JSON
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: coloured, human-readable console
        renderer = structlog.dev.ConsoleRenderer(colors=True)  # type: ignore[assignment]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a named bound logger. Usage: logger = get_logger(__name__)"""
    return structlog.get_logger(name)
