"""
Structured logging with JSON output, correlation IDs, and agent-level tracing.
"""
import logging
import sys
import json
import traceback
from datetime import datetime, timezone
from typing import Any, Optional
from contextvars import ContextVar
import uuid

# Context variable for correlation ID (per-request tracing)
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
claim_id_var: ContextVar[str] = ContextVar("claim_id", default="")
agent_name_var: ContextVar[str] = ContextVar("agent_name", default="")


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON for observability platforms."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Inject context variables
        corr_id = correlation_id_var.get("")
        if corr_id:
            log_data["correlation_id"] = corr_id

        claim_id = claim_id_var.get("")
        if claim_id:
            log_data["claim_id"] = claim_id

        agent = agent_name_var.get("")
        if agent:
            log_data["agent"] = agent

        # Extra fields from logger.info(..., extra={...})
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        # Exception info
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_data, default=str, ensure_ascii=False)


class ContextLogger(logging.LoggerAdapter):
    """Logger adapter that automatically injects context into every log call."""

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        extra = kwargs.get("extra", {})
        extra.setdefault("extra_data", {})
        return msg, kwargs


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Initialize the logging system. Call once at application startup."""
    import os

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    formatter = JSONFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    for noisy in ["httpx", "httpcore", "uvicorn.access", "sqlalchemy.engine"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger. Use module __name__ as convention."""
    return logging.getLogger(name)


def set_correlation_id(corr_id: Optional[str] = None) -> str:
    """Set or generate a correlation ID for the current async context."""
    cid = corr_id or str(uuid.uuid4())
    correlation_id_var.set(cid)
    return cid


def set_claim_context(claim_id: str) -> None:
    """Set the active claim ID for log tracing."""
    claim_id_var.set(claim_id)


def set_agent_context(agent_name: str) -> None:
    """Set the active agent name for log tracing."""
    agent_name_var.set(agent_name)


def clear_context() -> None:
    """Clear all context variables."""
    correlation_id_var.set("")
    claim_id_var.set("")
    agent_name_var.set("")


def log_agent_start(logger: logging.Logger, agent_name: str, claim_id: str) -> None:
    set_agent_context(agent_name)
    logger.info(f"Agent {agent_name} started", extra={"extra_data": {"claim_id": claim_id, "event": "agent_start"}})


def log_agent_complete(logger: logging.Logger, agent_name: str, claim_id: str, result: dict) -> None:
    logger.info(
        f"Agent {agent_name} completed",
        extra={"extra_data": {"claim_id": claim_id, "event": "agent_complete", "result_keys": list(result.keys())}},
    )


def log_agent_error(logger: logging.Logger, agent_name: str, claim_id: str, error: Exception) -> None:
    logger.error(
        f"Agent {agent_name} failed: {str(error)}",
        extra={"extra_data": {"claim_id": claim_id, "event": "agent_error", "error_type": type(error).__name__}},
        exc_info=True,
    )
