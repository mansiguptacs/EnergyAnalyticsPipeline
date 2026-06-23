"""
Structured JSON logging configuration for the Energy Analytics Pipeline.

Why structured logging?
- Machine-parseable: can be ingested by ELK, CloudWatch, Datadog
- Consistent format: every log line has the same fields
- Rich context: pipeline name, batch_id, row counts in every log line
- Searchable: easy to filter by batch_id, pipeline, severity

Usage:
    from src.utils.logging_config import setup_logging
    
    logger = setup_logging("my_pipeline")
    logger.info("Processing started", extra={"batch_id": "abc-123", "rows": 5000})
"""

import json
import logging
import sys
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach optional context fields if the caller passed them via `extra`
        for key in ("pipeline", "batch_id", "execution_date", "rows_processed", "file"):
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value

        # Include exception traceback if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging(
    name: str = "energy_pipeline",
    level: int | str = logging.INFO,
    use_json: bool = True,
) -> logging.Logger:
    """
    Configure and return a logger for a pipeline component.

    Args:
        name: Logger name (appears in every log line).
        level: Logging level (DEBUG, INFO, WARNING, ERROR).
        use_json: If True, output structured JSON. If False, use human-readable format.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)

    if use_json:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("psycopg2").setLevel(logging.WARNING)

    return logger
