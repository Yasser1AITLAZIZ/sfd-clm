"""Main FastAPI application for Backend MCP service"""
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
from app.api.v1.endpoints import salesforce, tasks

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
app.include_router(salesforce.router, tags=["MCP Salesforce"])
app.include_router(tasks.router, tags=["Tasks"])


@app.on_event("startup")
async def startup_event():
    """Startup event"""
    try:
        # Verify critical methods exist at startup
        from app.services.workflow_orchestrator import WorkflowOrchestrator
        from app.services.prompting.prompt_builder import PromptBuilder
        from app.services.prompting.prompt_optimizer import PromptOptimizer
        
        # Create test instances to verify methods
        test_pb = PromptBuilder()
        test_po = PromptOptimizer()
        
        has_build_prompt = hasattr(test_pb, 'build_prompt')
        has_optimize_prompt = hasattr(test_po, 'optimize_prompt')
        
        # Initialize SessionStorage at startup to create database if it doesn't exist
        try:
            from app.services.session_router import get_session_manager
            session_manager = get_session_manager()
            safe_log(
                logger,
                logging.INFO,
                "SessionStorage initialized at startup",
                db_path=session_manager.storage.db_path
            )
        except Exception as e:
            safe_log(
                logger,
                logging.WARNING,
                "Failed to initialize SessionStorage at startup (will be initialized on first use)",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
        
        safe_log(
            logger,
            logging.INFO,
            "Backend MCP service starting",
            app_name=settings.app_name,
            debug=settings.debug,
            log_level=settings.log_level,
            mock_salesforce_url=settings.mock_salesforce_url,
            has_build_prompt=has_build_prompt,
            has_optimize_prompt=has_optimize_prompt
        )
        
        if not has_build_prompt:
            safe_log(
                logger,
                logging.ERROR,
                "CRITICAL: build_prompt method not found at startup!",
                available_methods=str([m for m in dir(test_pb) if not m.startswith('_')])
            )
        if not has_optimize_prompt:
            safe_log(
                logger,
                logging.ERROR,
                "CRITICAL: optimize_prompt method not found at startup!",
                available_methods=str([m for m in dir(test_po) if not m.startswith('_')])
            )
    except Exception as e:
        print(f"Error in startup logging: {e}")
        import traceback
        traceback.print_exc()


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    try:
        safe_log(logger, logging.INFO, "Backend MCP service shutting down")
    except Exception:
        pass


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        return {
            "status": "healthy",
            "service": "backend-mcp",
            "version": "1.0.0"
        }
    except Exception as e:
        safe_log(logger, logging.ERROR, "Error in health check", error=str(e))
        return {
            "status": "unhealthy",
            "service": "backend-mcp"
        }

