"""Session storage with Redis backend"""
import json
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from app.core.logging import get_logger, safe_log
from app.core.exceptions import SessionStorageError

logger = get_logger(__name__)


class SessionStorage:
    """Redis-based session storage with CRUD operations"""
    
    def __init__(self, redis_url: str, default_ttl: int = 86400):
        """
        Initialize session storage with Redis connection.
        
        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
            default_ttl: Default TTL in seconds (default: 86400 = 24 hours)
        """
        try:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            self.default_ttl = default_ttl
            self.key_prefix = "session:"
            
            # Test connection
            self.redis_client.ping()
            
            safe_log(
                logger,
                logging.INFO,
                "SessionStorage initialized",
                redis_url=redis_url.split("@")[-1] if "@" in redis_url else redis_url,
                default_ttl=default_ttl
            )
        except (ConnectionError, TimeoutError) as e:
            safe_log(
                logger,
                logging.ERROR,
                "Failed to connect to Redis",
                redis_url=redis_url.split("@")[-1] if "@" in redis_url else redis_url,
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            raise SessionStorageError(f"Failed to connect to Redis: {e}") from e
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error initializing SessionStorage",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            raise SessionStorageError(f"Unexpected error initializing SessionStorage: {e}") from e
    
    def _get_key(self, session_id: str) -> str:
        """Get Redis key for session"""
        return f"{self.key_prefix}{session_id}"
    
    def create_session(self, record_id: str, context: Dict[str, Any]) -> str:
        """
        Create a new session.
        
        Args:
            record_id: Salesforce record ID
            context: Session context dictionary
            
        Returns:
            session_id: Generated session ID (UUID v4)
        """

        try:
            # Validate inputs
            if not record_id or not record_id.strip():
                safe_log(
                    logger,
                    logging.ERROR,
                    "Empty record_id in create_session",
                    record_id=record_id or "none"
                )
                raise SessionStorageError("record_id cannot be None or empty")
            
            if not context:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Empty context in create_session",
                    record_id=record_id
                )
                raise SessionStorageError("context cannot be None or empty")

            record_id = record_id.strip()
            
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Create session object
            now = datetime.utcnow()
            expires_at = now + timedelta(seconds=self.default_ttl)
            
            session_data = {
                "session_id": session_id,
                "record_id": record_id,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "context": context
            }

            # Store in Redis with TTL
            key = self._get_key(session_id)
            try:
                self.redis_client.setex(
                    key,
                    self.default_ttl,
                    json.dumps(session_data)
                )
            except (ConnectionError, TimeoutError) as e:

                safe_log(
                    logger,
                    logging.ERROR,
                    "Redis connection error in create_session",
                    session_id=session_id,
                    record_id=record_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                raise SessionStorageError(f"Redis connection error: {e}") from e
            except RedisError as e:

                safe_log(
                    logger,
                    logging.ERROR,
                    "Redis error in create_session",
                    session_id=session_id,
                    record_id=record_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                raise SessionStorageError(f"Redis error: {e}") from e
            
            safe_log(
                logger,
                logging.INFO,
                "Session created",
                session_id=session_id,
                record_id=record_id,
                ttl=self.default_ttl
            )
            
            return session_id
            
        except SessionStorageError:
            raise
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in create_session",
                record_id=record_id if 'record_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            raise SessionStorageError(f"Unexpected error creating session: {e}") from e
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data dictionary or None if not found/expired
        """
        try:
            # Validate input
            if not session_id or not session_id.strip():
                safe_log(
                    logger,
                    logger.WARNING,
                    "Empty session_id in get_session",
                    session_id=session_id or "none"
                )
                return None
            
            session_id = session_id.strip()
            key = self._get_key(session_id)
            
            try:
                session_json = self.redis_client.get(key)
            except (ConnectionError, TimeoutError) as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Redis connection error in get_session",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                # Return None on connection error to avoid breaking the app
                return None
            except RedisError as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Redis error in get_session",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return None
            
            if not session_json:
                safe_log(
                    logger,
                    logger.DEBUG,
                    "Session not found or expired",
                    session_id=session_id
                )
                return None
            
            try:
                session_data = json.loads(session_json)
                safe_log(
                    logger,
                    logger.DEBUG,
                    "Session retrieved",
                    session_id=session_id,
                    record_id=session_data.get("record_id") or "unknown"
                )
                return session_data
            except (json.JSONDecodeError, KeyError) as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Invalid session data format",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return None
                
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in get_session",
                session_id=session_id if 'session_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return None
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update session fields.
        
        Args:
            session_id: Session ID
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False if session not found
        """
        try:
            # Validate inputs
            if not session_id or not session_id.strip():
                safe_log(
                    logger,
                    logger.WARNING,
                    "Empty session_id in update_session",
                    session_id=session_id or "none"
                )
                return False
            
            if not updates:
                safe_log(
                    logger,
                    logger.WARNING,
                    "Empty updates in update_session",
                    session_id=session_id
                )
                return False
            
            session_id = session_id.strip()
            key = self._get_key(session_id)
            
            # Get existing session
            try:
                session_json = self.redis_client.get(key)
            except (ConnectionError, TimeoutError) as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Redis connection error in update_session",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return False
            except RedisError as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Redis error in update_session",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return False
            
            if not session_json:
                safe_log(
                    logger,
                    logger.WARNING,
                    "Session not found for update",
                    session_id=session_id
                )
                return False
            
            try:
                session_data = json.loads(session_json)
            except (json.JSONDecodeError, KeyError) as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Invalid session data format in update_session",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return False
            
            # Update fields
            for key_path, value in updates.items():
                if key_path == "context":
                    # Merge context updates
                    if isinstance(value, dict) and isinstance(session_data.get("context"), dict):
                        session_data["context"].update(value)
                    else:
                        session_data["context"] = value
                else:
                    session_data[key_path] = value
            
            # Update updated_at
            session_data["updated_at"] = datetime.utcnow().isoformat()
            
            # Get remaining TTL
            try:
                ttl = self.redis_client.ttl(key)
                if ttl <= 0:
                    # Session expired, use default TTL
                    ttl = self.default_ttl
            except Exception:
                ttl = self.default_ttl
            
            # Save updated session
            try:
                self.redis_client.setex(
                    key,
                    ttl,
                    json.dumps(session_data)
                )
            except (ConnectionError, TimeoutError) as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Redis connection error saving updated session",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return False
            except RedisError as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Redis error saving updated session",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return False
            
            safe_log(
                logger,
                logging.INFO,
                "Session updated",
                session_id=session_id,
                updated_fields=list(updates.keys())
            )
            
            return True
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in update_session",
                session_id=session_id if 'session_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if successful, False if session not found
        """
        try:
            # Validate input
            if not session_id or not session_id.strip():
                safe_log(
                    logger,
                    logger.WARNING,
                    "Empty session_id in delete_session",
                    session_id=session_id or "none"
                )
                return False
            
            session_id = session_id.strip()
            key = self._get_key(session_id)
            
            try:
                deleted = self.redis_client.delete(key)
            except (ConnectionError, TimeoutError) as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Redis connection error in delete_session",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return False
            except RedisError as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Redis error in delete_session",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return False
            
            if deleted > 0:
                safe_log(
                    logger,
                    logging.INFO,
                    "Session deleted",
                    session_id=session_id
                )
                return True
            else:
                safe_log(
                    logger,
                    logger.DEBUG,
                    "Session not found for deletion",
                    session_id=session_id
                )
                return False
                
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in delete_session",
                session_id=session_id if 'session_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return False
    
    def extend_session_ttl(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """
        Extend session TTL.
        
        Args:
            session_id: Session ID
            ttl: New TTL in seconds (default: uses default_ttl)
            
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
            key = self._get_key(session_id)
            
            # Use provided TTL or default
            new_ttl = ttl if ttl is not None else self.default_ttl
            
            # Check if session exists
            try:
                exists = self.redis_client.exists(key)
            except (ConnectionError, TimeoutError) as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Redis connection error checking session existence",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return False
            except RedisError as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Redis error checking session existence",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return False
            
            if not exists:
                safe_log(
                    logger,
                    logger.WARNING,
                    "Session not found for TTL extension",
                    session_id=session_id
                )
                return False
            
            # Get session data to update expires_at
            try:
                session_json = self.redis_client.get(key)
                if session_json:
                    session_data = json.loads(session_json)
                    now = datetime.utcnow()
                    session_data["expires_at"] = (now + timedelta(seconds=new_ttl)).isoformat()
                    session_data["updated_at"] = now.isoformat()
                    
                    # Update with new TTL
                    self.redis_client.setex(
                        key,
                        new_ttl,
                        json.dumps(session_data)
                    )
                else:
                    # Just extend TTL without updating data
                    self.redis_client.expire(key, new_ttl)
            except (ConnectionError, TimeoutError) as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Redis connection error extending session TTL",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return False
            except RedisError as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Redis error extending session TTL",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return False
            
            safe_log(
                logger,
                logging.INFO,
                "Session TTL extended",
                session_id=session_id,
                new_ttl=new_ttl
            )
            
            return True
            
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

