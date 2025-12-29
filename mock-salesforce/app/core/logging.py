"""Defensive structured logging"""
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger


class SafeJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that never fails"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record safely"""
        try:
            # Ensure all values are safe for JSON
            safe_record = self._make_safe(record)
            return super().format(safe_record)
        except Exception as e:
            # Fallback to simple format if JSON formatting fails
            try:
                return f"{record.levelname}: {record.getMessage()}"
            except Exception:
                return f"Logging error: {str(e)}"
    
    def _make_safe(self, record: logging.LogRecord) -> logging.LogRecord:
        """Make record safe for JSON serialization"""
        # Convert any None values to strings
        for key, value in record.__dict__.items():
            if value is None:
                setattr(record, key, "none")
        return record


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger with defensive logging"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = SafeJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Get log level from settings
        from app.core.config import settings
        log_level_str = settings.log_level.upper()
        log_level = getattr(logging, log_level_str, logging.DEBUG)
        logger.setLevel(log_level)
    
    return logger


def safe_log(
    logger: logging.Logger,
    level: int,
    message: str,
    **kwargs: Any
) -> None:
    """Safely log a message with defensive checks"""
    try:
        # Prepare safe extra data
        extra: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Add kwargs with safe defaults
        for key, value in kwargs.items():
            if value is None:
                extra[key] = "none"
            elif isinstance(value, str):
                extra[key] = value
            elif isinstance(value, (int, float, bool)):
                extra[key] = value
            else:
                # Convert to string for safety
                try:
                    extra[key] = str(value)
                except Exception:
                    extra[key] = "unserializable"
        
        logger.log(level, message, extra=extra)
    except Exception as e:
        # Logging should never break the application
        try:
            print(f"Logging error (non-critical): {e}")
        except Exception:
            pass  # Even print can fail, so we silently ignore

