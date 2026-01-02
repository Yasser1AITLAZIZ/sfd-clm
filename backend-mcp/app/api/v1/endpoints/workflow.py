"""Workflow status endpoints"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Any, Dict, List, Optional
import logging
from datetime import datetime

from app.core.logging import get_logger, safe_log
from app.core.config import settings
from app.services.workflow_step_storage import WorkflowStepStorage

logger = get_logger(__name__)

router = APIRouter()

# Initialize workflow step storage
_step_storage: Optional[WorkflowStepStorage] = None


def get_step_storage() -> WorkflowStepStorage:
    """Get or create workflow step storage instance"""
    global _step_storage
    if _step_storage is None:
        _step_storage = WorkflowStepStorage(settings.session_db_path)
    return _step_storage


@router.get(
    "/api/workflow/status/{workflow_id}",
    status_code=status.HTTP_200_OK,
    summary="Get workflow status",
    description="Get current workflow status, steps, and progress"
)
async def get_workflow_status(workflow_id: str) -> JSONResponse:
    """
    Get workflow status by workflow_id.
    
    Args:
        workflow_id: Workflow ID
        
    Returns:
        Workflow status response with steps and progress
    """
    try:
        if not workflow_id or not workflow_id.strip():
            safe_log(
                logger,
                logging.WARNING,
                "Empty workflow_id provided",
                endpoint="/api/workflow/status/{workflow_id}"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_WORKFLOW_ID",
                        "message": "workflow_id cannot be empty",
                        "details": None
                    }
                }
            )
        
        workflow_id = workflow_id.strip()
        step_storage = get_step_storage()
        
        # Get all workflow steps
        steps_data = step_storage.get_workflow_steps(workflow_id)
        
        if not steps_data:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": "error",
                    "error": {
                        "code": "WORKFLOW_NOT_FOUND",
                        "message": f"Workflow {workflow_id} not found",
                        "details": None
                    }
                }
            )
        
        # Determine overall status
        statuses = [step.get("status", "pending") for step in steps_data]
        if "failed" in statuses:
            overall_status = "failed"
        elif "in_progress" in statuses or any(s in ["pending", "in_progress"] for s in statuses):
            overall_status = "in_progress"
        elif all(s == "completed" for s in statuses):
            overall_status = "completed"
        else:
            overall_status = "pending"
        
        # Find current step (first in_progress or first pending)
        current_step = None
        for step in steps_data:
            if step.get("status") == "in_progress":
                current_step = step.get("step_name")
                break
        if not current_step:
            for step in steps_data:
                if step.get("status") == "pending":
                    current_step = step.get("step_name")
                    break
        
        # Calculate progress percentage
        completed_steps = sum(1 for s in statuses if s == "completed")
        total_steps = len(steps_data)
        progress_percentage = int((completed_steps / total_steps * 100)) if total_steps > 0 else 0
        
        # Get start and completion times
        started_at = steps_data[0].get("started_at") if steps_data else None
        completed_at = None
        if overall_status == "completed":
            # Find the last completed step's completion time
            for step in reversed(steps_data):
                if step.get("status") == "completed" and step.get("completed_at"):
                    completed_at = step.get("completed_at")
                    break
        
        # Format steps for response
        steps = []
        for step_data in steps_data:
            # Build comprehensive input_data object
            input_data_dict = {
                "record_id": step_data.get("input_record_id"),
                "user_message": step_data.get("input_user_message"),
                "documents_count": step_data.get("input_documents_count"),
                "fields_count": step_data.get("input_fields_count"),
            }
            # Include full input_context if available (already parsed from JSON)
            if step_data.get("input_context"):
                input_data_dict["context"] = step_data.get("input_context")
            # Include prompt if available
            if step_data.get("input_prompt"):
                input_data_dict["prompt"] = step_data.get("input_prompt")
            # Include salesforce_data if available (for validation_routing and preprocessing)
            if step_data.get("input_salesforce_data"):
                try:
                    import json
                    salesforce_data = step_data.get("input_salesforce_data")
                    if isinstance(salesforce_data, str):
                        salesforce_data = json.loads(salesforce_data)
                    input_data_dict["salesforce_data"] = salesforce_data
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # output_data is already parsed from JSON in get_workflow_steps
            output_data = step_data.get("output_data")
            
            step = {
                "step_name": step_data.get("step_name"),
                "step_order": step_data.get("step_order"),
                "status": step_data.get("status", "pending"),
                "started_at": step_data.get("started_at"),
                "completed_at": step_data.get("completed_at"),
                "processing_time": step_data.get("processing_time"),
                "error": step_data.get("output_error_message"),
                "error_details": step_data.get("error_details"),
                # Include input_data and output_data for Data Transformation Viewer
                "input_data": input_data_dict,
                "output_data": output_data,  # Already parsed from JSON
            }
            steps.append(step)
        
        response_data = {
            "workflow_id": workflow_id,
            "status": overall_status,
            "current_step": current_step,
            "steps": steps,
            "progress_percentage": progress_percentage,
            "started_at": started_at,
            "completed_at": completed_at,
        }
        
        safe_log(
            logger,
            logging.INFO,
            "Workflow status retrieved",
            workflow_id=workflow_id,
            status=overall_status,
            progress=progress_percentage
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "data": response_data
            }
        )
        
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Error getting workflow status",
            workflow_id=workflow_id if 'workflow_id' in locals() else "unknown",
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
                    "details": str(e) if e else None
                }
            }
        )


@router.get(
    "/api/workflow/{workflow_id}/steps",
    status_code=status.HTTP_200_OK,
    summary="Get workflow steps",
    description="Get detailed step information for a workflow"
)
async def get_workflow_steps(workflow_id: str) -> JSONResponse:
    """
    Get workflow steps by workflow_id.
    
    Args:
        workflow_id: Workflow ID
        
    Returns:
        List of workflow steps with detailed information
    """
    try:
        if not workflow_id or not workflow_id.strip():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_WORKFLOW_ID",
                        "message": "workflow_id cannot be empty",
                        "details": None
                    }
                }
            )
        
        workflow_id = workflow_id.strip()
        step_storage = get_step_storage()
        
        # Get all workflow steps
        steps_data = step_storage.get_workflow_steps(workflow_id)
        
        if not steps_data:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": "error",
                    "error": {
                        "code": "WORKFLOW_NOT_FOUND",
                        "message": f"Workflow {workflow_id} not found",
                        "details": None
                    }
                }
            )
        
        # Format steps for response
        steps = []
        for step_data in steps_data:
            step = {
                "step_name": step_data.get("step_name"),
                "step_order": step_data.get("step_order"),
                "status": step_data.get("status", "pending"),
                "started_at": step_data.get("started_at"),
                "completed_at": step_data.get("completed_at"),
                "processing_time": step_data.get("processing_time"),
                "error": step_data.get("output_error_message"),
                "error_details": step_data.get("error_details"),
                "input_data": {
                    "record_id": step_data.get("input_record_id"),
                    "user_message": step_data.get("input_user_message"),
                    "documents_count": step_data.get("input_documents_count"),
                    "fields_count": step_data.get("input_fields_count"),
                },
                "output_data": step_data.get("output_data"),
            }
            steps.append(step)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "data": steps
            }
        )
        
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Error getting workflow steps",
            workflow_id=workflow_id if 'workflow_id' in locals() else "unknown",
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
                    "details": str(e) if e else None
                }
            }
        )

