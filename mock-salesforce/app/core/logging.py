"""Defensive structured logging"""
import logging
import sys
import os
import inspect
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger


def _get_service_name() -> str:
    """Get service name from environment variable or container name"""
    service_name = os.getenv("SERVICE_NAME", "")
    if not service_name:
        # Try to infer from container name
        container_name = os.getenv("HOSTNAME", "")
        if "mock-salesforce" in container_name.lower():
            service_name = "mock-salesforce"
        elif "backend-mcp" in container_name.lower():
            service_name = "backend-mcp"
        elif "backend-langgraph" in container_name.lower():
            service_name = "backend-langgraph"
        else:
            service_name = "unknown-service"
    return service_name


def _get_caller_info(skip_frames: int = 2) -> Dict[str, str]:
    """Extract caller information from the call stack"""
    try:
        frame = inspect.currentframe()
        # Skip: current frame, _get_caller_info, safe_log/log function
        for _ in range(skip_frames):
            if frame:
                frame = frame.f_back
        
        if frame:
            filename = os.path.basename(frame.f_code.co_filename)
            function_name = frame.f_code.co_name
            line_number = frame.f_lineno
            module_path = frame.f_code.co_filename
            
            # Get relative path from app directory
            if "/app/" in module_path:
                module_path = module_path.split("/app/")[-1]
            elif "\\app\\" in module_path:
                module_path = module_path.split("\\app\\")[-1]
            
            return {
                "filename": filename,
                "function": function_name,
                "line": str(line_number),
                "module": module_path.replace("\\", "/")
            }
    except Exception:
        pass
    
    return {
        "filename": "unknown",
        "function": "unknown",
        "line": "0",
        "module": "unknown"
    }


class SafeJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that never fails"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record safely"""
        try:
            # Ensure all values are safe for JSON
            safe_record = self._make_safe(record)
            
            # Add service name and location info if not present
            if not hasattr(safe_record, 'service_name'):
                safe_record.service_name = _get_service_name()
            
            # Extract location info from LogRecord (works for both safe_log and direct logger calls)
            # Use source_* fields from safe_log, or fall back to LogRecord built-in attributes
            if not hasattr(safe_record, 'source_filename') or getattr(safe_record, 'source_filename', 'unknown') == "unknown":
                safe_record.source_filename = os.path.basename(safe_record.pathname) if safe_record.pathname else "unknown"
            if not hasattr(safe_record, 'source_function') or getattr(safe_record, 'source_function', 'unknown') == "unknown":
                safe_record.source_function = getattr(safe_record, 'funcName', "unknown")
            if not hasattr(safe_record, 'source_line') or getattr(safe_record, 'source_line', '0') == "0":
                safe_record.source_line = str(getattr(safe_record, 'lineno', 0))
            if not hasattr(safe_record, 'source_module') or getattr(safe_record, 'source_module', 'unknown') == "unknown":
                # Get relative module path
                module_path = safe_record.pathname if safe_record.pathname else ""
                if "/app/" in module_path:
                    safe_record.source_module = module_path.split("/app/")[-1].replace("\\", "/")
                elif "\\app\\" in module_path:
                    safe_record.source_module = module_path.split("\\app\\")[-1].replace("\\", "/")
                else:
                    safe_record.source_module = os.path.basename(module_path) if module_path else "unknown"
            
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
    """Human-readable console formatter with colors and location info"""
    
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
            
            # Get service name
            service_name = getattr(record, 'service_name', _get_service_name())
            service_tag = f"[{service_name}]"
            
            # Get location information from source_* fields (set by safe_log) or LogRecord built-in attributes
            if hasattr(record, 'source_filename') and getattr(record, 'source_filename', 'unknown') != "unknown":
                filename = record.source_filename
            else:
                filename = os.path.basename(record.pathname) if record.pathname else "unknown"
            
            if hasattr(record, 'source_function') and getattr(record, 'source_function', 'unknown') != "unknown":
                function_name = record.source_function
            else:
                function_name = getattr(record, 'funcName', "unknown")
            
            if hasattr(record, 'source_line') and getattr(record, 'source_line', '0') != "0":
                line_number = record.source_line
            else:
                line_number = str(getattr(record, 'lineno', 0))
            
            location_tag = f"[{filename}:{function_name}:{line_number}]"
            
            message = record.getMessage()
            
            # Build final log line with service and location
            parts = [f"{timestamp}", service_tag, level_name, location_tag, message]
            
            return " ".join(parts)
            
        except Exception as e:
            return f"{record.levelname}: {record.getMessage()}"


def get_logger(name: str, use_console: bool = None) -> logging.Logger:
    """
    Get a configured logger with defensive logging.
    Automatically includes service name and location information.
    
    Args:
        name: Logger name (typically __name__)
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
            formatter = ConsoleFormatter()
        else:
            formatter = SafeJsonFormatter(
                "%(timestamp)s %(level)s %(name)s %(service_name)s %(source_filename)s:%(source_function)s:%(source_line)s %(message)s"
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
    """
    Safely log a message with defensive checks.
    Automatically captures caller information (filename, function, line number).
    
    Args:
        logger: Logger instance
        level: Log level (logging.INFO, logging.ERROR, etc.)
        message: Log message
        **kwargs: Additional context to include in log
    """
    try:
        # Get caller information
        caller_info = _get_caller_info(skip_frames=2)
        
        # Prepare safe extra data
        # Use source_* prefix to avoid conflicts with LogRecord built-in attributes
        extra: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "service_name": _get_service_name(),
            "source_filename": caller_info.get("filename", "unknown"),
            "source_function": caller_info.get("function", "unknown"),
            "source_line": caller_info.get("line", "0"),
            "source_module": caller_info.get("module", "unknown"),
        }
        
        # Add kwargs with safe defaults (don't override location info if explicitly provided)
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

