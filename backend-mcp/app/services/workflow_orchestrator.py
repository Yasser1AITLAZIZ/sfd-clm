"""Workflow orchestrator for coordinating execution steps"""
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import uuid

from app.core.logging import get_logger, safe_log
from app.core.exceptions import (
    InvalidRequestError,
    SessionNotFoundError,
    WorkflowError
)
from app.services.session_router import validate_and_route
from app.models.schemas import (
    WorkflowRequestSchema,
    WorkflowResponseSchema,
    WorkflowStepSchema
)

logger = get_logger(__name__)


class WorkflowOrchestrator:
    """Orchestrator for coordinating workflow execution"""
    
    def __init__(self):
        """Initialize workflow orchestrator"""
        safe_log(
            logger,
            logging.INFO,
            "WorkflowOrchestrator initialized"
        )
    
    async def execute_workflow(
        self,
        request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the complete workflow.
        
        Steps:
        1. Validation & Routing
        2. Preprocessing (if new session)
        3. Prompt Building
        4. Prompt Optimization
        5. MCP Formatting
        6. MCP Sending
        7. Response Handling
        
        Args:
            request_data: Request data with record_id, session_id, user_message
            
        Returns:
            Workflow response with status and data
        """
        workflow_id = str(uuid.uuid4())
        record_id = request_data.get("record_id") or "unknown"
        session_id = request_data.get("session_id") or "none"
        
        workflow_state = {
            "workflow_id": workflow_id,
            "status": "pending",
            "current_step": None,
            "steps_completed": [],
            "data": {},
            "errors": [],
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None
        }
        
        try:
            safe_log(
                logger,
                logging.INFO,
                "Workflow execution started",
                workflow_id=workflow_id,
                record_id=record_id,
                session_id=session_id
            )
            
            # Step 1: Validation & Routing
            workflow_state["current_step"] = "validation_routing"
            safe_log(
                logger,
                logging.INFO,
                "Step 1: Validation & Routing",
                workflow_id=workflow_id,
                record_id=record_id,
                session_id=session_id
            )
            
            try:
                routing_result = await validate_and_route(
                    record_id=request_data.get("record_id"),
                    session_id=request_data.get("session_id"),
                    user_message=request_data.get("user_message")
                )
                
                if not routing_result:
                    raise WorkflowError("Routing returned empty result")
                
                workflow_state["data"]["routing"] = routing_result
                workflow_state["steps_completed"].append("validation_routing")
                
                safe_log(
                    logger,
                    logging.INFO,
                    "Step 1 completed: Validation & Routing",
                    workflow_id=workflow_id,
                    routing_status=routing_result.get("status", "unknown")
                )
                
            except (InvalidRequestError, SessionNotFoundError) as e:
                error_msg = str(e) if e else "Unknown error"
                workflow_state["errors"].append({
                    "step": "validation_routing",
                    "error": error_msg,
                    "error_type": type(e).__name__
                })
                workflow_state["status"] = "failed"
                safe_log(
                    logger,
                    logging.ERROR,
                    "Step 1 failed: Validation & Routing",
                    workflow_id=workflow_id,
                    error_type=type(e).__name__,
                    error_message=error_msg
                )
                return self._build_workflow_response(workflow_state)
            
            except Exception as e:
                error_msg = str(e) if e else "Unknown error"
                workflow_state["errors"].append({
                    "step": "validation_routing",
                    "error": error_msg,
                    "error_type": type(e).__name__
                })
                workflow_state["status"] = "failed"
                safe_log(
                    logger,
                    logging.ERROR,
                    "Unexpected error in Step 1",
                    workflow_id=workflow_id,
                    error_type=type(e).__name__,
                    error_message=error_msg
                )
                return self._build_workflow_response(workflow_state)
            
            # Determine next steps based on routing result
            routing_status = routing_result.get("status", "unknown")
            
            if routing_status == "initialization":
                # New session: need preprocessing
                # Step 2: Preprocessing (will be implemented in step 5)
                workflow_state["current_step"] = "preprocessing"
                safe_log(
                    logger,
                    logging.INFO,
                    "Step 2: Preprocessing (skipped - to be implemented)",
                    workflow_id=workflow_id,
                    record_id=record_id
                )
                # TODO: Implement preprocessing when step 5 is done
                workflow_state["data"]["preprocessing"] = {
                    "status": "skipped",
                    "message": "Preprocessing to be implemented in step 5"
                }
                workflow_state["steps_completed"].append("preprocessing")
                
            elif routing_status == "continuation":
                # Existing session: skip preprocessing
                workflow_state["current_step"] = "preprocessing"
                safe_log(
                    logger,
                    logging.INFO,
                    "Step 2: Preprocessing (skipped - continuation flow)",
                    workflow_id=workflow_id,
                    session_id=session_id
                )
                workflow_state["data"]["preprocessing"] = {
                    "status": "skipped",
                    "reason": "continuation_flow"
                }
                workflow_state["steps_completed"].append("preprocessing")
            
            # Step 3: Prompt Building (will be implemented in step 6)
            workflow_state["current_step"] = "prompt_building"
            safe_log(
                logger,
                logging.INFO,
                "Step 3: Prompt Building (skipped - to be implemented)",
                workflow_id=workflow_id
            )
            # TODO: Implement prompt building when step 6 is done
            workflow_state["data"]["prompt_building"] = {
                "status": "skipped",
                "message": "Prompt building to be implemented in step 6"
            }
            workflow_state["steps_completed"].append("prompt_building")
            
            # Step 4: Prompt Optimization (will be implemented in step 6)
            workflow_state["current_step"] = "prompt_optimization"
            safe_log(
                logger,
                logging.INFO,
                "Step 4: Prompt Optimization (skipped - to be implemented)",
                workflow_id=workflow_id
            )
            # TODO: Implement prompt optimization when step 6 is done
            workflow_state["data"]["prompt_optimization"] = {
                "status": "skipped",
                "message": "Prompt optimization to be implemented in step 6"
            }
            workflow_state["steps_completed"].append("prompt_optimization")
            
            # Step 5: MCP Formatting (will be implemented in step 7)
            workflow_state["current_step"] = "mcp_formatting"
            safe_log(
                logger,
                logging.INFO,
                "Step 5: MCP Formatting (skipped - to be implemented)",
                workflow_id=workflow_id
            )
            # TODO: Implement MCP formatting when step 7 is done
            workflow_state["data"]["mcp_formatting"] = {
                "status": "skipped",
                "message": "MCP formatting to be implemented in step 7"
            }
            workflow_state["steps_completed"].append("mcp_formatting")
            
            # Step 6: MCP Sending (will be implemented in step 7)
            workflow_state["current_step"] = "mcp_sending"
            safe_log(
                logger,
                logging.INFO,
                "Step 6: MCP Sending (skipped - to be implemented)",
                workflow_id=workflow_id
            )
            # TODO: Implement MCP sending when step 7 is done
            workflow_state["data"]["mcp_sending"] = {
                "status": "skipped",
                "message": "MCP sending to be implemented in step 7"
            }
            workflow_state["steps_completed"].append("mcp_sending")
            
            # Step 7: Response Handling (will be implemented in step 7)
            workflow_state["current_step"] = "response_handling"
            safe_log(
                logger,
                logging.INFO,
                "Step 7: Response Handling (skipped - to be implemented)",
                workflow_id=workflow_id
            )
            # TODO: Implement response handling when step 7 is done
            workflow_state["data"]["response_handling"] = {
                "status": "skipped",
                "message": "Response handling to be implemented in step 7"
            }
            workflow_state["steps_completed"].append("response_handling")
            
            # Workflow completed (with placeholders)
            workflow_state["status"] = "completed"
            workflow_state["current_step"] = None
            workflow_state["completed_at"] = datetime.utcnow().isoformat()
            
            safe_log(
                logger,
                logging.INFO,
                "Workflow execution completed",
                workflow_id=workflow_id,
                record_id=record_id,
                session_id=session_id,
                steps_completed=len(workflow_state["steps_completed"])
            )
            
            return self._build_workflow_response(workflow_state)
            
        except Exception as e:
            error_msg = str(e) if e else "Unknown error"
            workflow_state["status"] = "failed"
            workflow_state["errors"].append({
                "step": workflow_state.get("current_step", "unknown"),
                "error": error_msg,
                "error_type": type(e).__name__
            })
            workflow_state["completed_at"] = datetime.utcnow().isoformat()
            
            safe_log(
                logger,
                logging.ERROR,
                "Workflow execution failed",
                workflow_id=workflow_id,
                record_id=record_id,
                session_id=session_id,
                error_type=type(e).__name__,
                error_message=error_msg
            )
            
            return self._build_workflow_response(workflow_state)
    
    def _build_workflow_response(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Build workflow response from state"""
        return {
            "status": workflow_state.get("status", "unknown"),
            "workflow_id": workflow_state.get("workflow_id"),
            "current_step": workflow_state.get("current_step"),
            "steps_completed": workflow_state.get("steps_completed", []),
            "data": workflow_state.get("data", {}),
            "errors": workflow_state.get("errors", []),
            "started_at": workflow_state.get("started_at"),
            "completed_at": workflow_state.get("completed_at")
        }

