"""Workflow step storage with SQLite backend"""
import json
import uuid
import logging
import traceback
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.logging import get_logger, safe_log
from app.core.exceptions import SessionStorageError

logger = get_logger(__name__)


class WorkflowStepStorage:
    """SQLite-based workflow step storage with CRUD operations"""
    
    def __init__(self, db_path: str):
        """
        Initialize workflow step storage with SQLite database.
        
        Args:
            db_path: Path to SQLite database file (e.g., data/sessions.db)
        """
        try:
            self.db_path = db_path
            
            # Create data directory if it doesn't exist
            db_file = Path(db_path)
            db_dir = db_file.parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize database
            self._init_database()
            
            safe_log(
                logger,
                logging.INFO,
                "WorkflowStepStorage initialized",
                db_path=db_path
            )
        except sqlite3.Error as e:
            error_msg = str(e) if e else "Unknown"
            safe_log(
                logger,
                logging.ERROR,
                "Failed to initialize workflow steps database",
                db_path=db_path,
                error_type=type(e).__name__,
                error_message=error_msg,
                traceback=traceback.format_exc()
            )
            raise SessionStorageError(f"Failed to initialize workflow steps database: {error_msg}") from e
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error initializing WorkflowStepStorage",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown",
                traceback=traceback.format_exc()
            )
            raise SessionStorageError(f"Unexpected error initializing WorkflowStepStorage: {e}") from e
    
    def _init_database(self):
        """Initialize database schema for workflow_steps table"""
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                # Enable foreign keys for ON DELETE CASCADE to work
                conn.execute("PRAGMA foreign_keys = ON")
                # Create workflow_steps table if it doesn't exist
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
                
                conn.commit()
                
                safe_log(
                    logger,
                    logging.INFO,
                    "Workflow steps table initialized",
                    db_path=self.db_path
                )
        except sqlite3.Error as e:
            raise SessionStorageError(f"Failed to initialize workflow steps schema: {e}") from e
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get SQLite connection with proper settings"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys for ON DELETE CASCADE to work
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def create_workflow_step(
        self,
        session_id: str,
        workflow_id: str,
        step_name: str,
        step_order: int,
        input_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new workflow step.
        
        Args:
            session_id: Session ID
            workflow_id: Workflow ID
            step_name: Name of the step (e.g., 'validation_routing', 'preprocessing')
            step_order: Order of execution (1, 2, 3, ...)
            input_data: Optional input data dictionary
            
        Returns:
            step_id: Generated step ID (UUID v4)
        """
        try:
            # Validate inputs
            if not session_id or not session_id.strip():
                raise SessionStorageError("session_id cannot be None or empty")
            if not workflow_id or not workflow_id.strip():
                raise SessionStorageError("workflow_id cannot be None or empty")
            if not step_name or not step_name.strip():
                raise SessionStorageError("step_name cannot be None or empty")
            
            session_id = session_id.strip()
            workflow_id = workflow_id.strip()
            step_name = step_name.strip()
            
            # Generate step ID
            step_id = str(uuid.uuid4())
            
            # Extract input data
            input_record_id = input_data.get("record_id") if input_data else None
            input_user_message = input_data.get("user_message") if input_data else None
            input_documents_count = None
            input_fields_count = None
            input_prompt = None
            input_context = None
            
            if input_data:
                # Extract documents count
                if "documents_count" in input_data:
                    # Use explicit count if provided
                    input_documents_count = input_data["documents_count"]
                elif "documents" in input_data:
                    docs = input_data["documents"]
                    input_documents_count = len(docs) if isinstance(docs, (list, dict)) else None
                elif "salesforce_data" in input_data:
                    salesforce_data = input_data["salesforce_data"]
                    if isinstance(salesforce_data, dict) and "documents" in salesforce_data:
                        docs = salesforce_data["documents"]
                        input_documents_count = len(docs) if isinstance(docs, list) else None
                    elif hasattr(salesforce_data, 'documents'):
                        docs = salesforce_data.documents
                        input_documents_count = len(docs) if isinstance(docs, list) else None
                
                # Extract fields count - prioritize explicit count, then calculate from data
                if "fields_count" in input_data:
                    # Use explicit count if provided
                    input_fields_count = input_data["fields_count"]
                elif "form_json" in input_data:
                    form_json = input_data["form_json"]
                    input_fields_count = len(form_json) if isinstance(form_json, list) else None
                elif "fields" in input_data:
                    fields = input_data["fields"]
                    input_fields_count = len(fields) if isinstance(fields, (list, dict)) else None
                elif "fields_dictionary" in input_data:
                    fields = input_data["fields_dictionary"]
                    input_fields_count = len(fields) if isinstance(fields, dict) else None
                elif "salesforce_data" in input_data:
                    salesforce_data = input_data["salesforce_data"]
                    if isinstance(salesforce_data, dict):
                        # Try fields_to_fill first, then fields
                        if "fields_to_fill" in salesforce_data:
                            fields = salesforce_data["fields_to_fill"]
                            input_fields_count = len(fields) if isinstance(fields, list) else None
                        elif "fields" in salesforce_data:
                            fields = salesforce_data["fields"]
                            input_fields_count = len(fields) if isinstance(fields, list) else None
                    elif hasattr(salesforce_data, 'fields_to_fill'):
                        fields = salesforce_data.fields_to_fill
                        input_fields_count = len(fields) if isinstance(fields, list) else None
                    elif hasattr(salesforce_data, 'fields'):
                        fields = salesforce_data.fields
                        input_fields_count = len(fields) if isinstance(fields, list) else None
                
                # Extract prompt
                input_prompt = input_data.get("prompt")
                
                # Extract context (as JSON string)
                if "context" in input_data:
                    input_context = json.dumps(input_data["context"]) if input_data["context"] else None
                
                # Store salesforce_data as JSON string if present
                if "salesforce_data" in input_data:
                    salesforce_data = input_data["salesforce_data"]
                    # Convert to dict if it's a Pydantic model
                    if hasattr(salesforce_data, 'model_dump'):
                        salesforce_data = salesforce_data.model_dump()
                    # Store as JSON string in a separate field (we'll need to add this column)
                    # For now, we'll include it in input_context or create a new field
            
            # Store in SQLite
            now = datetime.utcnow().isoformat()
            try:
                safe_log(
                    logger,
                    logging.DEBUG,
                    "Inserting workflow step into database",
                    step_id=step_id,
                    session_id=session_id,
                    workflow_id=workflow_id,
                    step_name=step_name,
                    step_order=step_order,
                    db_path=self.db_path
                )
                
                with self._get_connection() as conn:
                    # Check if table exists
                    cursor = conn.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name='workflow_steps'
                    """)
                    table_exists = cursor.fetchone() is not None
                    
                    if not table_exists:
                        safe_log(
                            logger,
                            logging.ERROR,
                            "workflow_steps table does not exist",
                            db_path=self.db_path,
                            step_id=step_id,
                            step_name=step_name
                        )
                        # Try to create the table
                        self._init_database()
                    
                    # Disable FOREIGN KEY constraint temporarily if session_id starts with "workflow-"
                    # This allows creating steps before the session is created
                    if session_id.startswith("workflow-"):
                        conn.execute("PRAGMA foreign_keys = OFF")
                    
                    try:
                        conn.execute("""
                            INSERT INTO workflow_steps (
                                step_id, session_id, workflow_id, step_name, step_order, status,
                                input_record_id, input_user_message, input_documents_count, 
                                input_fields_count, input_prompt, input_context,
                                started_at
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            step_id,
                            session_id,
                            workflow_id,
                            step_name,
                            step_order,
                            "pending",
                            input_record_id,
                            input_user_message,
                            input_documents_count,
                            input_fields_count,
                            input_prompt,
                            input_context,
                            now
                        ))
                        conn.commit()
                    finally:
                        # Re-enable FOREIGN KEY constraint
                        if session_id.startswith("workflow-"):
                            conn.execute("PRAGMA foreign_keys = ON")
                    
                    safe_log(
                        logger,
                        logging.DEBUG,
                        "Workflow step inserted successfully",
                        step_id=step_id,
                        session_id=session_id,
                        step_name=step_name
                    )
            except sqlite3.Error as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "SQLite error creating workflow step",
                    step_id=step_id,
                    step_name=step_name,
                    session_id=session_id,
                    workflow_id=workflow_id,
                    db_path=self.db_path,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown",
                    traceback=traceback.format_exc()
                )
                raise SessionStorageError(f"SQLite error creating workflow step: {e}") from e
            
            safe_log(
                logger,
                logging.INFO,
                "Workflow step created",
                step_id=step_id,
                step_name=step_name,
                step_order=step_order,
                workflow_id=workflow_id
            )
            
            return step_id
            
        except SessionStorageError:
            raise
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error creating workflow step",
                step_name=step_name if 'step_name' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown",
                traceback=traceback.format_exc()
            )
            raise SessionStorageError(f"Unexpected error creating workflow step: {e}") from e
    
    def update_workflow_step(
        self,
        step_id: str,
        status: str,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        processing_time: Optional[float] = None
    ) -> bool:
        """
        Update a workflow step with outputs and status.
        
        Args:
            step_id: Step ID
            status: Status ('in_progress', 'completed', 'failed')
            output_data: Optional output data dictionary
            error_message: Optional error message
            error_details: Optional error details dictionary
            processing_time: Optional processing time in seconds
            
        Returns:
            True if successful, False if step not found
        """
        try:
            if not step_id or not step_id.strip():
                safe_log(
                    logger,
                    logging.WARNING,
                    "Empty step_id in update_workflow_step",
                    step_id=step_id or "none"
                )
                return False
            
            step_id = step_id.strip()
            
            # Extract output data
            output_extracted_fields_count = None
            output_confidence_avg = None
            output_status = status
            output_error_message = error_message
            output_data_json = None
            
            if output_data:
                # Extract fields count
                if "extracted_data" in output_data:
                    extracted_data = output_data["extracted_data"]
                    output_extracted_fields_count = len(extracted_data) if isinstance(extracted_data, dict) else None
                
                # Extract confidence average
                if "confidence_scores" in output_data:
                    confidence_scores = output_data["confidence_scores"]
                    if isinstance(confidence_scores, dict) and len(confidence_scores) > 0:
                        values = [v for v in confidence_scores.values() if isinstance(v, (int, float))]
                        if values:
                            output_confidence_avg = sum(values) / len(values)
                
                # Store output_data as JSON
                output_data_json = json.dumps(output_data) if output_data else None
            
            # Store error_details as JSON
            error_details_json = json.dumps(error_details) if error_details else None
            
            # Update in SQLite
            now = datetime.utcnow().isoformat()
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute("""
                        UPDATE workflow_steps
                        SET status = ?,
                            output_extracted_fields_count = ?,
                            output_confidence_avg = ?,
                            output_status = ?,
                            output_error_message = ?,
                            output_data = ?,
                            completed_at = ?,
                            processing_time = ?,
                            error_details = ?
                        WHERE step_id = ?
                    """, (
                        status,
                        output_extracted_fields_count,
                        output_confidence_avg,
                        output_status,
                        output_error_message,
                        output_data_json,
                        now if status in ("completed", "failed") else None,
                        processing_time,
                        error_details_json,
                        step_id
                    ))
                    
                    if cursor.rowcount == 0:
                        safe_log(
                            logger,
                            logging.WARNING,
                            "Workflow step not found for update",
                            step_id=step_id
                        )
                        return False
                    
                    conn.commit()
                    
                    safe_log(
                        logger,
                        logging.INFO,
                        "Workflow step updated",
                        step_id=step_id,
                        status=status,
                        processing_time=processing_time
                    )
                    return True
            except sqlite3.Error as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "SQLite error updating workflow step",
                    step_id=step_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown",
                    traceback=traceback.format_exc()
                )
                return False
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error updating workflow step",
                step_id=step_id if 'step_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown",
                traceback=traceback.format_exc()
            )
            return False
    
    def get_workflow_steps(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Get all workflow steps for a workflow.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            List of workflow step dictionaries
        """
        try:
            if not workflow_id or not workflow_id.strip():
                return []
            
            workflow_id = workflow_id.strip()
            
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute("""
                        SELECT * FROM workflow_steps
                        WHERE workflow_id = ?
                        ORDER BY step_order
                    """, (workflow_id,))
                    
                    steps = []
                    for row in cursor.fetchall():
                        step = dict(row)
                        # Parse JSON fields
                        if step.get("input_context"):
                            try:
                                step["input_context"] = json.loads(step["input_context"])
                            except json.JSONDecodeError:
                                pass
                        if step.get("output_data"):
                            try:
                                step["output_data"] = json.loads(step["output_data"])
                            except json.JSONDecodeError:
                                pass
                        if step.get("error_details"):
                            try:
                                step["error_details"] = json.loads(step["error_details"])
                            except json.JSONDecodeError:
                                pass
                        steps.append(step)
                    
                    return steps
            except sqlite3.Error as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "SQLite error getting workflow steps",
                    workflow_id=workflow_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return []
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error getting workflow steps",
                workflow_id=workflow_id if 'workflow_id' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return []
    
    def get_step_by_name(
        self,
        workflow_id: str,
        step_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific workflow step by name.
        
        Args:
            workflow_id: Workflow ID
            step_name: Step name
            
        Returns:
            Workflow step dictionary or None if not found
        """
        try:
            if not workflow_id or not workflow_id.strip():
                return None
            if not step_name or not step_name.strip():
                return None
            
            workflow_id = workflow_id.strip()
            step_name = step_name.strip()
            
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute("""
                        SELECT * FROM workflow_steps
                        WHERE workflow_id = ? AND step_name = ?
                        ORDER BY step_order DESC
                        LIMIT 1
                    """, (workflow_id, step_name))
                    
                    row = cursor.fetchone()
                    if row:
                        step = dict(row)
                        # Parse JSON fields
                        if step.get("input_context"):
                            try:
                                step["input_context"] = json.loads(step["input_context"])
                            except json.JSONDecodeError:
                                pass
                        if step.get("output_data"):
                            try:
                                step["output_data"] = json.loads(step["output_data"])
                            except json.JSONDecodeError:
                                pass
                        if step.get("error_details"):
                            try:
                                step["error_details"] = json.loads(step["error_details"])
                            except json.JSONDecodeError:
                                pass
                        return step
                    return None
            except sqlite3.Error as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "SQLite error getting workflow step by name",
                    workflow_id=workflow_id,
                    step_name=step_name,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                return None
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error getting workflow step by name",
                workflow_id=workflow_id if 'workflow_id' in locals() else "unknown",
                step_name=step_name if 'step_name' in locals() else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return None
    
    def get_recent_workflows(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get list of recent workflows with their status and metadata.
        
        Args:
            limit: Maximum number of workflows to return
            
        Returns:
            List of workflow dictionaries with workflow_id, status, started_at, completed_at, record_id
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT
                        workflow_id,
                        MIN(started_at) as started_at,
                        MAX(CASE WHEN status = 'completed' THEN completed_at END) as completed_at,
                        MAX(CASE WHEN step_name = 'validation_routing' THEN input_record_id END) as record_id,
                        CASE 
                            WHEN COUNT(CASE WHEN status = 'failed' THEN 1 END) > 0 THEN 'failed'
                            WHEN COUNT(CASE WHEN status = 'in_progress' THEN 1 END) > 0 THEN 'in_progress'
                            WHEN COUNT(CASE WHEN status = 'completed' THEN 1 END) = COUNT(*) THEN 'completed'
                            ELSE 'pending'
                        END as status
                    FROM workflow_steps
                    GROUP BY workflow_id
                    ORDER BY started_at DESC
                    LIMIT ?
                """, (limit,))
                
                workflows = []
                for row in cursor.fetchall():
                    workflows.append({
                        "workflow_id": row[0],
                        "status": row[4],
                        "started_at": row[1],
                        "completed_at": row[2],
                        "record_id": row[3] or "unknown"
                    })
                
                safe_log(
                    logger,
                    logging.INFO,
                    "Recent workflows retrieved",
                    count=len(workflows),
                    limit=limit
                )
                
                return workflows
        except sqlite3.Error as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error retrieving recent workflows",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error"
            )
            return []
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error retrieving recent workflows",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error",
                traceback=traceback.format_exc()
            )
            return []

