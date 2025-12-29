"""Session router for handling new vs continuing sessions"""
from typing import Dict, Any, Optional
import logging
import traceback
from datetime import datetime

from app.core.logging import get_logger, safe_log
from app.core.config import settings
from app.core.exceptions import SessionNotFoundError, InvalidRequestError, SessionStorageError
from app.services.salesforce_client import fetch_salesforce_data
from app.services.session_storage import SessionStorage
from app.services.session_manager import SessionManager
from app.models.schemas import (
    InitializationResponseSchema,
    ContinuationResponseSchema,
    SalesforceDataResponseSchema
)

logger = get_logger(__name__)

# Global session manager instance (initialized lazily)
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create session manager instance"""
    global _session_manager
    if _session_manager is None:
        try:
            # Check for SESSION_DB_PATH environment variable (used in Docker)
            import os
            db_path = os.getenv("SESSION_DB_PATH", settings.session_db_path)
            
            storage = SessionStorage(
                db_path=db_path,
                default_ttl=settings.session_ttl_seconds
            )
            _session_manager = SessionManager(storage)
            safe_log(
                logger,
                logging.INFO,
                "SessionManager initialized in router"
            )
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Failed to initialize SessionManager",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown",
                traceback=traceback.format_exc()
            )
            raise SessionStorageError(f"Failed to initialize SessionManager: {e}") from e
    return _session_manager


async def validate_and_route(
    record_id: str,
    session_id: Optional[str],
    user_message: str
) -> Dict[str, Any]:
    """
    Validate request and route to appropriate flow.
    
    Returns response dict with status and data.
    """
    try:
        # Validate parameters
        if not record_id or not record_id.strip():
            safe_log(
                logger,
                logging.ERROR,
                "Empty record_id in validate_and_route",
                record_id=record_id or "none"
            )
            raise InvalidRequestError("record_id cannot be None or empty")
        
        if not user_message or not user_message.strip():
            safe_log(
                logger,
                logging.ERROR,
                "Empty user_message in validate_and_route",
                record_id=record_id
            )
            raise InvalidRequestError("user_message cannot be None or empty")
        
        record_id = record_id.strip()
        user_message = user_message.strip()
        
        # Get session manager
        session_manager = get_session_manager()
        
        # Check if session exists
        session_exists = False
        if session_id:
            session_id = session_id.strip()
            if session_id:
                session_exists = session_manager.check_session_exists(session_id)
        
        safe_log(
            logger,
            logging.INFO,
            "Routing request",
            record_id=record_id,
            session_id=session_id or "none",
            session_exists=session_exists,
            user_message_length=len(user_message)
        )
        
        # Route to appropriate flow
        if not session_exists:
            # New session - initialization flow
            result = await route_to_initialization(record_id, user_message)
            return result
        else:
            # Existing session - continuation flow
            return route_to_continuation(session_id, user_message)
            
    except InvalidRequestError:
        raise
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Unexpected error in validate_and_route",
            record_id=record_id if 'record_id' in locals() else "unknown",
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error",
            traceback=traceback.format_exc()
        )
        raise


async def route_to_initialization(record_id: str, user_message: str) -> Dict[str, Any]:
    """
    Route to initialization flow (new session).
    
    Fetches Salesforce data and prepares for preprocessing.
    """
    try:
        # Validate record_id
        if not record_id or not record_id.strip():
            safe_log(
                logger,
                logging.ERROR,
                "Empty record_id in route_to_initialization",
                record_id=record_id or "none"
            )
            raise InvalidRequestError("record_id cannot be None or empty")
        
        record_id = record_id.strip()
        
        safe_log(
            logger,
            logging.INFO,
            "Routing to initialization",
            record_id=record_id,
            user_message_length=len(user_message) if user_message else 0
        )
        
        # Fetch Salesforce data
        try:
            salesforce_data = await fetch_salesforce_data(record_id)
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Failed to fetch Salesforce data in initialization",
                record_id=record_id,
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            raise
        
        # Validate salesforce_data is complete
        if not salesforce_data:
            safe_log(
                logger,
                logging.ERROR,
                "Salesforce data is None or empty",
                record_id=record_id
            )
            raise InvalidRequestError("Failed to retrieve Salesforce data")
        
        # Initialize session with SessionManager
        session_manager = get_session_manager()
        try:
            session_id = session_manager.initialize_session(record_id, salesforce_data)
        except (SessionStorageError, InvalidRequestError) as e:
            safe_log(
                logger,
                logging.ERROR,
                "Failed to initialize session",
                record_id=record_id,
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            raise
        
        # Create response
        response = InitializationResponseSchema(
            record_id=record_id,
            salesforce_data=salesforce_data
        )
        
        safe_log(
            logger,
            logging.INFO,
            "Initialization routing completed",
            record_id=record_id,
            session_id=session_id,
            documents_count=len(salesforce_data.documents) if salesforce_data.documents else 0,
            fields_count=len(salesforce_data.fields_to_fill) if salesforce_data.fields_to_fill else 0
        )
        
        return response.model_dump()
        
    except InvalidRequestError:
        raise
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Unexpected error in route_to_initialization",
            record_id=record_id if 'record_id' in locals() else "unknown",
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error",
            traceback=traceback.format_exc()
        )
        raise


def route_to_continuation(session_id: str, user_message: str) -> Dict[str, Any]:
    """
    Route to continuation flow (existing session).
    
    Retrieves session context and prepares for prompt building.
    """
    try:
        # Validate session_id
        if not session_id or not session_id.strip():
            safe_log(
                logger,
                logging.ERROR,
                "Empty session_id in route_to_continuation",
                session_id=session_id or "none"
            )
            raise InvalidRequestError("session_id cannot be None or empty")
        
        session_id = session_id.strip()
        
        # Validate user_message
        if not user_message or not user_message.strip():
            safe_log(
                logger,
                logging.ERROR,
                "Empty user_message in route_to_continuation",
                session_id=session_id
            )
            raise InvalidRequestError("user_message cannot be None or empty")
        
        user_message = user_message.strip()
        
        safe_log(
            logger,
            logging.INFO,
            "Routing to continuation",
            session_id=session_id,
            user_message_length=len(user_message)
        )
        
        # Get session manager and retrieve context
        session_manager = get_session_manager()
        session_context = session_manager.get_session_context(session_id)
        
        if not session_context:
            safe_log(
                logger,
                logging.WARNING,
                "Session not found or expired in continuation",
                session_id=session_id
            )
            raise SessionNotFoundError(f"Session {session_id} not found or expired")
        
        # Create response
        response = ContinuationResponseSchema(
            session_id=session_id,
            user_message=user_message
        )
        
        safe_log(
            logger,
            logging.INFO,
            "Continuation routing completed",
            session_id=session_id,
            user_message_length=len(user_message),
            history_length=len(session_context.get("conversation_history", []))
        )
        
        return response.model_dump()
        
    except (InvalidRequestError, SessionNotFoundError):
        raise
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Unexpected error in route_to_continuation",
            session_id=session_id if 'session_id' in locals() else "unknown",
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error",
            traceback=traceback.format_exc()
        )
        raise



