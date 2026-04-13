"""Structured logging setup."""

from __future__ import annotations

import logging
import sys

import structlog


def setup_logging(level: str = "INFO") -> None:
    """Configure structlog with console output."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=_SafePrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


class _SafePrintLoggerFactory:
    """Like structlog.PrintLoggerFactory but always writes to the
    *current* sys.stderr — not the one captured at factory creation
    time. Prevents 'I/O operation on closed file' when stderr is
    replaced (e.g. by pytest or daemon restart).
    """
    def __call__(self, *args, **kwargs):
        return structlog.PrintLogger(file=sys.stderr)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger."""
    return structlog.get_logger(name)
