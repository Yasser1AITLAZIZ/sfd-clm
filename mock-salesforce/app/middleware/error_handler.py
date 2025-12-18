"""Global error handling middleware"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Any, Dict
import traceback
import logging
from app.core.logging import get_logger, safe_log

logger = get_logger(__name__)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled exceptions"""
    import logging
    try:
        # Get request context safely
        record_id = request.path_params.get("record_id", "unknown")
        if hasattr(request.state, "record_id"):
            record_id = getattr(request.state, "record_id", "unknown")
        
        # Log the exception with full context
        try:
            traceback_str = traceback.format_exc()
        except Exception:
            traceback_str = "Unable to format traceback"
        
        safe_log(
            logger,
            logging.ERROR,
            "Unhandled exception",
            error_type=type(exc).__name__,
            error_message=str(exc) if exc else "Unknown error",
            endpoint=request.url.path if hasattr(request, 'url') else "unknown",
            method=request.method if hasattr(request, 'method') else "unknown",
            record_id=record_id,
            traceback=traceback_str
        )
        
        # Return standardized error response
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred",
                    "details": None
                }
            }
        )
    except Exception as log_error:
        # Even error handling can fail, so we have a fallback
        try:
            print(f"Error handler failed: {log_error}")
        except Exception:
            pass
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred"
                }
            }
        )


async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors"""
    try:
        record_id = "unknown"
        if hasattr(request.state, "record_id"):
            record_id = getattr(request.state, "record_id", "unknown")
        
        safe_log(
            logger,
            logging.WARNING,
            "Validation error",
            error_type="ValidationError",
            errors=exc.errors() if hasattr(exc, "errors") else [],
            endpoint=request.url.path,
            record_id=record_id
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input data",
                    "details": exc.errors() if hasattr(exc, "errors") else None
                }
            }
        )
    except Exception as e:
        safe_log(logger, logging.ERROR, "Error in validation handler", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input data"
                }
            }
        )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTP exceptions"""
    try:
        record_id = "unknown"
        if hasattr(request.state, "record_id"):
            record_id = getattr(request.state, "record_id", "unknown")
        
        safe_log(
            logger,
            logging.WARNING,
            "HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail if hasattr(exc, "detail") else None,
            endpoint=request.url.path,
            record_id=record_id
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail if hasattr(exc, "detail") else "HTTP error",
                    "details": None
                }
            }
        )
    except Exception as e:
        safe_log(logger, logging.ERROR, "Error in HTTP exception handler", error=str(e))
        return JSONResponse(
            status_code=exc.status_code if hasattr(exc, "status_code") else 500,
            content={
                "status": "error",
                "error": {
                    "code": "HTTP_ERROR",
                    "message": "HTTP error occurred"
                }
            }
        )


import logging

