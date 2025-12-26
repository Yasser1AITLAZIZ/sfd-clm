"""Session manager service for business logic"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from app.core.logging import get_logger, safe_log
from app.core.exceptions import SessionStorageError, SessionNotFoundError, InvalidRequestError
from app.services.session_storage import SessionStorage
from app.models.schemas import (
    SalesforceDataResponseSchema,
    SessionContextSchema,
    ConversationMessageSchema
)

logger = get_logger(__name__)


class SessionManager:
    """Session manager for business logic operations"""
    
    def __init__(self, session_storage: SessionStorage):
        """
        Initialize session manager.
        
        Args:
            session_storage: SessionStorage instance
        """
        self.storage = session_storage
        
        safe_log(
            logger,
            logging.INFO,
            "SessionManager initialized"
        )
    
    def initialize_session(
        self,
        record_id: str,
        salesforce_data: SalesforceDataResponseSchema
    ) -> str:
        """
        Initialize a new session with Salesforce data.
        
        Args:
            record_id: Salesforce record ID
            salesforce_data: Salesforce data response schema
            
        Returns:
            session_id: Generated session ID
        """
        try:
            # Validate inputs
            if not record_id or not record_id.strip():
                safe_log(
                    logger,
                    logging.ERROR,
                    "Empty record_id in initialize_session",
                    record_id=record_id or "none"
                )
                raise InvalidRequestError("record_id cannot be None or empty")
            
            if not salesforce_data:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Empty salesforce_data in initialize_session",
                    record_id=record_id
                )
                raise InvalidRequestError("salesforce_data cannot be None")
            
            record_id = record_id.strip()
            
            # Create initial context
            context = {
                "salesforce_data": salesforce_data.model_dump(),
                "conversation_history": [],
                "extracted_data": {},
                "metadata": {
                    "preprocessing_completed": False,
                    "prompt_built": False,
                    "langgraph_processed": False
                }
            }
            
            # Create session via storage
            try:
                session_id = self.storage.create_session(record_id, context)
            except SessionStorageError as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Storage error in initialize_session",
                    record_id=record_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                raise
            
            safe_log(
                logger,
                logging.INFO,
                "Session initialized",
                session_id=session_id,
                record_id=record_id,
                documents_count=len(salesforce_data.documents) if salesforce_data.documents else 0,
                fields_count=len(salesforce_data.fields_to_fill) if salesforce_data.fields_to_fill else 0
            )
            
            return session_id
            
        except (InvalidRequestError, SessionStorageError):
            raise
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in initialize_session",
                record_id=record_id if 'record_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            raise SessionStorageError(f"Unexpected error initializing session: {e}") from e
    
    def check_session_exists(self, session_id: str) -> bool:
        """
        Check if session exists and is not expired.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if session exists, False otherwise
        """
        try:
            # Validate input
            if not session_id or not session_id.strip():
                safe_log(
                    logger,
                    logger.DEBUG,
                    "Empty session_id in check_session_exists",
                    session_id=session_id or "none"
                )
                return False
            
            session_id = session_id.strip()
            
            # Get session
            session = self.storage.get_session(session_id)
            
            exists = session is not None
            
            safe_log(
                logger,
                logger.DEBUG,
                "Session existence checked",
                session_id=session_id,
                exists=exists
            )
            
            return exists
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in check_session_exists",
                session_id=session_id if 'session_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            # Return False on error to be safe
            return False
    
    def append_message_to_history(
        self,
        session_id: str,
        role: str,
        message: str
    ) -> bool:
        """
        Append message to conversation history.
        
        Args:
            session_id: Session ID
            role: Message role ("user" or "assistant")
            message: Message content
            
        Returns:
            True if successful, False if session not found
        """
        try:
            # Validate inputs
            if not session_id or not session_id.strip():
                safe_log(
                    logger,
                    logging.ERROR,
                    "Empty session_id in append_message_to_history",
                    session_id=session_id or "none"
                )
                raise InvalidRequestError("session_id cannot be None or empty")
            
            if role not in ("user", "assistant"):
                safe_log(
                    logger,
                    logging.ERROR,
                    "Invalid role in append_message_to_history",
                    session_id=session_id,
                    role=role or "none"
                )
                raise InvalidRequestError(f"role must be 'user' or 'assistant', got '{role}'")
            
            if not message or not message.strip():
                safe_log(
                    logger,
                    logging.ERROR,
                    "Empty message in append_message_to_history",
                    session_id=session_id,
                    role=role
                )
                raise InvalidRequestError("message cannot be None or empty")
            
            session_id = session_id.strip()
            message = message.strip()
            
            # Get current session
            session = self.storage.get_session(session_id)
            if not session:
                safe_log(
                    logger,
                    logger.WARNING,
                    "Session not found for appending message",
                    session_id=session_id
                )
                return False
            
            # Get conversation history
            context = session.get("context", {})
            conversation_history = context.get("conversation_history", [])
            
            # Create new message
            new_message = {
                "role": role,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Append to history
            conversation_history.append(new_message)
            
            # Update session
            updates = {
                "context": {
                    "conversation_history": conversation_history
                }
            }
            
            success = self.storage.update_session(session_id, updates)
            
            if success:
                safe_log(
                    logger,
                    logging.INFO,
                    "Message appended to history",
                    session_id=session_id,
                    role=role,
                    message_length=len(message)
                )
            else:
                safe_log(
                    logger,
                    logger.WARNING,
                    "Failed to update session when appending message",
                    session_id=session_id
                )
            
            return success
            
        except (InvalidRequestError, SessionStorageError):
            raise
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in append_message_to_history",
                session_id=session_id if 'session_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return False
    
    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete session context.
        
        Args:
            session_id: Session ID
            
        Returns:
            Context dictionary or None if session not found/expired
        """
        try:
            # Validate input
            if not session_id or not session_id.strip():
                safe_log(
                    logger,
                    logger.WARNING,
                    "Empty session_id in get_session_context",
                    session_id=session_id or "none"
                )
                return None
            
            session_id = session_id.strip()
            
            # Get session
            session = self.storage.get_session(session_id)
            if not session:
                safe_log(
                    logger,
                    logger.DEBUG,
                    "Session not found for context retrieval",
                    session_id=session_id
                )
                return None
            
            # Extract context
            context = session.get("context")
            if not context:
                safe_log(
                    logger,
                    logger.WARNING,
                    "Session has no context",
                    session_id=session_id
                )
                return None
            
            safe_log(
                logger,
                logger.DEBUG,
                "Session context retrieved",
                session_id=session_id,
                record_id=session.get("record_id") or "unknown",
                history_length=len(context.get("conversation_history", []))
            )
            
            return context
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in get_session_context",
                session_id=session_id if 'session_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return None
    
    def extend_session_ttl(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """
        Extend session TTL.
        
        Args:
            session_id: Session ID
            ttl: New TTL in seconds (default: uses storage default)
            
        Returns:
            True if successful, False if session not found
        """
        try:
            # Validate input
            if not session_id or not session_id.strip():
                safe_log(
                    logger,
                    logger.WARNING,
                    "Empty session_id in extend_session_ttl",
                    session_id=session_id or "none"
                )
                return False
            
            session_id = session_id.strip()
            
            # Extend TTL via storage
            success = self.storage.extend_session_ttl(session_id, ttl)
            
            if success:
                safe_log(
                    logger,
                    logging.INFO,
                    "Session TTL extended via manager",
                    session_id=session_id,
                    ttl=ttl or "default"
                )
            else:
                safe_log(
                    logger,
                    logger.WARNING,
                    "Failed to extend session TTL",
                    session_id=session_id
                )
            
            return success
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in extend_session_ttl",
                session_id=session_id if 'session_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return False

