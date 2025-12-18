"""Main FastAPI application for Mock Salesforce service"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import get_logger, safe_log
from app.middleware.error_handler import (
    global_exception_handler,
    validation_exception_handler,
    http_exception_handler
)
from app.api.v1.endpoints import salesforce, apex

import logging

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)

# Include routers
app.include_router(salesforce.router, tags=["Salesforce Mock"])
app.include_router(apex.router, tags=["Apex Mock"])


@app.on_event("startup")
async def startup_event():
    """Startup event"""
    try:
        safe_log(
            logger,
            logging.INFO,
            "Mock Salesforce service starting",
            app_name=settings.app_name,
            debug=settings.debug,
            log_level=settings.log_level
        )
    except Exception as e:
        print(f"Error in startup logging: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    try:
        safe_log(logger, logging.INFO, "Mock Salesforce service shutting down")
    except Exception:
        pass


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        return {
            "status": "healthy",
            "service": "mock-salesforce",
            "version": "1.0.0"
        }
    except Exception as e:
        safe_log(logger, logging.ERROR, "Error in health check", error=str(e))
        return {
            "status": "unhealthy",
            "service": "mock-salesforce"
        }

