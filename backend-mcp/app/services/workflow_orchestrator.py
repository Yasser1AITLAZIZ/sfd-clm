"""Workflow orchestrator for coordinating execution steps"""
from typing import Dict, Any, Optional
import logging
import traceback
from datetime import datetime
import uuid
import time

from app.core.logging import get_logger, safe_log, log_progress, log_timing, log_progress, log_timing
from app.core.exceptions import (
    InvalidRequestError,
    SessionNotFoundError,
    WorkflowError
)
from app.services.session_router import validate_and_route
from app.services.preprocessing.preprocessing_pipeline import PreprocessingPipeline
from app.services.prompting.prompt_builder import PromptBuilder
from app.services.prompting.prompt_optimizer import PromptOptimizer
from app.services.mcp.mcp_message_formatter import MCPMessageFormatter
from app.services.mcp.mcp_sender import MCPSender
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
        self.preprocessing_pipeline = PreprocessingPipeline()
        self.prompt_builder = PromptBuilder()
        self.prompt_optimizer = PromptOptimizer()
        self.mcp_formatter = MCPMessageFormatter()
        self.mcp_sender = MCPSender()
        
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
        
        # Total number of steps in workflow
        TOTAL_STEPS = 7
        
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
        
        workflow_start_time = time.time()
        
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
            step_start_time = time.time()
            workflow_state["current_step"] = "validation_routing"
            log_progress(
                logger,
                logging.INFO,
                "Starting Validation & Routing",
                step_number=1,
                total_steps=TOTAL_STEPS,
                step_name="validation_routing",
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
                
                step_elapsed = time.time() - step_start_time
                log_timing(
                    logger,
                    logging.INFO,
                    "Step 1 completed: Validation & Routing",
                    elapsed_time=step_elapsed,
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
                    error_message=error_msg,
                    traceback=traceback.format_exc()
                )
                return self._build_workflow_response(workflow_state)
            
            # Determine next steps based on routing result
            routing_status = routing_result.get("status", "unknown")
            
            if routing_status == "initialization":
                # New session: need preprocessing
                # Step 2: Preprocessing
                step_start_time = time.time()
                workflow_state["current_step"] = "preprocessing"
                log_progress(
                    logger,
                    logging.INFO,
                    "Starting Preprocessing",
                    step_number=2,
                    total_steps=TOTAL_STEPS,
                    step_name="preprocessing",
                    workflow_id=workflow_id,
                    record_id=record_id
                )
                
                try:
                    salesforce_data = routing_result.get("salesforce_data")
                    if salesforce_data:
                        preprocessed_data = await self.preprocessing_pipeline.execute_preprocessing(salesforce_data)
                        workflow_state["data"]["preprocessing"] = {
                            "status": "completed",
                            "preprocessed_data": preprocessed_data.model_dump() if hasattr(preprocessed_data, 'model_dump') else {}
                        }
                        workflow_state["steps_completed"].append("preprocessing")
                        step_elapsed = time.time() - step_start_time
                        log_timing(
                            logger,
                            logging.INFO,
                            "Step 2 completed: Preprocessing",
                            elapsed_time=step_elapsed,
                            workflow_id=workflow_id
                        )
                    else:
                        raise WorkflowError("No salesforce_data available for preprocessing")
                        
                except Exception as e:
                    error_msg = str(e) if e else "Unknown error"
                    workflow_state["errors"].append({
                        "step": "preprocessing",
                        "error": error_msg,
                        "error_type": type(e).__name__
                    })
                    safe_log(
                        logger,
                        logging.ERROR,
                        "Step 2 failed: Preprocessing",
                        workflow_id=workflow_id,
                        error_type=type(e).__name__,
                        error_message=error_msg,
                        traceback=traceback.format_exc()
                    )
                    # Continue workflow even if preprocessing fails
                    workflow_state["data"]["preprocessing"] = {
                        "status": "failed",
                        "error": error_msg
                    }
                    workflow_state["steps_completed"].append("preprocessing")
                
            elif routing_status == "continuation":
                # Existing session: skip preprocessing
                workflow_state["current_step"] = "preprocessing"
                log_progress(
                    logger,
                    logging.INFO,
                    "Step 2: Preprocessing (skipped - continuation flow)",
                    step_number=2,
                    total_steps=TOTAL_STEPS,
                    step_name="preprocessing",
                    workflow_id=workflow_id,
                    session_id=session_id
                )
                workflow_state["data"]["preprocessing"] = {
                    "status": "skipped",
                    "reason": "continuation_flow"
                }
                workflow_state["steps_completed"].append("preprocessing")
            
            # Step 3: Prompt Building
            step_start_time = time.time()
            workflow_state["current_step"] = "prompt_building"
            log_progress(
                logger,
                logging.INFO,
                "Starting Prompt Building",
                step_number=3,
                total_steps=TOTAL_STEPS,
                step_name="prompt_building",
                workflow_id=workflow_id
            )
            
            try:
                # Get preprocessed data or routing result
                preprocessed_data = workflow_state["data"].get("preprocessing", {}).get("preprocessed_data")
                if not preprocessed_data and routing_status == "continuation":
                    # For continuation, use session context
                    preprocessed_data = {}
                
                user_message = request_data.get("user_message", "")
                prompt_result = await self.prompt_builder.build_prompt(
                    user_message=user_message,
                    preprocessed_data=preprocessed_data,
                    routing_status=routing_status
                )
                
                workflow_state["data"]["prompt_building"] = {
                    "status": "completed",
                    "prompt": prompt_result.get("prompt", ""),
                    "scenario_type": prompt_result.get("scenario_type", "extraction")
                }
                workflow_state["steps_completed"].append("prompt_building")
                step_elapsed = time.time() - step_start_time
                log_timing(
                    logger,
                    logging.INFO,
                    "Step 3 completed: Prompt Building",
                    elapsed_time=step_elapsed,
                    workflow_id=workflow_id
                )
                
            except Exception as e:
                error_msg = str(e) if e else "Unknown error"
                workflow_state["errors"].append({
                    "step": "prompt_building",
                    "error": error_msg,
                    "error_type": type(e).__name__
                })
                safe_log(
                    logger,
                    logging.ERROR,
                    "Step 3 failed: Prompt Building",
                    workflow_id=workflow_id,
                    error_type=type(e).__name__,
                    error_message=error_msg,
                    traceback=traceback.format_exc()
                )
                # Use fallback prompt
                workflow_state["data"]["prompt_building"] = {
                    "status": "completed",
                    "prompt": request_data.get("user_message", "Extract data from documents"),
                    "scenario_type": "extraction"
                }
                workflow_state["steps_completed"].append("prompt_building")
            
            # Step 4: Prompt Optimization
            step_start_time = time.time()
            workflow_state["current_step"] = "prompt_optimization"
            log_progress(
                logger,
                logging.INFO,
                "Starting Prompt Optimization",
                step_number=4,
                total_steps=TOTAL_STEPS,
                step_name="prompt_optimization",
                workflow_id=workflow_id
            )
            
            try:
                prompt = workflow_state["data"]["prompt_building"].get("prompt", "")
                optimized_prompt = await self.prompt_optimizer.optimize_prompt(prompt)
                
                workflow_state["data"]["prompt_optimization"] = {
                    "status": "completed",
                    "optimized_prompt": optimized_prompt.get("prompt", prompt),
                    "optimizations_applied": optimized_prompt.get("optimizations_applied", [])
                }
                workflow_state["steps_completed"].append("prompt_optimization")
                step_elapsed = time.time() - step_start_time
                log_timing(
                    logger,
                    logging.INFO,
                    "Step 4 completed: Prompt Optimization",
                    elapsed_time=step_elapsed,
                    workflow_id=workflow_id
                )
                
            except Exception as e:
                error_msg = str(e) if e else "Unknown error"
                safe_log(
                    logger,
                    logging.ERROR,
                    "Step 4 failed: Prompt Optimization",
                    workflow_id=workflow_id,
                    error_type=type(e).__name__,
                    error_message=error_msg,
                    traceback=traceback.format_exc()
                )
                # Use original prompt if optimization fails
                prompt = workflow_state["data"]["prompt_building"].get("prompt", "")
                workflow_state["data"]["prompt_optimization"] = {
                    "status": "completed",
                    "optimized_prompt": prompt,
                    "optimizations_applied": []
                }
                workflow_state["steps_completed"].append("prompt_optimization")
            
            # Step 5: MCP Formatting
            step_start_time = time.time()
            workflow_state["current_step"] = "mcp_formatting"
            log_progress(
                logger,
                logging.INFO,
                "Starting MCP Formatting",
                step_number=5,
                total_steps=TOTAL_STEPS,
                step_name="mcp_formatting",
                workflow_id=workflow_id
            )
            
            try:
                optimized_prompt = workflow_state["data"]["prompt_optimization"].get("optimized_prompt", "")
                preprocessed_data = workflow_state["data"].get("preprocessing", {}).get("preprocessed_data", {})
                
                # Prepare context for MCP
                context = {
                    "documents": preprocessed_data.get("processed_documents", []),
                    "fields": preprocessed_data.get("fields_dictionary", {}).get("fields", []),
                    "session_id": session_id if session_id != "none" else None
                }
                
                metadata = {
                    "record_id": record_id,
                    "record_type": routing_result.get("salesforce_data", {}).get("record_type", "Claim") if routing_result.get("salesforce_data") else "Claim",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                mcp_message = self.mcp_formatter.format_message(
                    prompt=optimized_prompt,
                    context=context,
                    metadata=metadata
                )
                
                # Store formatted message for use in next step
                workflow_state["data"]["mcp_formatting"] = {
                    "status": "completed",
                    "message_id": mcp_message.message_id if hasattr(mcp_message, 'message_id') else "unknown"
                }
                # Store the formatted message object in workflow state for reuse
                workflow_state["_mcp_message"] = mcp_message
                workflow_state["steps_completed"].append("mcp_formatting")
                step_elapsed = time.time() - step_start_time
                log_timing(
                    logger,
                    logging.INFO,
                    "Step 5 completed: MCP Formatting",
                    elapsed_time=step_elapsed,
                    workflow_id=workflow_id
                )
                
            except Exception as e:
                error_msg = str(e) if e else "Unknown error"
                workflow_state["errors"].append({
                    "step": "mcp_formatting",
                    "error": error_msg,
                    "error_type": type(e).__name__
                })
                workflow_state["status"] = "failed"
                safe_log(
                    logger,
                    logging.ERROR,
                    "Step 5 failed: MCP Formatting",
                    workflow_id=workflow_id,
                    error_type=type(e).__name__,
                    error_message=error_msg,
                    traceback=traceback.format_exc()
                )
                return self._build_workflow_response(workflow_state)
            
            # Step 6: MCP Sending
            step_start_time = time.time()
            workflow_state["current_step"] = "mcp_sending"
            log_progress(
                logger,
                logging.INFO,
                "Starting MCP Sending",
                step_number=6,
                total_steps=TOTAL_STEPS,
                step_name="mcp_sending",
                workflow_id=workflow_id
            )
            
            try:
                # Reuse the formatted message from step 5
                mcp_message = workflow_state.get("_mcp_message")
                if not mcp_message:
                    # Fallback: format message if not stored (should not happen)
                    safe_log(
                        logger,
                        logging.WARNING,
                        "MCP message not found in workflow state, formatting again",
                        workflow_id=workflow_id
                    )
                    optimized_prompt = workflow_state["data"]["prompt_optimization"].get("optimized_prompt", "")
                    preprocessed_data = workflow_state["data"].get("preprocessing", {}).get("preprocessed_data", {})
                    context = {
                        "documents": preprocessed_data.get("processed_documents", []),
                        "fields": preprocessed_data.get("fields_dictionary", {}).get("fields", []),
                        "session_id": session_id if session_id != "none" else None
                    }
                    metadata = {
                        "record_id": record_id,
                        "record_type": routing_result.get("salesforce_data", {}).get("record_type", "Claim") if routing_result.get("salesforce_data") else "Claim",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    mcp_message = self.mcp_formatter.format_message(
                        prompt=optimized_prompt,
                        context=context,
                        metadata=metadata
                    )
                
                mcp_response = await self.mcp_sender.send_to_langgraph(mcp_message, async_mode=False)
                # #region agent log
                import json as json_lib
                import time
                try:
                    with open(r'c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json_lib.dumps({"id":f"log_{int(time.time()*1000)}_mcp_response_received","timestamp":int(time.time()*1000),"location":"workflow_orchestrator.py:487","message":"MCP response received in workflow","data":{"has_extracted_data":hasattr(mcp_response,'extracted_data'),"extracted_data_count":len(mcp_response.extracted_data) if hasattr(mcp_response,'extracted_data') else 0,"extracted_data_keys":list(mcp_response.extracted_data.keys()) if hasattr(mcp_response,'extracted_data') and mcp_response.extracted_data else [],"status":mcp_response.status if hasattr(mcp_response,'status') else "unknown"},"sessionId":"debug-session","runId":"run1","hypothesisId":"D"}) + "\n")
                except: pass
                # #endregion
                
                workflow_state["data"]["mcp_sending"] = {
                    "status": "completed",
                    "mcp_response": {
                        "extracted_data": mcp_response.extracted_data if hasattr(mcp_response, 'extracted_data') else {},
                        "confidence_scores": mcp_response.confidence_scores if hasattr(mcp_response, 'confidence_scores') else {},
                        "status": mcp_response.status if hasattr(mcp_response, 'status') else "unknown"
                    }
                }
                # #region agent log
                try:
                    with open(r'c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json_lib.dumps({"id":f"log_{int(time.time()*1000)}_workflow_state_updated","timestamp":int(time.time()*1000),"location":"workflow_orchestrator.py:496","message":"Workflow state updated with mcp_response","data":{"mcp_response_extracted_data_count":len(workflow_state["data"]["mcp_sending"]["mcp_response"].get("extracted_data",{}))},"sessionId":"debug-session","runId":"run1","hypothesisId":"D"}) + "\n")
                except: pass
                # #endregion
                workflow_state["steps_completed"].append("mcp_sending")
                step_elapsed = time.time() - step_start_time
                log_timing(
                    logger,
                    logging.INFO,
                    "Step 6 completed: MCP Sending",
                    elapsed_time=step_elapsed,
                    workflow_id=workflow_id,
                    extracted_fields=len(mcp_response.extracted_data if hasattr(mcp_response, 'extracted_data') else {})
                )
                
            except Exception as e:
                error_msg = str(e) if e else "Unknown error"
                workflow_state["errors"].append({
                    "step": "mcp_sending",
                    "error": error_msg,
                    "error_type": type(e).__name__
                })
                workflow_state["status"] = "failed"
                safe_log(
                    logger,
                    logging.ERROR,
                    "Step 6 failed: MCP Sending",
                    workflow_id=workflow_id,
                    error_type=type(e).__name__,
                    error_message=error_msg,
                    traceback=traceback.format_exc()
                )
                return self._build_workflow_response(workflow_state)
            
            # Step 7: Response Handling
            step_start_time = time.time()
            workflow_state["current_step"] = "response_handling"
            log_progress(
                logger,
                logging.INFO,
                "Starting Response Handling",
                step_number=7,
                total_steps=TOTAL_STEPS,
                step_name="response_handling",
                workflow_id=workflow_id
            )
            
            try:
                mcp_response_data = workflow_state["data"]["mcp_sending"].get("mcp_response", {})
                
                workflow_state["data"]["response_handling"] = {
                    "status": "completed",
                    "extracted_data": mcp_response_data.get("extracted_data", {}),
                    "confidence_scores": mcp_response_data.get("confidence_scores", {}),
                    "final_status": mcp_response_data.get("status", "success")
                }
                workflow_state["steps_completed"].append("response_handling")
                step_elapsed = time.time() - step_start_time
                log_timing(
                    logger,
                    logging.INFO,
                    "Step 7 completed: Response Handling",
                    elapsed_time=step_elapsed,
                    workflow_id=workflow_id,
                    extracted_fields=len(mcp_response_data.get("extracted_data", {}))
                )
                
            except Exception as e:
                error_msg = str(e) if e else "Unknown error"
                workflow_state["errors"].append({
                    "step": "response_handling",
                    "error": error_msg,
                    "error_type": type(e).__name__
                })
                safe_log(
                    logger,
                    logging.ERROR,
                    "Step 7 failed: Response Handling",
                    workflow_id=workflow_id,
                    error_type=type(e).__name__,
                    error_message=error_msg,
                    traceback=traceback.format_exc()
                )
                # Don't fail workflow, just log error
                workflow_state["data"]["response_handling"] = {
                    "status": "completed",
                    "extracted_data": {},
                    "confidence_scores": {},
                    "final_status": "error"
                }
                workflow_state["steps_completed"].append("response_handling")
                step_elapsed = time.time() - step_start_time
                log_timing(
                    logger,
                    logging.WARNING,
                    "Step 7 completed with errors: Response Handling",
                    elapsed_time=step_elapsed,
                    workflow_id=workflow_id
                )
            
            # Workflow completed
            workflow_state["status"] = "completed"
            workflow_state["current_step"] = None
            workflow_state["completed_at"] = datetime.utcnow().isoformat()
            
            total_elapsed = time.time() - workflow_start_time
            log_timing(
                logger,
                logging.INFO,
                "Workflow execution completed successfully",
                elapsed_time=total_elapsed,
                workflow_id=workflow_id,
                record_id=record_id,
                session_id=session_id,
                steps_completed=len(workflow_state["steps_completed"]),
                total_steps=TOTAL_STEPS
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
                error_message=error_msg,
                traceback=traceback.format_exc()
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

