"""Session storage with SQLite backend"""
import json
import uuid
import logging
import traceback
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.core.logging import get_logger, safe_log
from app.core.exceptions import SessionStorageError

logger = get_logger(__name__)


class SessionStorage:
    """SQLite-based session storage with CRUD operations"""
    
    def __init__(self, db_path: str, default_ttl: int = 86400):
        """
        Initialize session storage with SQLite database.
        
        Args:
            db_path: Path to SQLite database file (e.g., data/sessions.db)
            default_ttl: Default TTL in seconds (default: 86400 = 24 hours)
        """
        try:
            self.db_path = db_path
            self.default_ttl = default_ttl
            
            # Create data directory if it doesn't exist
            db_file = Path(db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize database
            self._init_database()
            
            safe_log(
                logger,
                logging.INFO,
                "SessionStorage initialized",
                db_path=db_path,
                default_ttl=default_ttl
            )
        except sqlite3.Error as e:
            error_msg = str(e) if e else "Unknown"
            safe_log(
                logger,
                logging.ERROR,
                "Failed to initialize SQLite database",
                db_path=db_path,
                error_type=type(e).__name__,
                error_message=error_msg,
                traceback=traceback.format_exc()
            )
            raise SessionStorageError(f"Failed to initialize SQLite database: {error_msg}") from e
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error initializing SessionStorage",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown",
                traceback=traceback.format_exc()
            )
            raise SessionStorageError(f"Unexpected error initializing SessionStorage: {e}") from e
    
    def _init_database(self):
        """Initialize database schema"""
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        record_id TEXT NOT NULL,
                        data TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_expires_at ON sessions(expires_at)
                """)
                conn.commit()
        except sqlite3.Error as e:
            raise SessionStorageError(f"Failed to initialize database schema: {e}") from e
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get SQLite connection with proper settings"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _cleanup_expired_sessions(self, conn: sqlite3.Connection):
        """Clean up expired sessions"""
        try:
            now = datetime.utcnow().isoformat()
            cursor = conn.execute(
                "DELETE FROM sessions WHERE expires_at < ?",
                (now,)
            )
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                conn.commit()
                safe_log(
                    logger,
                    logging.DEBUG,
                    "Cleaned up expired sessions",
                    deleted_count=deleted_count
                )
        except sqlite3.Error as e:
            safe_log(
                logger,
                logging.WARNING,
                "Error cleaning up expired sessions",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            # Don't raise, just log the warning
    
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

            # Serialize session data to JSON
            try:
                session_json = json.dumps(session_data)
            except (TypeError, ValueError) as json_error:
                safe_log(
                    logger,
                    logging.ERROR,
                    "JSON serialization error in create_session",
                    session_id=session_id,
                    record_id=record_id,
                    error_type=type(json_error).__name__,
                    error_message=str(json_error) if json_error else "Unknown",
                    traceback=traceback.format_exc()
                )
                raise SessionStorageError(f"Failed to serialize session data to JSON: {json_error}") from json_error
            
            # Store in SQLite
            try:
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT INTO sessions (session_id, record_id, data, created_at, updated_at, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        record_id,
                        session_json,
                        now.isoformat(),
                        now.isoformat(),
                        expires_at.isoformat()
                    ))
                    conn.commit()
            except sqlite3.IntegrityError as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Session ID collision in create_session",
                    session_id=session_id,
                    record_id=record_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                raise SessionStorageError(f"Session ID collision: {e}") from e
            except sqlite3.Error as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "SQLite error in create_session",
                    session_id=session_id,
                    record_id=record_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown",
                    traceback=traceback.format_exc()
                )
                raise SessionStorageError(f"SQLite error creating session: {e}") from e
            
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
                error_message=str(e) if e else "Unknown",
                traceback=traceback.format_exc()
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
                    logging.WARNING,
                    "Empty session_id in get_session",
                    session_id=session_id or "none"
                )
                return None
            
            session_id = session_id.strip()
            
            try:
                with self._get_connection() as conn:
                    # Clean up expired sessions periodically
                    self._cleanup_expired_sessions(conn)
                    
                    # Get session
                    now = datetime.utcnow().isoformat()
                    cursor = conn.execute("""
                        SELECT data, expires_at FROM sessions
                        WHERE session_id = ? AND expires_at > ?
                    """, (session_id, now))
                    
                    row = cursor.fetchone()
                    
                    if not row:
                        safe_log(
                            logger,
                            logging.DEBUG,
                            "Session not found or expired",
                            session_id=session_id
                        )
                        return None
                    
                    session_json = row[0]
                    
                    try:
                        session_data = json.loads(session_json)
                        safe_log(
                            logger,
                            logging.DEBUG,
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
            except sqlite3.Error as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "SQLite error in get_session",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown",
                    traceback=traceback.format_exc()
                )
                return None
                
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in get_session",
                session_id=session_id if 'session_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown",
                traceback=traceback.format_exc()
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
                    logging.WARNING,
                    "Empty session_id in update_session",
                    session_id=session_id or "none"
                )
                return False
            
            if not updates:
                safe_log(
                    logger,
                    logging.WARNING,
                    "Empty updates in update_session",
                    session_id=session_id
                )
                return False
            
            session_id = session_id.strip()
            
            try:
                with self._get_connection() as conn:
                    # Get existing session
                    now = datetime.utcnow().isoformat()
                    cursor = conn.execute("""
                        SELECT data, expires_at FROM sessions
                        WHERE session_id = ? AND expires_at > ?
                    """, (session_id, now))
                    
                    row = cursor.fetchone()
                    
                    if not row:
                        safe_log(
                            logger,
                            logging.WARNING,
                            "Session not found for update",
                            session_id=session_id
                        )
                        return False
                    
                    session_json = row[0]
                    expires_at_str = row[1]
                    
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
                    session_data["updated_at"] = now
                    
                    # Calculate remaining TTL from expires_at
                    expires_at = datetime.fromisoformat(expires_at_str)
                    remaining_seconds = int((expires_at - datetime.fromisoformat(now)).total_seconds())
                    
                    if remaining_seconds <= 0:
                        # Session expired, use default TTL
                        new_expires_at = datetime.fromisoformat(now) + timedelta(seconds=self.default_ttl)
                    else:
                        # Keep existing expiration
                        new_expires_at = expires_at
                    
                    # Save updated session
                    updated_json = json.dumps(session_data)
                    conn.execute("""
                        UPDATE sessions
                        SET data = ?, updated_at = ?, expires_at = ?
                        WHERE session_id = ?
                    """, (
                        updated_json,
                        now,
                        new_expires_at.isoformat(),
                        session_id
                    ))
                    conn.commit()
                    
                    safe_log(
                        logger,
                        logging.INFO,
                        "Session updated",
                        session_id=session_id,
                        updated_fields=list(updates.keys())
                    )
                    
                    return True
            except sqlite3.Error as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "SQLite error in update_session",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown",
                    traceback=traceback.format_exc()
                )
                return False
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in update_session",
                session_id=session_id if 'session_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown",
                traceback=traceback.format_exc()
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
                    logging.WARNING,
                    "Empty session_id in delete_session",
                    session_id=session_id or "none"
                )
                return False
            
            session_id = session_id.strip()
            
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "DELETE FROM sessions WHERE session_id = ?",
                        (session_id,)
                    )
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    if deleted_count > 0:
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
                            logging.DEBUG,
                            "Session not found for deletion",
                            session_id=session_id
                        )
                        return False
            except sqlite3.Error as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "SQLite error in delete_session",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown",
                    traceback=traceback.format_exc()
                )
                return False
                
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in delete_session",
                session_id=session_id if 'session_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown",
                traceback=traceback.format_exc()
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
                    logging.WARNING,
                    "Empty session_id in extend_session_ttl",
                    session_id=session_id or "none"
                )
                return False
            
            session_id = session_id.strip()
            
            # Use provided TTL or default
            new_ttl = ttl if ttl is not None else self.default_ttl
            
            try:
                with self._get_connection() as conn:
                    # Check if session exists and get current data
                    now = datetime.utcnow().isoformat()
                    cursor = conn.execute("""
                        SELECT data, expires_at FROM sessions
                        WHERE session_id = ? AND expires_at > ?
                    """, (session_id, now))
                    
                    row = cursor.fetchone()
                    
                    if not row:
                        safe_log(
                            logger,
                            logging.WARNING,
                            "Session not found for TTL extension",
                            session_id=session_id
                        )
                        return False
                    
                    session_json = row[0]
                    new_expires_at = datetime.fromisoformat(now) + timedelta(seconds=new_ttl)
                    
                    # Update session data with new expires_at
                    try:
                        session_data = json.loads(session_json)
                        session_data["expires_at"] = new_expires_at.isoformat()
                        session_data["updated_at"] = now
                        updated_json = json.dumps(session_data)
                    except (json.JSONDecodeError, KeyError):
                        # If we can't parse, just update expires_at
                        updated_json = session_json
                    
                    # Update expires_at in database
                    conn.execute("""
                        UPDATE sessions
                        SET data = ?, updated_at = ?, expires_at = ?
                        WHERE session_id = ?
                    """, (
                        updated_json,
                        now,
                        new_expires_at.isoformat(),
                        session_id
                    ))
                    conn.commit()
                    
                    safe_log(
                        logger,
                        logging.INFO,
                        "Session TTL extended",
                        session_id=session_id,
                        new_ttl=new_ttl
                    )
                    
                    return True
            except sqlite3.Error as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "SQLite error extending session TTL",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown",
                    traceback=traceback.format_exc()
                )
                return False
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in extend_session_ttl",
                session_id=session_id if 'session_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown",
                traceback=traceback.format_exc()
            )
            return False
