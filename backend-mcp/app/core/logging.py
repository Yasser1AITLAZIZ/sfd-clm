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
            # Get color for log level
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            
            # Format timestamp
            timestamp = datetime.fromisoformat(
                record.timestamp if hasattr(record, 'timestamp') 
                else datetime.utcnow().isoformat()
            ).strftime("%Y-%m-%d %H:%M:%S")
            
            # Build message parts
            level_name = f"{color}{record.levelname:8s}{reset}"
            
            # Extract workflow progress if available
            progress_info = ""
            if hasattr(record, 'workflow_id'):
                progress_info = f" [WF:{record.workflow_id[:8]}]"
            if hasattr(record, 'current_step'):
                step_num = getattr(record, 'step_number', '?')
                total_steps = getattr(record, 'total_steps', '?')
                progress_info += f" [Step {step_num}/{total_steps}: {record.current_step}]"
            elif hasattr(record, 'step_number'):
                step_num = record.step_number
                total_steps = getattr(record, 'total_steps', '?')
                progress_info += f" [Step {step_num}/{total_steps}]"
            
            # Extract timing if available
            timing_info = ""
            if hasattr(record, 'elapsed_time'):
                timing_info = f" ({record.elapsed_time:.2f}s)"
            if hasattr(record, 'execution_time'):
                timing_info = f" ({record.execution_time:.2f}s)"
            
            # Build main message
            message = record.getMessage()
            
            # Add extra context
            extra_parts = []
            if hasattr(record, 'record_id') and record.record_id != "unknown":
                extra_parts.append(f"record_id={record.record_id}")
            if hasattr(record, 'session_id') and record.session_id not in ("none", None):
                extra_parts.append(f"session_id={record.session_id}")
            if hasattr(record, 'workflow_status'):
                extra_parts.append(f"status={record.workflow_status}")
            
            context = " | ".join(extra_parts) if extra_parts else ""
            
            # Build final log line
            parts = [f"{timestamp}", level_name]
            if progress_info:
                parts.append(progress_info)
            parts.append(message)
            if context:
                parts.append(f"({context})")
            if timing_info:
                parts.append(timing_info)
            
            log_line = " ".join(parts)
            
            # Add traceback if available
            if hasattr(record, 'traceback') and record.traceback:
                traceback_str = str(record.traceback)
                # Format traceback with indentation for readability
                traceback_lines = traceback_str.split('\n')
                formatted_traceback = '\n'.join([f"  {line}" for line in traceback_lines if line.strip()])
                if formatted_traceback:
                    log_line += f"\n{color}Traceback:{reset}\n{formatted_traceback}"
            
            return log_line
            
        except Exception as e:
            # Fallback to simple format
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
        # Auto-detect format preference
        if use_console is None:
            log_format = os.getenv("LOG_FORMAT", "console").lower()
            use_console = log_format in ("console", "human", "readable")
        
        handler = logging.StreamHandler(sys.stdout)
        
        if use_console:
            # Use human-readable console formatter
            formatter = ConsoleFormatter()
        else:
            # Use JSON formatter for structured logging
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
    traceback: Optional[str] = None,
    **kwargs: Any
) -> None:
    """
    Safely log a message with defensive checks.
    
    Args:
        logger: Logger instance
        level: Log level (logging.INFO, logging.ERROR, etc.)
        message: Log message
        traceback: Optional traceback string (from traceback.format_exc())
        **kwargs: Additional context to include in log
    """
    try:
        # Prepare safe extra data
        extra: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Add traceback if provided
        if traceback:
            extra["traceback"] = traceback
        
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

