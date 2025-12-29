"""Defensive structured logging with hybrid console/JSON formatters"""
import logging
import sys
import os
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger


class SafeJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that never fails"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record safely"""
        try:
            safe_record = self._make_safe(record)
            return super().format(safe_record)
        except Exception as e:
            try:
                return f"{record.levelname}: {record.getMessage()}"
            except Exception:
                return f"Logging error: {str(e)}"
    
    def _make_safe(self, record: logging.LogRecord) -> logging.LogRecord:
        """Make record safe for JSON serialization"""
        for key, value in record.__dict__.items():
            if value is None:
                setattr(record, key, "none")
        return record


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with colors and progress indicators"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console output"""
        try:
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            
            timestamp = datetime.fromisoformat(
                record.timestamp if hasattr(record, 'timestamp') 
                else datetime.utcnow().isoformat()
            ).strftime("%Y-%m-%d %H:%M:%S")
            
            level_name = f"{color}{record.levelname:8s}{reset}"
            
            progress_info = ""
            if hasattr(record, 'request_id'):
                progress_info = f" [Req:{record.request_id[:8]}]"
            if hasattr(record, 'current_step'):
                step_num = getattr(record, 'step_number', '?')
                total_steps = getattr(record, 'total_steps', '?')
                progress_info += f" [Step {step_num}/{total_steps}: {record.current_step}]"
            
            timing_info = ""
            if hasattr(record, 'elapsed_time'):
                timing_info = f" ({record.elapsed_time:.2f}s)"
            if hasattr(record, 'execution_time'):
                timing_info = f" ({record.execution_time:.2f}s)"
            
            message = record.getMessage()
            
            extra_parts = []
            if hasattr(record, 'record_id') and record.record_id != "unknown":
                extra_parts.append(f"record_id={record.record_id}")
            if hasattr(record, 'session_id') and record.session_id not in ("none", None):
                extra_parts.append(f"session_id={record.session_id}")
            
            context = " | ".join(extra_parts) if extra_parts else ""
            
            parts = [f"{timestamp}", level_name]
            if progress_info:
                parts.append(progress_info)
            parts.append(message)
            if context:
                parts.append(f"({context})")
            if timing_info:
                parts.append(timing_info)
            
            return " ".join(parts)
            
        except Exception as e:
            return f"{record.levelname}: {record.getMessage()}"


def get_logger(name: str, use_console: bool = None) -> logging.Logger:
    """
    Get a configured logger with defensive logging.
    
    Args:
        name: Logger name
        use_console: If True, use console formatter; if False, use JSON;
                    if None, auto-detect based on LOG_FORMAT env var
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        if use_console is None:
            log_format = os.getenv("LOG_FORMAT", "console").lower()
            use_console = log_format in ("console", "human", "readable")
        
        handler = logging.StreamHandler(sys.stdout)
        
        if use_console:
            formatter = ConsoleFormatter()
        else:
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
        extra: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        for key, value in kwargs.items():
            if value is None:
                extra[key] = "none"
            elif isinstance(value, str):
                extra[key] = value
            elif isinstance(value, (int, float, bool)):
                extra[key] = value
            else:
                try:
                    extra[key] = str(value)
                except Exception:
                    extra[key] = "unserializable"
        
        logger.log(level, message, extra=extra)
    except Exception as e:
        try:
            print(f"Logging error (non-critical): {e}")
        except Exception:
            pass


def log_progress(
    logger: logging.Logger,
    level: int,
    message: str,
    step_number: int,
    total_steps: int,
    step_name: str = "",
    **kwargs: Any
) -> None:
    """Log a progress message with step information"""
    progress_pct = int((step_number / total_steps) * 100) if total_steps > 0 else 0
    progress_msg = f"[{progress_pct}%] {message}"
    if step_name:
        progress_msg = f"[{progress_pct}%] Step {step_number}/{total_steps}: {step_name} - {message}"
    
    safe_log(
        logger,
        level,
        progress_msg,
        step_number=step_number,
        total_steps=total_steps,
        current_step=step_name,
        progress_percent=progress_pct,
        **kwargs
    )


def log_timing(
    logger: logging.Logger,
    level: int,
    message: str,
    elapsed_time: float,
    **kwargs: Any
) -> None:
    """Log a message with timing information"""
    timing_msg = f"{message} (took {elapsed_time:.2f}s)"
    safe_log(
        logger,
        level,
        timing_msg,
        elapsed_time=elapsed_time,
        execution_time=elapsed_time,
        **kwargs
    )

