"""Task status endpoints"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Any
import logging

from app.models.schemas import TaskStatusSchema
from app.services.mcp.mcp_task_queue import MCPTaskQueue
from app.core.logging import get_logger, safe_log

logger = get_logger(__name__)

router = APIRouter()
task_queue = MCPTaskQueue()


@router.get(
    "/api/task-status/{task_id}",
    response_model=TaskStatusSchema,
    status_code=status.HTTP_200_OK,
    summary="Get task status",
    description="Get status of async task by task_id"
)
async def get_task_status(task_id: str) -> JSONResponse:
    """
    Get task status by task_id.
    
    Args:
        task_id: Task ID
        
    Returns:
        Task status response
    """
    try:
        if not task_id or not task_id.strip():
            safe_log(
                logger,
                logging.WARNING,
                "Empty task_id provided",
                endpoint="/api/task-status/{task_id}"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_TASK_ID",
                        "message": "task_id cannot be empty",
                        "details": None
                    }
                }
            )
        
        task_id = task_id.strip()
        
        # Check task status
        task_status = await task_queue.check_task_status(task_id)
        
        if task_status.status == "not_found":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": "error",
                    "error": {
                        "code": "TASK_NOT_FOUND",
                        "message": f"Task {task_id} not found",
                        "details": None
                    }
                }
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "data": task_status.model_dump() if hasattr(task_status, 'model_dump') else {}
            }
        )
        
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Unexpected error in get_task_status",
            task_id=task_id if 'task_id' in locals() else "unknown",
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred",
                    "details": None
                }
            }
        )

