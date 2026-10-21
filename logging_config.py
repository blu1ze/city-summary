"""Logging setup: structlog to stderr, every record carries a short run_id."""

import logging
import sys
import uuid

import structlog


def configure_logging(verbose: bool = False) -> str:
    """Configure structlog and return the run_id of this process."""
    run_id = uuid.uuid4().hex[:8]
    level = logging.DEBUG if verbose else logging.WARNING

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        # Logs go to stderr: stdout stays clean for the summary and --json
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(run_id=run_id)
    return run_id
