"""Main FastAPI application for Backend LangGraph service"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import get_logger, safe_log
from app.api.v1.endpoints import mcp

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

# Include routers
app.include_router(mcp.router, tags=["LangGraph MCP"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "backend-langgraph"}


@app.on_event("startup")
async def startup_event():
    """Startup event"""
    try:
        safe_log(
            logger,
            logging.INFO,
            "Backend LangGraph service starting",
            app_name=settings.app_name,
            debug=settings.debug,
            log_level=settings.log_level,
            port=settings.port
        )
    except Exception as e:
        print(f"Error in startup logging: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    try:
        safe_log(
            logger,
            logging.INFO,
            "Backend LangGraph service shutting down"
        )
    except Exception as e:
        print(f"Error in shutdown logging: {e}")

