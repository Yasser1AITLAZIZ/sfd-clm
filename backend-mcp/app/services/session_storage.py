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
from app.models.schemas import (
    SessionInputDataSchema,
    LanggraphResponseDataSchema,
    InteractionHistoryItemSchema,
    ProcessingMetadataSchema,
    RefactoredSessionSchema
)

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
            db_dir = db_file.parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            # Ensure directory is writable (important for Docker volumes)
            try:
                # Test write permissions by creating a temporary file
                test_file = db_dir / ".write_test"
                test_file.touch()
                test_file.unlink()
            except (PermissionError, OSError) as perm_error:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Cannot write to data directory",
                    db_path=str(db_dir),
                    error_type=type(perm_error).__name__,
                    error_message=str(perm_error) if perm_error else "Unknown"
                )
                raise SessionStorageError(f"Cannot write to data directory {db_dir}: {perm_error}") from perm_error
            
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
        """Initialize database schema with refactored structure"""
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                # Enable foreign keys for ON DELETE CASCADE to work
                conn.execute("PRAGMA foreign_keys = ON")
                # Check if old structure exists (has 'data' column but not 'input_data')
                cursor = conn.execute("PRAGMA table_info(sessions)")
                columns = [row[1] for row in cursor.fetchall()]
                
                old_structure = "data" in columns and "input_data" not in columns
                new_structure = "input_data" in columns
                
                if old_structure:
                    # Old structure detected - drop and recreate
                    safe_log(
                        logger,
                        logging.WARNING,
                        "Old session table structure detected. Dropping and recreating with new structure.",
                        db_path=self.db_path
                    )
                    conn.execute("DROP TABLE IF EXISTS sessions")
                    conn.commit()
                
                # Create new refactored table structure
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        record_id TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'active',
                        input_data TEXT NOT NULL,
                        langgraph_response TEXT,
                        interactions_history TEXT,
                        processing_metadata TEXT
                    )
                """)
                # Create indexes for performance
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_expires_at ON sessions(expires_at)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_record_id ON sessions(record_id)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_status ON sessions(status)
                """)
                
                # Initialize workflow_steps table
                self._init_workflow_steps_table(conn)
                
                conn.commit()
                
                if old_structure:
                    safe_log(
                        logger,
                        logging.INFO,
                        "Session table recreated with new refactored structure",
                        db_path=self.db_path
                    )
        except sqlite3.Error as e:
            raise SessionStorageError(f"Failed to initialize database schema: {e}") from e
    
    def _init_workflow_steps_table(self, conn: sqlite3.Connection):
        """Initialize workflow_steps table if it doesn't exist"""
        try:
            # Check if table already exists
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='workflow_steps'
            """)
            if cursor.fetchone():
                # Table exists, skip creation
                return
            
            # Create workflow_steps table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_steps (
                    step_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    step_order INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    
                    -- Inputs (colonnes séparées pour lisibilité)
                    input_record_id TEXT,
                    input_user_message TEXT,
                    input_documents_count INTEGER,
                    input_fields_count INTEGER,
                    input_prompt TEXT,
                    input_context TEXT,
                    
                    -- Outputs (colonnes séparées pour lisibilité)
                    output_extracted_fields_count INTEGER,
                    output_confidence_avg REAL,
                    output_status TEXT,
                    output_error_message TEXT,
                    output_data TEXT,
                    
                    -- Métadonnées
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    processing_time REAL,
                    error_details TEXT,
                    
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_workflow_steps_session 
                ON workflow_steps(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_workflow_steps_workflow 
                ON workflow_steps(workflow_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_workflow_steps_step_name 
                ON workflow_steps(step_name)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_workflow_steps_status 
                ON workflow_steps(status)
            """)
            
            safe_log(
                logger,
                logging.INFO,
                "Workflow steps table initialized",
                db_path=self.db_path
            )
        except sqlite3.Error as e:
            safe_log(
                logger,
                logging.WARNING,
                "Failed to initialize workflow_steps table (will be created on first use)",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            # Don't raise - allow workflow to continue without workflow_steps table
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get SQLite connection with proper settings"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys for ON DELETE CASCADE to work
        conn.execute("PRAGMA foreign_keys = ON")
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
    
    def create_session(
        self,
        record_id: str,
        input_data: Dict[str, Any],
        status: str = "active"
    ) -> str:
        """
        Create a new session with refactored structure.
        
        Args:
            record_id: Salesforce record ID
            input_data: Input data dictionary (will be validated as SessionInputDataSchema)
            status: Session status (default: "active")
            
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
            
            if not input_data:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Empty input_data in create_session",
                    record_id=record_id
                )
                raise SessionStorageError("input_data cannot be None or empty")

            record_id = record_id.strip()
            
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Create session timestamps
            now = datetime.utcnow()
            expires_at = now + timedelta(seconds=self.default_ttl)
            
            # Validate and serialize input_data
            try:
                input_data_schema = SessionInputDataSchema(**input_data)
                input_data_json = json.dumps(input_data_schema.model_dump(mode='json'))
            except Exception as schema_error:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Invalid input_data schema in create_session",
                    session_id=session_id,
                    record_id=record_id,
                    error_type=type(schema_error).__name__,
                    error_message=str(schema_error) if schema_error else "Unknown"
                )
                raise SessionStorageError(f"Invalid input_data schema: {schema_error}") from schema_error
            
            # Initialize empty structures
            interactions_history_json = json.dumps([])
            processing_metadata = ProcessingMetadataSchema()
            processing_metadata_json = json.dumps(processing_metadata.model_dump(mode='json'))
            
            # Store in SQLite
            try:
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT INTO sessions (
                            session_id, record_id, created_at, updated_at, expires_at,
                            status, input_data, langgraph_response, interactions_history,
                            processing_metadata
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        record_id,
                        now.isoformat(),
                        now.isoformat(),
                        expires_at.isoformat(),
                        status,
                        input_data_json,
                        None,  # langgraph_response initially null
                        interactions_history_json,
                        processing_metadata_json
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
                "Session created with refactored structure",
                session_id=session_id,
                record_id=record_id,
                ttl=self.default_ttl,
                status=status
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
        Get session by ID with refactored structure.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data dictionary (RefactoredSessionSchema format) or None if not found/expired
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
                    
                    # Get session with all columns
                    now = datetime.utcnow().isoformat()
                    cursor = conn.execute("""
                        SELECT session_id, record_id, created_at, updated_at, expires_at,
                               status, input_data, langgraph_response, interactions_history,
                               processing_metadata
                        FROM sessions
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
                    
                    # Parse JSON columns
                    try:
                        input_data = json.loads(row[6]) if row[6] else {}
                        langgraph_response = json.loads(row[7]) if row[7] else None
                        interactions_history = json.loads(row[8]) if row[8] else []
                        processing_metadata = json.loads(row[9]) if row[9] else {}
                        
                        session_data = {
                            "session_id": row[0],
                            "record_id": row[1],
                            "created_at": row[2],
                            "updated_at": row[3],
                            "expires_at": row[4],
                            "status": row[5],
                            "input_data": input_data,
                            "langgraph_response": langgraph_response,
                            "interactions_history": interactions_history,
                            "processing_metadata": processing_metadata
                        }
                        
                        safe_log(
                            logger,
                            logging.DEBUG,
                            "Session retrieved with refactored structure",
                            session_id=session_id,
                            record_id=row[1] or "unknown",
                            status=row[5]
                        )
                        return session_data
                    except (json.JSONDecodeError, KeyError, IndexError) as e:
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
    
    def store_langgraph_response(
        self,
        session_id: str,
        langgraph_response: Dict[str, Any]
    ) -> bool:
        """
        Store langgraph response in session.
        
        Args:
            session_id: Session ID
            langgraph_response: Langgraph response data dictionary
            
        Returns:
            True if successful, False if session not found
        """
        try:
            if not session_id or not session_id.strip():
                safe_log(
                    logger,
                    logging.WARNING,
                    "Empty session_id in store_langgraph_response",
                    session_id=session_id or "none"
                )
                return False
            
            session_id = session_id.strip()
            
            # Validate and serialize response
            try:
                # Normalize status if present (schema only accepts "success", "error", "partial")
                if "status" in langgraph_response:
                    status_value = langgraph_response["status"]
                    if isinstance(status_value, str):
                        status_lower = status_value.lower()
                        if status_lower not in ("success", "error", "partial"):
                            if "error" in status_lower or "fail" in status_lower:
                                langgraph_response["status"] = "error"
                            elif "partial" in status_lower or "incomplete" in status_lower:
                                langgraph_response["status"] = "partial"
                            else:
                                langgraph_response["status"] = "success"  # Default
                
                # Ensure timestamp is present (required field)
                if "timestamp" not in langgraph_response or not langgraph_response.get("timestamp"):
                    from datetime import datetime
                    langgraph_response["timestamp"] = datetime.utcnow().isoformat()
                
                response_schema = LanggraphResponseDataSchema(**langgraph_response)
                response_json = json.dumps(response_schema.model_dump(mode='json'))
            except Exception as schema_error:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Invalid langgraph_response schema",
                    session_id=session_id,
                    error_type=type(schema_error).__name__,
                    error_message=str(schema_error) if schema_error else "Unknown",
                    langgraph_response_keys=list(langgraph_response.keys()) if isinstance(langgraph_response, dict) else [],
                    langgraph_response_status=langgraph_response.get("status") if isinstance(langgraph_response, dict) else None
                )
                return False
            
            try:
                with self._get_connection() as conn:
                    now = datetime.utcnow().isoformat()
                    cursor = conn.execute("""
                        UPDATE sessions
                        SET langgraph_response = ?, updated_at = ?
                        WHERE session_id = ? AND expires_at > ?
                    """, (response_json, now, session_id, now))
                    
                    if cursor.rowcount == 0:
                        safe_log(
                            logger,
                            logging.WARNING,
                            "Session not found for storing langgraph response",
                            session_id=session_id
                        )
                        return False
                    
                    conn.commit()
                    
                    safe_log(
                        logger,
                        logging.INFO,
                        "Langgraph response stored",
                        session_id=session_id,
                        extracted_fields=len(langgraph_response.get("extracted_data", {}))
                    )
                    return True
            except sqlite3.Error as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "SQLite error storing langgraph response",
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
                "Unexpected error storing langgraph response",
                session_id=session_id if 'session_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown",
                traceback=traceback.format_exc()
            )
            return False
    
    def add_interaction_to_history(
        self,
        session_id: str,
        interaction: Dict[str, Any]
    ) -> bool:
        """
        Add an interaction to the interactions history.
        
        Args:
            session_id: Session ID
            interaction: Interaction data dictionary
            
        Returns:
            True if successful, False if session not found
        """
        try:
            if not session_id or not session_id.strip():
                safe_log(
                    logger,
                    logging.WARNING,
                    "Empty session_id in add_interaction_to_history",
                    session_id=session_id or "none"
                )
                return False
            
            session_id = session_id.strip()
            
            # Validate interaction
            try:
                interaction_schema = InteractionHistoryItemSchema(**interaction)
                interaction_dict = interaction_schema.model_dump(mode='json')
            except Exception as schema_error:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Invalid interaction schema",
                    session_id=session_id,
                    error_type=type(schema_error).__name__,
                    error_message=str(schema_error) if schema_error else "Unknown"
                )
                return False
            
            try:
                with self._get_connection() as conn:
                    now = datetime.utcnow().isoformat()
                    
                    # Get current history
                    cursor = conn.execute("""
                        SELECT interactions_history FROM sessions
                        WHERE session_id = ? AND expires_at > ?
                    """, (session_id, now))
                    
                    row = cursor.fetchone()
                    if not row:
                        safe_log(
                            logger,
                            logging.WARNING,
                            "Session not found for adding interaction",
                            session_id=session_id
                        )
                        return False
                    
                    # Parse existing history
                    try:
                        history = json.loads(row[0]) if row[0] else []
                    except json.JSONDecodeError:
                        history = []
                    
                    # Add new interaction
                    history.append(interaction_dict)
                    history_json = json.dumps(history)
                    
                    # Update session
                    conn.execute("""
                        UPDATE sessions
                        SET interactions_history = ?, updated_at = ?
                        WHERE session_id = ?
                    """, (history_json, now, session_id))
                    conn.commit()
                    
                    safe_log(
                        logger,
                        logging.INFO,
                        "Interaction added to history",
                        session_id=session_id,
                        interaction_id=interaction.get("interaction_id", "unknown"),
                        history_length=len(history)
                    )
                    return True
            except sqlite3.Error as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "SQLite error adding interaction to history",
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
                "Unexpected error adding interaction to history",
                session_id=session_id if 'session_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown",
                traceback=traceback.format_exc()
            )
            return False
    
    def update_processing_metadata(
        self,
        session_id: str,
        metadata_updates: Dict[str, Any]
    ) -> bool:
        """
        Update processing metadata in session.
        
        Args:
            session_id: Session ID
            metadata_updates: Dictionary of metadata fields to update
            
        Returns:
            True if successful, False if session not found
        """
        try:
            if not session_id or not session_id.strip():
                safe_log(
                    logger,
                    logging.WARNING,
                    "Empty session_id in update_processing_metadata",
                    session_id=session_id or "none"
                )
                return False
            
            session_id = session_id.strip()
            
            try:
                with self._get_connection() as conn:
                    now = datetime.utcnow().isoformat()
                    
                    # Get current metadata
                    cursor = conn.execute("""
                        SELECT processing_metadata FROM sessions
                        WHERE session_id = ? AND expires_at > ?
                    """, (session_id, now))
                    
                    row = cursor.fetchone()
                    if not row:
                        safe_log(
                            logger,
                            logging.WARNING,
                            "Session not found for updating metadata",
                            session_id=session_id
                        )
                        return False
                    
                    # Parse existing metadata
                    try:
                        metadata = json.loads(row[0]) if row[0] else {}
                    except json.JSONDecodeError:
                        metadata = {}
                    
                    # Update metadata
                    metadata.update(metadata_updates)
                    
                    # Validate with schema
                    try:
                        metadata_schema = ProcessingMetadataSchema(**metadata)
                        metadata_json = json.dumps(metadata_schema.model_dump(mode='json'))
                    except Exception as schema_error:
                        safe_log(
                            logger,
                            logging.WARNING,
                            "Invalid metadata schema, storing as-is",
                            session_id=session_id,
                            error_type=type(schema_error).__name__
                        )
                        metadata_json = json.dumps(metadata)
                    
                    # Update session
                    conn.execute("""
                        UPDATE sessions
                        SET processing_metadata = ?, updated_at = ?
                        WHERE session_id = ?
                    """, (metadata_json, now, session_id))
                    conn.commit()
                    
                    safe_log(
                        logger,
                        logging.INFO,
                        "Processing metadata updated",
                        session_id=session_id,
                        updated_fields=list(metadata_updates.keys())
                    )
                    return True
            except sqlite3.Error as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "SQLite error updating processing metadata",
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
                "Unexpected error updating processing metadata",
                session_id=session_id if 'session_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown",
                traceback=traceback.format_exc()
            )
            return False
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update session fields with refactored structure.
        
        Args:
            session_id: Session ID
            updates: Dictionary of fields to update (status, input_data, langgraph_response, etc.)
            
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
                        SELECT expires_at FROM sessions
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
                    
                    expires_at_str = row[0]
                    
                    # Build update query dynamically
                    update_fields = []
                    update_values = []
                    
                    # Handle status update
                    if "status" in updates:
                        update_fields.append("status = ?")
                        update_values.append(updates["status"])
                    
                    # Handle input_data update
                    if "input_data" in updates:
                        try:
                            input_data_schema = SessionInputDataSchema(**updates["input_data"])
                            input_data_json = json.dumps(input_data_schema.model_dump(mode='json'))
                            update_fields.append("input_data = ?")
                            update_values.append(input_data_json)
                        except Exception as e:
                            safe_log(
                                logger,
                                logging.ERROR,
                                "Invalid input_data in update_session",
                                session_id=session_id,
                                error_type=type(e).__name__
                            )
                            return False
                    
                    # Handle langgraph_response update
                    if "langgraph_response" in updates:
                        if updates["langgraph_response"] is None:
                            update_fields.append("langgraph_response = ?")
                            update_values.append(None)
                        else:
                            try:
                                response_schema = LanggraphResponseDataSchema(**updates["langgraph_response"])
                                response_json = json.dumps(response_schema.model_dump(mode='json'))
                                update_fields.append("langgraph_response = ?")
                                update_values.append(response_json)
                            except Exception as e:
                                safe_log(
                                    logger,
                                    logging.ERROR,
                                    "Invalid langgraph_response in update_session",
                                    session_id=session_id,
                                    error_type=type(e).__name__
                                )
                                return False
                    
                    # Always update updated_at
                    update_fields.append("updated_at = ?")
                    update_values.append(now)
                    
                    # Calculate remaining TTL
                    expires_at = datetime.fromisoformat(expires_at_str)
                    remaining_seconds = int((expires_at - datetime.fromisoformat(now)).total_seconds())
                    
                    if remaining_seconds <= 0:
                        new_expires_at = datetime.fromisoformat(now) + timedelta(seconds=self.default_ttl)
                    else:
                        new_expires_at = expires_at
                    
                    update_fields.append("expires_at = ?")
                    update_values.append(new_expires_at.isoformat())
                    
                    # Add session_id for WHERE clause
                    update_values.append(session_id)
                    
                    # Execute update
                    update_query = f"""
                        UPDATE sessions
                        SET {', '.join(update_fields)}
                        WHERE session_id = ?
                    """
                    conn.execute(update_query, update_values)
                    conn.commit()
                    
                    safe_log(
                        logger,
                        logging.INFO,
                        "Session updated with refactored structure",
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
                    # Check if session exists and get current expires_at
                    now = datetime.utcnow().isoformat()
                    cursor = conn.execute("""
                        SELECT expires_at FROM sessions
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
                    
                    new_expires_at = datetime.fromisoformat(now) + timedelta(seconds=new_ttl)
                    
                    # Update expires_at in database (no need to update JSON columns)
                    conn.execute("""
                        UPDATE sessions
                        SET updated_at = ?, expires_at = ?
                        WHERE session_id = ?
                    """, (
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
