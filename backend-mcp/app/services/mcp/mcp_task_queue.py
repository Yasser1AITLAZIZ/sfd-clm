"""Async task queue for MCP requests using Celery or RQ"""
from typing import Dict, Any, Optional
import logging
import uuid
from datetime import datetime

from app.core.logging import get_logger, safe_log
from app.core.config import settings
from app.models.schemas import (
    MCPMessageSchema,
    TaskStatusSchema,
    TaskResponseSchema
)

logger = get_logger(__name__)

# For now, use in-memory task storage (will be replaced with Celery/RQ)
_task_storage: Dict[str, Dict[str, Any]] = {}


class MCPTaskQueue:
    """Task queue for async MCP requests"""
    
    def __init__(self):
        """Initialize task queue"""
        safe_log(
            logger,
            logging.INFO,
            "MCPTaskQueue initialized"
        )
    
    async def enqueue_request(
        self,
        mcp_message: MCPMessageSchema
    ) -> str:
        """
        Enqueue MCP request for async processing.
        
        Args:
            mcp_message: MCP message schema
            
        Returns:
            Task ID
        """
        try:
            task_id = str(uuid.uuid4())
            
            # Store task
            _task_storage[task_id] = {
                "task_id": task_id,
                "status": "pending",
                "message": mcp_message.model_dump() if hasattr(mcp_message, 'model_dump') else {},
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "result": None,
                "error": None
            }
            
            safe_log(
                logger,
                logging.INFO,
                "Request enqueued",
                task_id=task_id,
                message_id=mcp_message.message_id if mcp_message else "unknown"
            )
            
            # TODO: In production, use Celery/RQ to process task asynchronously
            # For now, just return task_id
            
            return task_id
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error enqueuing request",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error"
            )
            raise
    
    async def check_task_status(self, task_id: str) -> TaskStatusSchema:
        """
        Check status of task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status schema
        """
        try:
            if task_id not in _task_storage:
                safe_log(
                    logger,
                    logging.WARNING,
                    "Task not found",
                    task_id=task_id
                )
                return TaskStatusSchema(
                    task_id=task_id,
                    status="not_found",
                    message="Task not found"
                )
            
            task = _task_storage[task_id]
            
            status_schema = TaskStatusSchema(
                task_id=task_id,
                status=task.get("status", "unknown"),
                message=task.get("error"),
                result=task.get("result"),
                created_at=task.get("created_at"),
                updated_at=task.get("updated_at")
            )
            
            return status_schema
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error checking task status",
                task_id=task_id,
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return TaskStatusSchema(
                task_id=task_id,
                status="error",
                message=str(e) if e else "Unknown error"
            )
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Update task status.
        
        Args:
            task_id: Task ID
            status: New status (pending, processing, completed, failed)
            result: Task result (if completed)
            error: Error message (if failed)
            
        Returns:
            True if updated successfully
        """
        try:
            if task_id not in _task_storage:
                safe_log(
                    logger,
                    logging.WARNING,
                    "Task not found for update",
                    task_id=task_id
                )
                return False
            
            _task_storage[task_id].update({
                "status": status,
                "result": result,
                "error": error,
                "updated_at": datetime.utcnow().isoformat()
            })
            
            safe_log(
                logger,
                logging.INFO,
                "Task status updated",
                task_id=task_id,
                status=status
            )
            
            return True
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error updating task status",
                task_id=task_id,
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return False

