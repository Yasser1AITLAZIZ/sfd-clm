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
from app.services.session_router import validate_and_route, get_session_manager
from app.services.preprocessing.preprocessing_pipeline import PreprocessingPipeline
from app.services.prompting.prompt_builder import PromptBuilder
from app.services.prompting.prompt_optimizer import PromptOptimizer
from app.services.mcp.mcp_message_formatter import MCPMessageFormatter
from app.services.mcp.mcp_sender import MCPSender
from app.services.workflow_step_storage import WorkflowStepStorage
from app.core.config import settings
import uuid
from app.models.schemas import (
    WorkflowRequestSchema,
    WorkflowResponseSchema,
    WorkflowStepSchema
)

logger = get_logger(__name__)


def extract_fields_from_preprocessed_data(preprocessed_data: Any) -> list:
    """
    Extract fields from preprocessed_data (handles both Pydantic and dict).
    Converts Pydantic field objects to dicts for serialization.
    
    Args:
        preprocessed_data: PreprocessedDataSchema object or dict
        
    Returns:
        List of fields (as dicts)
    """
    if not preprocessed_data:
        return []
    
    # If it's a Pydantic model, convert to dict
    if hasattr(preprocessed_data, 'model_dump'):
        data = preprocessed_data.model_dump()
    elif isinstance(preprocessed_data, dict):
        data = preprocessed_data
    else:
        # Try to access as attribute
        if hasattr(preprocessed_data, 'fields_dictionary'):
            fields_dict = preprocessed_data.fields_dictionary
            if hasattr(fields_dict, 'fields'):
                fields = fields_dict.fields
                # Convert Pydantic objects to dicts
                return [field.model_dump() if hasattr(field, 'model_dump') else (field.__dict__ if hasattr(field, '__dict__') else field) for field in fields]
            elif hasattr(fields_dict, 'model_dump'):
                fields_dict_data = fields_dict.model_dump()
                return fields_dict_data.get("fields", [])
        return []
    
    # Extract from dict
    fields_dict = data.get("fields_dictionary", {})
    if isinstance(fields_dict, dict):
        fields = fields_dict.get("fields", [])
        # Convert Pydantic objects to dicts if needed
        return [field.model_dump() if hasattr(field, 'model_dump') else (field.__dict__ if hasattr(field, '__dict__') and not isinstance(field, dict) else field) for field in fields]
    elif hasattr(fields_dict, 'fields'):
        fields = fields_dict.fields
        # Convert Pydantic objects to dicts
        return [field.model_dump() if hasattr(field, 'model_dump') else (field.__dict__ if hasattr(field, '__dict__') else field) for field in fields]
    elif hasattr(fields_dict, 'model_dump'):
        fields_dict_data = fields_dict.model_dump()
        return fields_dict_data.get("fields", [])
    return []


def extract_documents_from_preprocessed_data(preprocessed_data: Any) -> list:
    """
    Extract documents from preprocessed_data (handles both Pydantic and dict).
    
    Args:
        preprocessed_data: PreprocessedDataSchema object or dict
        
    Returns:
        List of documents
    """
    if not preprocessed_data:
        return []
    
    # If it's a Pydantic model, convert to dict
    if hasattr(preprocessed_data, 'model_dump'):
        data = preprocessed_data.model_dump()
    elif isinstance(preprocessed_data, dict):
        data = preprocessed_data
    else:
        # Try to access as attribute
        if hasattr(preprocessed_data, 'processed_documents'):
            return preprocessed_data.processed_documents
        return []
    
    # Extract from dict
    return data.get("processed_documents", [])


class WorkflowOrchestrator:
    """Orchestrator for coordinating workflow execution"""
    
    def __init__(self):
        """Initialize workflow orchestrator"""
        self.preprocessing_pipeline = PreprocessingPipeline()
        self.prompt_builder = PromptBuilder()
        self.prompt_optimizer = PromptOptimizer()
        self.mcp_formatter = MCPMessageFormatter()
        self.mcp_sender = MCPSender()
        
        # Initialize workflow step storage
        try:
            self.step_storage = WorkflowStepStorage(settings.session_db_path)
        except Exception as e:
            safe_log(
                logger,
                logging.WARNING,
                "Failed to initialize WorkflowStepStorage, workflow steps will not be tracked",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            self.step_storage = None
        
        # Verify methods exist at runtime
        if not hasattr(self.prompt_builder, 'build_prompt'):
            safe_log(
                logger,
                logging.ERROR,
                "PromptBuilder.build_prompt method not found! Available methods: " + str([m for m in dir(self.prompt_builder) if not m.startswith('_')])
            )
        if not hasattr(self.prompt_optimizer, 'optimize_prompt'):
            safe_log(
                logger,
                logging.ERROR,
                "PromptOptimizer.optimize_prompt method not found! Available methods: " + str([m for m in dir(self.prompt_optimizer) if not m.startswith('_')])
            )
        
        safe_log(
            logger,
            logging.INFO,
            "WorkflowOrchestrator initialized"
        )
    
    def _create_step_record(
        self,
        session_id: str,
        workflow_id: str,
        step_name: str,
        step_order: int,
        input_data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Helper method to create a workflow step record"""
        # Log detailed information about why step might not be created
        if not self.step_storage:
            safe_log(
                logger,
                logging.WARNING,
                f"Workflow step NOT created for {step_name}: step_storage is None",
                session_id=session_id,
                workflow_id=workflow_id,
                step_name=step_name,
                step_order=step_order
            )
            return None
        
        if session_id == "none":
            safe_log(
                logger,
                logging.WARNING,
                f"Workflow step NOT created for {step_name}: session_id is 'none'",
                session_id=session_id,
                workflow_id=workflow_id,
                step_name=step_name,
                step_order=step_order
            )
            return None
        
        try:
            safe_log(
                logger,
                logging.DEBUG,
                f"Creating workflow step for {step_name}",
                session_id=session_id,
                workflow_id=workflow_id,
                step_name=step_name,
                step_order=step_order,
                has_input_data=bool(input_data)
            )
            
            step_id = self.step_storage.create_workflow_step(
                session_id=session_id,
                workflow_id=workflow_id,
                step_name=step_name,
                step_order=step_order,
                input_data=input_data
            )
            
            safe_log(
                logger,
                logging.INFO,
                f"Workflow step created successfully for {step_name}",
                step_id=step_id,
                session_id=session_id,
                workflow_id=workflow_id,
                step_name=step_name
            )
            
            return step_id
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                f"Failed to create workflow step for {step_name}",
                session_id=session_id,
                workflow_id=workflow_id,
                step_name=step_name,
                step_order=step_order,
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown",
                traceback=traceback.format_exc()
            )
            return None
    
    def _update_step_record(
        self,
        step_id: Optional[str],
        status: str,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        processing_time: Optional[float] = None
    ):
        """Helper method to update a workflow step record"""
        if not self.step_storage or not step_id:
            return
        try:
            self.step_storage.update_workflow_step(
                step_id=step_id,
                status=status,
                output_data=output_data,
                error_message=error_message,
                error_details=error_details,
                processing_time=processing_time
            )
        except Exception as e:
            safe_log(
                logger,
                logging.WARNING,
                f"Failed to update workflow step {step_id}",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
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
            step_id_1 = None
            
            # Create workflow step record
            step_id_1 = self._create_step_record(
                session_id=session_id,
                workflow_id=workflow_id,
                step_name="validation_routing",
                step_order=1,
                input_data={
                    "record_id": record_id,
                    "user_message": request_data.get("user_message", ""),
                    "session_id": session_id
                }
            )
            if step_id_1:
                self._update_step_record(step_id_1, "in_progress")
            
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
                
                # Update workflow step record
                self._update_step_record(
                    step_id_1,
                    "completed",
                    output_data={"status": routing_result.get("status", "unknown")},
                    processing_time=step_elapsed
                )
                
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
                
                # Update workflow step record with error
                if self.step_storage and step_id_1:
                    try:
                        step_elapsed = time.time() - step_start_time
                        self.step_storage.update_workflow_step(
                            step_id_1,
                            "failed",
                            error_message=error_msg,
                            error_details={"error_type": type(e).__name__},
                            processing_time=step_elapsed
                        )
                    except Exception:
                        pass
                
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
                
                # Update workflow step record with error
                step_elapsed = time.time() - step_start_time
                self._update_step_record(
                    step_id_1,
                    "failed",
                    error_message=error_msg,
                    error_details={"error_type": type(e).__name__},
                    processing_time=step_elapsed
                )
                
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
                # Extract session_id from routing result for new sessions
                if routing_result.get("session_id"):
                    session_id = routing_result["session_id"]
                    safe_log(
                        logger,
                        logging.INFO,
                        "Session ID updated from routing",
                        session_id=session_id,
                        workflow_id=workflow_id
                    )
                # New session: need preprocessing
                # Step 2: Preprocessing
                step_start_time = time.time()
                workflow_state["current_step"] = "preprocessing"
                step_id_2 = self._create_step_record(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    step_name="preprocessing",
                    step_order=2,
                    input_data={
                        "record_id": record_id,
                        "salesforce_data": routing_result.get("salesforce_data", {})
                    }
                )
                if step_id_2:
                    self._update_step_record(step_id_2, "in_progress")
                
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
                        self._update_step_record(
                            step_id_2,
                            "completed",
                            output_data={"status": "completed"},
                            processing_time=step_elapsed
                        )
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
                    step_elapsed = time.time() - step_start_time
                    self._update_step_record(
                        step_id_2,
                        "failed",
                        error_message=error_msg,
                        error_details={"error_type": type(e).__name__},
                        processing_time=step_elapsed
                    )
                
            elif routing_status == "continuation":
                # Existing session: skip preprocessing
                workflow_state["current_step"] = "preprocessing"
                step_id_2 = self._create_step_record(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    step_name="preprocessing",
                    step_order=2,
                    input_data={"record_id": record_id}
                )
                if step_id_2:
                    self._update_step_record(step_id_2, "completed", output_data={"status": "skipped", "reason": "continuation_flow"})
                
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
            step_id_3 = self._create_step_record(
                session_id=session_id,
                workflow_id=workflow_id,
                step_name="prompt_building",
                step_order=3,
                input_data={
                    "record_id": record_id,
                    "user_message": request_data.get("user_message", ""),
                    "preprocessed_data": workflow_state["data"].get("preprocessing", {}).get("preprocessed_data", {})
                }
            )
            if step_id_3:
                self._update_step_record(step_id_3, "in_progress")
            
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
                # Try to call build_prompt, with fallback if method doesn't exist
                # Use getattr with default to safely check and call the method
                build_prompt_method = getattr(self.prompt_builder, 'build_prompt', None)
                if build_prompt_method and callable(build_prompt_method):
                    prompt_result = await build_prompt_method(
                        user_message=user_message,
                        preprocessed_data=preprocessed_data,
                        routing_status=routing_status
                    )
                else:
                    # Fallback: use build_initialization_prompt if build_prompt doesn't exist
                    safe_log(
                        logger,
                        logging.WARNING,
                        "build_prompt method not found, using fallback",
                        workflow_id=workflow_id,
                        available_methods=str([m for m in dir(self.prompt_builder) if not m.startswith('_')])
                    )
                    # Try to create a minimal PreprocessedDataSchema for fallback
                    from app.models.schemas import PreprocessedDataSchema, ContextSummarySchema
                    if isinstance(preprocessed_data, dict):
                        fallback_preprocessed = PreprocessedDataSchema(
                            record_id=preprocessed_data.get("record_id", "unknown"),
                            record_type=preprocessed_data.get("record_type", "Claim"),
                            processed_documents=preprocessed_data.get("processed_documents", []),
                            fields_dictionary=preprocessed_data.get("fields_dictionary", {}),
                            context_summary=ContextSummarySchema(
                                record_type=preprocessed_data.get("record_type", "Claim"),
                                objective="",
                                documents_available=[],
                                fields_to_extract=[],
                                business_rules=[]
                            ),
                            validation_results={"passed": False, "errors": []},
                            metrics={}
                        )
                    else:
                        fallback_preprocessed = preprocessed_data if preprocessed_data else PreprocessedDataSchema(
                            record_id="unknown",
                            record_type="Claim",
                            processed_documents=[],
                            fields_dictionary={},
                            context_summary=ContextSummarySchema(
                                record_type="Claim",
                                objective="",
                                documents_available=[],
                                fields_to_extract=[],
                                business_rules=[]
                            ),
                            validation_results={"passed": False, "errors": []},
                            metrics={}
                        )
                    prompt_response = await self.prompt_builder.build_initialization_prompt(
                        fallback_preprocessed,
                        user_message
                    )
                    prompt_result = {
                        "prompt": prompt_response.prompt if prompt_response.prompt else user_message,
                        "scenario_type": prompt_response.scenario_type if prompt_response.scenario_type else "extraction"
                    }
                
                workflow_state["data"]["prompt_building"] = {
                    "status": "completed",
                    "prompt": prompt_result.get("prompt", ""),
                    "scenario_type": prompt_result.get("scenario_type", "extraction")
                }
                workflow_state["steps_completed"].append("prompt_building")
                step_elapsed = time.time() - step_start_time
                self._update_step_record(
                    step_id_3,
                    "completed",
                    output_data={
                        "status": "completed",
                        "prompt": prompt_result.get("prompt", "")[:500] if prompt_result.get("prompt") else None
                    },
                    processing_time=step_elapsed
                )
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
                step_elapsed = time.time() - step_start_time
                self._update_step_record(
                    step_id_3,
                    "completed",
                    output_data={"status": "completed", "prompt": request_data.get("user_message", "")[:500]},
                    processing_time=step_elapsed
                )
            
            # Step 4: Prompt Optimization
            step_start_time = time.time()
            workflow_state["current_step"] = "prompt_optimization"
            step_id_4 = self._create_step_record(
                session_id=session_id,
                workflow_id=workflow_id,
                step_name="prompt_optimization",
                step_order=4,
                input_data={
                    "record_id": record_id,
                    "prompt": workflow_state["data"]["prompt_building"].get("prompt", "")
                }
            )
            if step_id_4:
                self._update_step_record(step_id_4, "in_progress")
            
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
                # Try to call optimize_prompt, with fallback if method doesn't exist
                # Use getattr with default to safely check and call the method
                optimize_prompt_method = getattr(self.prompt_optimizer, 'optimize_prompt', None)
                if optimize_prompt_method and callable(optimize_prompt_method):
                    optimized_prompt = await optimize_prompt_method(prompt)
                else:
                    # Fallback: use optimize method if optimize_prompt doesn't exist
                    safe_log(
                        logger,
                        logging.WARNING,
                        "optimize_prompt method not found, using fallback",
                        workflow_id=workflow_id,
                        available_methods=str([m for m in dir(self.prompt_optimizer) if not m.startswith('_')])
                    )
                    from app.models.schemas import PromptResponseSchema
                    prompt_response = PromptResponseSchema(
                        prompt=prompt,
                        scenario_type="extraction",
                        metadata={}
                    )
                    optimized_result = await self.prompt_optimizer.optimize(prompt_response)
                    optimized_prompt = {
                        "prompt": optimized_result.prompt if optimized_result.prompt else prompt,
                        "optimizations_applied": optimized_result.optimizations_applied if optimized_result.optimizations_applied else []
                    }
                
                workflow_state["data"]["prompt_optimization"] = {
                    "status": "completed",
                    "optimized_prompt": optimized_prompt.get("prompt", prompt),
                    "optimizations_applied": optimized_prompt.get("optimizations_applied", [])
                }
                workflow_state["steps_completed"].append("prompt_optimization")
                step_elapsed = time.time() - step_start_time
                self._update_step_record(
                    step_id_4,
                    "completed",
                    output_data={
                        "status": "completed",
                        "optimized_prompt": optimized_prompt.get("prompt", "")[:500] if optimized_prompt.get("prompt") else None
                    },
                    processing_time=step_elapsed
                )
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
                step_elapsed = time.time() - step_start_time
                self._update_step_record(
                    step_id_4,
                    "completed",
                    output_data={"status": "completed", "optimized_prompt": prompt[:500]},
                    processing_time=step_elapsed
                )
            
            # Step 5: MCP Formatting
            step_start_time = time.time()
            workflow_state["current_step"] = "mcp_formatting"
            
            # Prepare context for MCP (before creating step record)
            optimized_prompt = workflow_state["data"]["prompt_optimization"].get("optimized_prompt", "")
            preprocessed_data = workflow_state["data"].get("preprocessing", {}).get("preprocessed_data", {})
            
            # Get fields from preprocessed_data using helper function
            fields = extract_fields_from_preprocessed_data(preprocessed_data)
            
            # Log diagnostic information
            safe_log(
                logger,
                logging.INFO,
                "Extracting fields from preprocessed_data",
                workflow_id=workflow_id,
                preprocessed_data_type=type(preprocessed_data).__name__,
                fields_count=len(fields),
                has_preprocessed_data=preprocessed_data is not None
            )
            
            if not fields:
                # Fallback: get fields from salesforce_data in routing_result
                salesforce_data = routing_result.get("salesforce_data", {})
                if salesforce_data:
                    # Handle both Pydantic model and dict
                    if hasattr(salesforce_data, 'fields_to_fill'):
                        fields = salesforce_data.fields_to_fill
                    elif isinstance(salesforce_data, dict):
                        fields = salesforce_data.get("fields_to_fill", [])
                    
                    safe_log(
                        logger,
                        logging.INFO,
                        "Using fallback fields from salesforce_data",
                        workflow_id=workflow_id,
                        fields_count=len(fields)
                    )
            
            # Get documents from preprocessed_data using helper function
            documents = extract_documents_from_preprocessed_data(preprocessed_data)
            
            if not documents:
                # Fallback: get documents from salesforce_data in routing_result
                salesforce_data = routing_result.get("salesforce_data", {})
                if salesforce_data:
                    # Handle both Pydantic model and dict
                    if hasattr(salesforce_data, 'documents'):
                        documents = salesforce_data.documents
                    elif isinstance(salesforce_data, dict):
                        documents = salesforce_data.get("documents", [])
            
            safe_log(
                logger,
                logging.INFO,
                "Context prepared for MCP",
                workflow_id=workflow_id,
                fields_count=len(fields),
                documents_count=len(documents)
            )
            
            # Prepare context for MCP
            context = {
                "documents": documents,
                "fields": fields,
                "session_id": session_id if session_id != "none" else None
            }
            
            step_id_5 = self._create_step_record(
                session_id=session_id,
                workflow_id=workflow_id,
                step_name="mcp_formatting",
                step_order=5,
                input_data={
                    "record_id": record_id,
                    "prompt": optimized_prompt,
                    "context": context
                }
            )
            if step_id_5:
                self._update_step_record(step_id_5, "in_progress")
            
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
                self._update_step_record(
                    step_id_5,
                    "completed",
                    output_data={"status": "completed"},
                    processing_time=step_elapsed
                )
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
                step_elapsed = time.time() - step_start_time
                self._update_step_record(
                    step_id_5,
                    "failed",
                    error_message=error_msg,
                    error_details={"error_type": type(e).__name__},
                    processing_time=step_elapsed
                )
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
            step_id_6 = self._create_step_record(
                session_id=session_id,
                workflow_id=workflow_id,
                step_name="mcp_sending",
                step_order=6,
                input_data={
                    "record_id": record_id,
                    "prompt": workflow_state["data"]["prompt_optimization"].get("optimized_prompt", "")
                }
            )
            if step_id_6:
                self._update_step_record(step_id_6, "in_progress")
            
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
                    
                    # Get fields from preprocessed_data using helper function
                    fields = extract_fields_from_preprocessed_data(preprocessed_data)
                    
                    if not fields:
                        # Fallback: get fields from salesforce_data in routing_result
                        salesforce_data = routing_result.get("salesforce_data", {})
                        if salesforce_data:
                            # Handle both Pydantic model and dict
                            if hasattr(salesforce_data, 'fields_to_fill'):
                                fields = salesforce_data.fields_to_fill
                            elif isinstance(salesforce_data, dict):
                                fields = salesforce_data.get("fields_to_fill", [])
                    
                    # Get documents from preprocessed_data using helper function
                    documents = extract_documents_from_preprocessed_data(preprocessed_data)
                    
                    if not documents:
                        # Fallback: get documents from salesforce_data in routing_result
                        salesforce_data = routing_result.get("salesforce_data", {})
                        if salesforce_data:
                            # Handle both Pydantic model and dict
                            if hasattr(salesforce_data, 'documents'):
                                documents = salesforce_data.documents
                            elif isinstance(salesforce_data, dict):
                                documents = salesforce_data.get("documents", [])
                    
                    context = {
                        "documents": documents,
                        "fields": fields,
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
                    
                    # Store input_data in session before sending to langgraph
                    if session_id and session_id != "none":
                        try:
                            session_manager = get_session_manager()
                            # Get current session to update input_data
                            session = session_manager.storage.get_session(session_id)
                            if session:
                                input_data = session.get("input_data", {})
                                # Update input_data with current prompt and context
                                input_data["prompt"] = optimized_prompt
                                input_data["context"] = context
                                input_data["metadata"] = metadata
                                input_data["user_message"] = request_data.get("user_message", "")
                                input_data["timestamp"] = datetime.utcnow().isoformat()
                                
                                # Update session with new input_data
                                session_manager.storage.update_session(session_id, {"input_data": input_data})
                                
                                # Add interaction to history
                                interaction_id = str(uuid.uuid4())
                                interaction = {
                                    "interaction_id": interaction_id,
                                    "request": {
                                        "user_message": request_data.get("user_message", ""),
                                        "prompt": optimized_prompt,
                                        "timestamp": datetime.utcnow().isoformat()
                                    },
                                    "response": None,
                                    "processing_time": None,
                                    "status": "pending"
                                }
                                session_manager.storage.add_interaction_to_history(session_id, interaction)
                                
                                # Store interaction_id in workflow_state for later update
                                workflow_state["data"]["current_interaction_id"] = interaction_id
                                
                                safe_log(
                                    logger,
                                    logging.INFO,
                                    "Input data stored in session before langgraph",
                                    session_id=session_id,
                                    interaction_id=interaction_id
                                )
                        except Exception as e:
                            safe_log(
                                logger,
                                logging.WARNING,
                                "Failed to store input_data in session",
                                session_id=session_id,
                                error_type=type(e).__name__,
                                error_message=str(e) if e else "Unknown"
                            )
                            # Continue workflow even if storage fails
                
                mcp_response = await self.mcp_sender.send_to_langgraph(mcp_message, async_mode=False)
                
                # Extract response data
                extracted_data = mcp_response.extracted_data if hasattr(mcp_response, 'extracted_data') else {}
                confidence_scores = mcp_response.confidence_scores if hasattr(mcp_response, 'confidence_scores') else {}
                response_status = mcp_response.status if hasattr(mcp_response, 'status') else "unknown"
                
                # Log extracted_data details
                extracted_data_is_none = extracted_data is None
                extracted_data_is_empty = not extracted_data or len(extracted_data) == 0
                
                safe_log(
                    logger,
                    logging.INFO,
                    "MCP response received from LangGraph",
                    record_id=record_id,
                    session_id=session_id or "none",
                    response_status=response_status,
                    extracted_data_count=len(extracted_data) if extracted_data else 0,
                    extracted_data_is_none=extracted_data_is_none,
                    extracted_data_is_empty=extracted_data_is_empty,
                    extracted_data_keys=list(extracted_data.keys())[:10] if extracted_data else [],
                    confidence_scores_count=len(confidence_scores) if confidence_scores else 0,
                    has_extracted_data=bool(extracted_data)
                )
                
                workflow_state["data"]["mcp_sending"] = {
                    "status": "completed",
                    "mcp_response": {
                        "extracted_data": extracted_data,
                        "confidence_scores": confidence_scores,
                        "status": response_status
                    }
                }
                
                # Store langgraph response in session
                if session_id and session_id != "none":
                    try:
                        session_manager = get_session_manager()
                        step_elapsed = time.time() - step_start_time
                        
                        # Build langgraph response data
                        langgraph_response = {
                            "extracted_data": extracted_data,
                            "confidence_scores": confidence_scores,
                            "status": response_status,
                            "timestamp": datetime.utcnow().isoformat(),
                            "processing_time": step_elapsed
                        }
                        
                        # Store response
                        session_manager.store_langgraph_response(session_id, langgraph_response)
                        
                        # Update interaction in history with response
                        interaction_id = workflow_state["data"].get("current_interaction_id")
                        if interaction_id:
                            session_manager.update_interaction_response(
                                session_id=session_id,
                                interaction_id=interaction_id,
                                response=langgraph_response,
                                processing_time=step_elapsed,
                                status=response_status
                            )
                        
                        # Update processing metadata
                        session_manager.update_processing_metadata(session_id, {
                            "langgraph_processed": True,
                            "langgraph_processed_timestamp": datetime.utcnow().isoformat(),
                            "workflow_id": workflow_id
                        })
                        
                        safe_log(
                            logger,
                            logging.INFO,
                            "Langgraph response stored in session",
                            session_id=session_id,
                            extracted_fields=len(extracted_data)
                        )
                    except Exception as e:
                        safe_log(
                            logger,
                            logging.WARNING,
                            "Failed to store langgraph response in session",
                            session_id=session_id,
                            error_type=type(e).__name__,
                            error_message=str(e) if e else "Unknown"
                        )
                        # Continue workflow even if storage fails
                
                workflow_state["steps_completed"].append("mcp_sending")
                step_elapsed = time.time() - step_start_time
                self._update_step_record(
                    step_id_6,
                    "completed",
                    output_data={
                        "extracted_data": extracted_data,
                        "confidence_scores": confidence_scores,
                        "status": response_status
                    },
                    processing_time=step_elapsed
                )
                log_timing(
                    logger,
                    logging.INFO,
                    "Step 6 completed: MCP Sending",
                    elapsed_time=step_elapsed,
                    workflow_id=workflow_id,
                    extracted_fields=len(extracted_data)
                )
                
            except Exception as e:
                error_msg = str(e) if e else "Unknown error"
                workflow_state["errors"].append({
                    "step": "mcp_sending",
                    "error": error_msg,
                    "error_type": type(e).__name__
                })
                workflow_state["status"] = "failed"
                step_elapsed = time.time() - step_start_time
                self._update_step_record(
                    step_id_6,
                    "failed",
                    error_message=error_msg,
                    error_details={"error_type": type(e).__name__},
                    processing_time=step_elapsed
                )
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
            step_id_7 = self._create_step_record(
                session_id=session_id,
                workflow_id=workflow_id,
                step_name="response_handling",
                step_order=7,
                input_data={
                    "record_id": record_id,
                    "mcp_response": workflow_state["data"]["mcp_sending"].get("mcp_response", {})
                }
            )
            if step_id_7:
                self._update_step_record(step_id_7, "in_progress")
            
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
                
                # Log mcp_response_data details
                extracted_data_from_response = mcp_response_data.get("extracted_data", {})
                extracted_data_is_none = extracted_data_from_response is None
                extracted_data_is_empty = not extracted_data_from_response or len(extracted_data_from_response) == 0
                
                safe_log(
                    logger,
                    logging.INFO,
                    "Processing response_handling step",
                    record_id=record_id,
                    session_id=session_id or "none",
                    mcp_response_status=mcp_response_data.get("status", "unknown"),
                    extracted_data_count=len(extracted_data_from_response) if extracted_data_from_response else 0,
                    extracted_data_is_none=extracted_data_is_none,
                    extracted_data_is_empty=extracted_data_is_empty,
                    extracted_data_keys=list(extracted_data_from_response.keys())[:10] if extracted_data_from_response else [],
                    has_extracted_data=bool(extracted_data_from_response),
                    mcp_response_keys=list(mcp_response_data.keys())
                )
                
                workflow_state["data"]["response_handling"] = {
                    "status": "completed",
                    "extracted_data": extracted_data_from_response if extracted_data_from_response else {},
                    "confidence_scores": mcp_response_data.get("confidence_scores", {}),
                    "final_status": mcp_response_data.get("status", "success")
                }
                workflow_state["steps_completed"].append("response_handling")
                step_elapsed = time.time() - step_start_time
                self._update_step_record(
                    step_id_7,
                    "completed",
                    output_data={
                        "extracted_data": mcp_response_data.get("extracted_data", {}),
                        "confidence_scores": mcp_response_data.get("confidence_scores", {}),
                        "status": mcp_response_data.get("status", "success")
                    },
                    processing_time=step_elapsed
                )
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
                self._update_step_record(
                    step_id_7,
                    "completed",
                    output_data={"status": "error"},
                    error_message=error_msg,
                    processing_time=step_elapsed
                )
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
        response_data = workflow_state.get("data", {})
        
        # Extract extracted_data from response_handling or mcp_sending for easy access
        extracted_data = {}
        confidence_scores = {}
        quality_score = None
        
        # Try to get from response_handling first (most recent)
        response_handling = response_data.get("response_handling", {})
        if response_handling:
            extracted_data = response_handling.get("extracted_data", {}) or {}
            confidence_scores = response_handling.get("confidence_scores", {}) or {}
        
        # Fallback to mcp_sending if response_handling doesn't have it
        if not extracted_data:
            mcp_sending = response_data.get("mcp_sending", {})
            mcp_response = mcp_sending.get("mcp_response", {}) if mcp_sending else {}
            if mcp_response:
                extracted_data = mcp_response.get("extracted_data", {}) or {}
                confidence_scores = mcp_response.get("confidence_scores", {}) or {}
                quality_score = mcp_response.get("quality_score")
        
        # Build response with extracted_data at root level for easy access
        response = {
            "status": workflow_state.get("status", "unknown"),
            "workflow_id": workflow_state.get("workflow_id"),
            "current_step": workflow_state.get("current_step"),
            "steps_completed": workflow_state.get("steps_completed", []),
            "data": response_data,
            "errors": workflow_state.get("errors", []),
            "started_at": workflow_state.get("started_at"),
            "completed_at": workflow_state.get("completed_at")
        }
        
        # Add extracted_data at root level if available (for backward compatibility and easy access)
        if extracted_data:
            response["extracted_data"] = extracted_data
            response["confidence_scores"] = confidence_scores
            if quality_score is not None:
                response["quality_score"] = quality_score
            
            safe_log(
                logger,
                logging.INFO,
                "Added extracted_data to root level of workflow response",
                extracted_data_count=len(extracted_data),
                confidence_scores_count=len(confidence_scores),
                quality_score=quality_score
            )
        
        return response

