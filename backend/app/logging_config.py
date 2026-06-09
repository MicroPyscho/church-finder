"""
Structured logging configuration for Sanctuary.

Development: human-readable coloured output
Production:  JSON lines (compatible with Datadog, Papertrail, CloudWatch)
"""
import logging
import sys
from app.config import settings


class _DevFormatter(logging.Formatter):
    GREY   = "\x1b[38;20m"
    YELLOW = "\x1b[33;20m"
    RED    = "\x1b[31;20m"
    BOLD   = "\x1b[1;31m"
    RESET  = "\x1b[0m"

    FORMATS = {
        logging.DEBUG:    GREY   + "%(levelname)-8s %(name)s: %(message)s" + RESET,
        logging.INFO:     "%(levelname)-8s %(name)s: %(message)s",
        logging.WARNING:  YELLOW + "%(levelname)-8s %(name)s: %(message)s" + RESET,
        logging.ERROR:    RED    + "%(levelname)-8s %(name)s: %(message)s" + RESET,
        logging.CRITICAL: BOLD   + "%(levelname)-8s %(name)s: %(message)s" + RESET,
    }

    def format(self, record):
        fmt = self.FORMATS.get(record.levelno, self.FORMATS[logging.INFO])
        return logging.Formatter(fmt).format(record)


class _JSONFormatter(logging.Formatter):
    def format(self, record):
        import json
        from datetime import datetime, timezone
        return json.dumps({
            "time":    datetime.now(timezone.utc).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "message": record.getMessage(),
            "module":  record.module,
        })


def configure_logging():
    """Set up logging for the application."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Remove existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if settings.is_production:
        handler.setFormatter(_JSONFormatter())
    else:
        handler.setFormatter(_DevFormatter())

    root.addHandler(handler)

    # Silence noisy libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    logging.getLogger("playwright").setLevel(logging.WARNING)
