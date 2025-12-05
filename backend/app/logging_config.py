import logging
import logging.handlers
import sys
from pathlib import Path

import structlog


def configure_logging(log_file: str, log_level: str = "INFO") -> None:
    """
    Configure structured logging with JSON formatter

    This sets up:
    - JSON formatting for machine-readable logs
    - Console output for development
    - File output with rotation for production
    - Proper log levels and filtering
    - Contextual information (timestamp, log level, etc.)

    Args:
        log_file: Path to log file (e.g., "logs/automation.log")
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure standard library logging
    # This is needed because some libraries use stdlib logging
    logging.basicConfig(
        format="%(message)s",
        level=numeric_level,
        handlers=[],  # We'll add handlers below
    )

    # Create console handler (for development)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    # Create rotating file handler (for production)
    # Rotate when file reaches 10MB, keep 5 backup files
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)

    # Add handlers to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Configure structlog
    structlog.configure(
        processors=[
            # Add log level to event dict
            structlog.stdlib.add_log_level,
            # Add logger name to event dict
            structlog.stdlib.add_logger_name,
            # Add timestamp to event dict
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            # Add stack info if exception occurred
            structlog.processors.StackInfoRenderer(),
            # Format exception info
            structlog.processors.format_exc_info,
            # Decode unicode
            structlog.processors.UnicodeDecoder(),
            # Render as JSON for file output
            structlog.processors.JSONRenderer(),
        ],
        # Use stdlib logging for output
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache logger instances for performance
        cache_logger_on_first_use=True,
    )


def configure_logging_for_console() -> None:
    """
    Configure logging for console output only (development mode)

    This is a simpler configuration for development that outputs
    human-readable logs to the console instead of JSON.
    """
    # Configure structlog for console output
    structlog.configure(
        processors=[
            # Add log level
            structlog.stdlib.add_log_level,
            # Add logger name
            structlog.stdlib.add_logger_name,
            # Add timestamp
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            # Add stack info if exception occurred
            structlog.processors.StackInfoRenderer(),
            # Format exception info
            structlog.processors.format_exc_info,
            # Decode unicode
            structlog.processors.UnicodeDecoder(),
            # Render as key-value pairs for console (more readable than JSON)
            structlog.dev.ConsoleRenderer(),
        ],
        # Use stdlib logging for output
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache logger instances
        cache_logger_on_first_use=True,
    )

    # Configure basic console output
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
        stream=sys.stdout,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a configured structlog logger instance

    Args:
        name: Optional logger name (defaults to calling module)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
