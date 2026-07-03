"""
Logging module for D-Booth backend.

Provides structured JSON logging with async support, request tracing,
and performance monitoring capabilities.
"""

import logging
import sys
import json
from pathlib import Path
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from typing import Any, Dict, Optional
from datetime import datetime
from queue import Queue
import traceback

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in JSON format for structured logging.

    Captures standard log fields plus custom fields from the extra parameter.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.

        Args:
            record: LogRecord to format

        Returns:
            JSON-formatted log string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add custom fields from extra parameter
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "ip"):
            log_data["ip"] = record.ip

        # Add any other custom attributes
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName",
                "relativeCreated", "thread", "threadName", "exc_info",
                "exc_text", "stack_info", "request_id", "user_id",
                "duration_ms", "status_code", "method", "path", "ip"
            ]:
                try:
                    json.dumps(value)  # Test if serializable
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)

        return json.dumps(log_data, default=str, ensure_ascii=False)


class RequestContextFilter(logging.Filter):
    """
    Filter that adds request context to log records.

    Can be enhanced with thread-local storage for automatic context injection.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add default context fields if not present.

        Args:
            record: LogRecord to enhance

        Returns:
            Always True to pass all records
        """
        if not hasattr(record, "request_id"):
            record.request_id = None
        if not hasattr(record, "user_id"):
            record.user_id = None
        return True


def setup_logging() -> logging.Logger:
    """
    Configure application logging with JSON formatting and async support.

    Sets up:
    - Console handler with human-readable format (dev) or JSON (prod)
    - File handler with JSON format for all logs
    - Error file handler for ERROR+ logs only
    - Async logging via QueueHandler for non-blocking I/O

    Returns:
        Configured root logger instance
    """
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatters
    json_formatter = JSONFormatter()

    # Human-readable formatter for console in dev mode
    console_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ) if settings.DEBUG else json_formatter

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(RequestContextFilter())

    # File handler for all logs (JSON format)
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10_485_760,  # 10MB
        backupCount=10,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(json_formatter)
    file_handler.addFilter(RequestContextFilter())

    # File handler for errors only (JSON format)
    error_handler = RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=10_485_760,  # 10MB
        backupCount=10,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_formatter)
    error_handler.addFilter(RequestContextFilter())

    # Set up async logging via queue
    log_queue: Queue = Queue(-1)  # Unlimited size

    # Queue listener handles actual I/O in background thread
    queue_listener = QueueListener(
        log_queue,
        file_handler,
        error_handler,
        respect_handler_level=True
    )
    queue_listener.start()

    # Queue handlers for async logging
    queue_handler = QueueHandler(log_queue)
    root_logger.addHandler(queue_handler)

    # Console goes direct (for immediate feedback in dev)
    root_logger.addHandler(console_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Store queue listener for cleanup
    root_logger._queue_listener = queue_listener  # type: ignore

    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging initialized: level={logging.getLevelName(log_level)}, "
        f"format={'human-readable' if settings.DEBUG else 'JSON'}"
    )

    return root_logger


def shutdown_logging() -> None:
    """
    Gracefully shutdown logging system.

    Stops the queue listener and flushes all pending logs.
    Should be called during application shutdown.
    """
    root_logger = logging.getLogger()
    if hasattr(root_logger, "_queue_listener"):
        root_logger._queue_listener.stop()  # type: ignore
        logging.info("Logging system shutdown complete")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Operation started", extra={"request_id": "abc123"})
    """
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs: Any
) -> None:
    """
    Log message with additional context fields.

    Args:
        logger: Logger instance to use
        level: Log level (logging.INFO, logging.ERROR, etc.)
        message: Log message
        request_id: Optional request ID for tracing
        user_id: Optional user ID
        **kwargs: Additional context fields

    Example:
        log_with_context(
            logger,
            logging.INFO,
            "User action completed",
            request_id="req-123",
            user_id="user-456",
            action="upload_photo",
            duration_ms=142
        )
    """
    extra: Dict[str, Any] = kwargs.copy()
    if request_id:
        extra["request_id"] = request_id
    if user_id:
        extra["user_id"] = user_id

    logger.log(level, message, extra=extra)


# Initialize logging on module import
logger = setup_logging()
