"""Main FastAPI application for Backend MCP service"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import get_logger, safe_log
from app.core.exceptions import SessionStorageError
from app.middleware.error_handler import (
    global_exception_handler,
    validation_exception_handler,
    http_exception_handler
)
from app.api.v1.endpoints import salesforce, tasks

import logging
import sqlite3
import traceback
import os
from pathlib import Path

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
        
        # Create test instances to verify methods
        test_pb = PromptBuilder()
        
        has_build_prompt = hasattr(test_pb, 'build_prompt')
        
        # CRITICAL: Initialize SessionStorage at startup to create database if it doesn't exist
        # This MUST succeed for the service to work properly
        try:
            from app.services.session_router import get_session_manager
            
            # Get database path (from env or config)
            db_path = os.getenv("SESSION_DB_PATH", settings.session_db_path)
            
            # Force initialization of SessionStorage
            session_manager = get_session_manager()
            
            # Verify database was created by checking if tables exist
            db_file = Path(db_path)
            if db_file.exists():
                # Verify tables exist
                conn = sqlite3.connect(str(db_path))
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
                sessions_table_exists = cursor.fetchone() is not None
                
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_steps'")
                workflow_steps_table_exists = cursor.fetchone() is not None
                conn.close()
                
                if not sessions_table_exists:
                    safe_log(
                        logger,
                        logging.ERROR,
                        "CRITICAL: Database file exists but 'sessions' table is missing!",
                        db_path=db_path
                    )
                    raise SessionStorageError("Database tables not initialized properly: 'sessions' table missing")
                
                safe_log(
                    logger,
                    logging.INFO,
                    "✅ SessionStorage initialized successfully at startup",
                    db_path=session_manager.storage.db_path,
                    database_exists=True,
                    sessions_table_exists=True,
                    workflow_steps_table_exists=workflow_steps_table_exists
                )
            else:
                safe_log(
                    logger,
                    logging.WARNING,
                    "Database file does not exist yet (will be created on first use)",
                    db_path=db_path
                )
                safe_log(
                    logger,
                    logging.INFO,
                    "✅ SessionStorage initialized at startup (database will be created on first use)",
                    db_path=session_manager.storage.db_path
                )
        except SessionStorageError as e:
            # CRITICAL ERROR: Database initialization failed
            error_msg = str(e) if e else "Unknown error"
            safe_log(
                logger,
                logging.CRITICAL,
                "❌ CRITICAL: Failed to initialize SessionStorage at startup",
                error_type=type(e).__name__,
                error_message=error_msg,
                traceback=traceback.format_exc()
            )
            # Re-raise to prevent service from starting with broken database
            raise RuntimeError(f"Failed to initialize database at startup: {error_msg}") from e
        except Exception as e:
            # CRITICAL ERROR: Database initialization failed
            error_msg = str(e) if e else "Unknown error"
            safe_log(
                logger,
                logging.CRITICAL,
                "❌ CRITICAL: Failed to initialize SessionStorage at startup",
                error_type=type(e).__name__,
                error_message=error_msg,
                traceback=traceback.format_exc()
            )
            # Re-raise to prevent service from starting with broken database
            raise RuntimeError(f"Failed to initialize database at startup: {error_msg}") from e
        
        # Also initialize WorkflowStepStorage to ensure workflow_steps table exists
        try:
            from app.services.workflow_step_storage import WorkflowStepStorage
            db_path = os.getenv("SESSION_DB_PATH", settings.session_db_path)
            step_storage = WorkflowStepStorage(db_path)
            safe_log(
                logger,
                logging.INFO,
                "✅ WorkflowStepStorage initialized successfully at startup",
                db_path=db_path
            )
        except Exception as e:
            safe_log(
                logger,
                logging.WARNING,
                "⚠️  Failed to initialize WorkflowStepStorage at startup (will be initialized on first use)",
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
            has_build_prompt=has_build_prompt
        )
        
        if not has_build_prompt:
            safe_log(
                logger,
                logging.ERROR,
                "CRITICAL: build_prompt method not found at startup!",
                available_methods=str([m for m in dir(test_pb) if not m.startswith('_')])
            )
    except Exception as e:
        safe_log(
            logger,
            logging.CRITICAL,
            "FATAL: Service startup failed",
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown",
            traceback=traceback.format_exc()
        )
        # Re-raise to prevent service from starting in broken state
        raise


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

