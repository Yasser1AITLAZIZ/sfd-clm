"""Main FastAPI application for Backend LangGraph service"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import get_logger, safe_log
from app.api.v1.endpoints import mcp, metrics

import logging

logger = get_logger(__name__)

# Initialize Phoenix Arize tracing if enabled
_phoenix_initialized = False

def _initialize_phoenix():
    """Initialize Phoenix Arize tracing for LangGraph"""
    global _phoenix_initialized
    
    if not settings.phoenix_enabled:
        safe_log(
            logger,
            logging.INFO,
            "Phoenix tracing is disabled",
            phoenix_enabled=settings.phoenix_enabled
        )
        return
    
    if _phoenix_initialized:
        return
    
    try:
        from phoenix.otel import register
        from openinference.instrumentation.langchain import LangChainInstrumentor
        
        safe_log(
            logger,
            logging.INFO,
            "Initializing Phoenix tracing",
            project_name=settings.phoenix_project_name,
            endpoint=settings.phoenix_endpoint or "local",
            collector_endpoint=settings.phoenix_collector_endpoint or "default"
        )
        
        # Register Phoenix tracer
        tracer_provider = register(
            project_name=settings.phoenix_project_name,
            endpoint=settings.phoenix_endpoint,
            collector_endpoint=settings.phoenix_collector_endpoint,
            auto_instrument=True
        )
        
        # Instrument LangChain/LangGraph
        LangChainInstrumentor().instrument()
        
        _phoenix_initialized = True
        
        safe_log(
            logger,
            logging.INFO,
            "Phoenix tracing initialized successfully",
            project_name=settings.phoenix_project_name
        )
        
    except ImportError as e:
        safe_log(
            logger,
            logging.WARNING,
            "Phoenix dependencies not installed, tracing disabled",
            error=str(e),
            install_hint="pip install openinference-instrumentation-langchain arize-phoenix"
        )
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Failed to initialize Phoenix tracing",
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown"
        )

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
app.include_router(metrics.router, prefix="/api/v1", tags=["Metrics"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "backend-langgraph"}


@app.on_event("startup")
async def startup_event():
    """Startup event"""
    # Initialize Phoenix tracing
    _initialize_phoenix()
    try:
        safe_log(
            logger,
            logging.INFO,
            "Backend LangGraph service starting",
            app_name=settings.app_name,
            debug=settings.debug,
            log_level=settings.log_level,
            port=settings.port,
            phoenix_enabled=settings.phoenix_enabled
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

