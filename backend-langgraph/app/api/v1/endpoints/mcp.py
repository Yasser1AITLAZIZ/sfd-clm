"""MCP endpoint for processing requests"""
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional
import logging
import uuid
import random
import asyncio
from datetime import datetime

from app.core.logging import get_logger, safe_log
from app.core.config import settings
from app.state import MCPAgentState, Document, PageOCR
from app.utils.singletons import get_compiled_graph
from app.utils.mock_data_generator import MockDataGenerator
from app.utils.metrics import MetricsCollector
from app.utils.memory_manager import MemoryManager

logger = get_logger(__name__)

router = APIRouter()


def generate_mock_extracted_data(fields_dictionary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate intelligent mock extracted data with field relationships.
    
    Args:
        fields_dictionary: Dictionary of field definitions
        
    Returns:
        Dictionary of extracted field values
    """
    generator = MockDataGenerator()
    extracted_data = generator.generate_extracted_data(fields_dictionary)
    
    # Validate consistency
    validated_data = generator.validate_data_consistency(extracted_data, fields_dictionary)
    
    return validated_data


def generate_mock_confidence_scores(
    extracted_data: Dict[str, Any],
    fields_dictionary: Dict[str, Any]
) -> Dict[str, float]:
    """
    Generate mock confidence scores for extracted data.
    
    Args:
        extracted_data: Dictionary of extracted field values
        fields_dictionary: Dictionary of field definitions
        
    Returns:
        Dictionary of confidence scores (0.0-1.0)
    """
    confidence_scores = {}
    
    for field_name, value in extracted_data.items():
        if value is None:
            confidence_scores[field_name] = 0.0
            continue
        
        field_config = fields_dictionary.get(field_name, {})
        is_required = field_config.get("required", False)
        field_type = field_config.get("type", "text").lower()
        
        # Required fields have higher confidence (0.85-0.95)
        if is_required:
            confidence_scores[field_name] = round(random.uniform(0.85, 0.95), 2)
        # Picklist/radio with possible values have high confidence (0.80-0.95)
        elif field_type in ["picklist", "radio"] and field_config.get("possibleValues"):
            confidence_scores[field_name] = round(random.uniform(0.80, 0.95), 2)
        # Optional fields have lower confidence (0.70-0.85)
        else:
            confidence_scores[field_name] = round(random.uniform(0.70, 0.85), 2)
    
    return confidence_scores


def generate_mock_ocr_data(documents: list) -> Dict[str, Any]:
    """
    Generate mock OCR data based on documents.
    
    Args:
        documents: List of document data
        
    Returns:
        Dictionary with ocr_text_length, text_blocks_count, and field_mappings
    """
    total_pages = sum(len(doc.get("pages", [])) for doc in documents)
    
    # Estimate OCR text length (roughly 500-2000 chars per page)
    ocr_text_length = total_pages * random.randint(500, 2000)
    
    # Estimate text blocks (roughly 10-30 blocks per page)
    text_blocks_count = total_pages * random.randint(10, 30)
    
    # Generate sample OCR text
    ocr_text = " ".join([
        "Document traité avec succès.",
        "Texte extrait automatiquement pour simulation.",
        "Données OCR générées pour les tests."
    ] * (total_pages * 2))
    
    return {
        "ocr_text_length": ocr_text_length,
        "text_blocks_count": text_blocks_count,
        "ocr_text": ocr_text[:ocr_text_length]  # Truncate to estimated length
    }


async def mock_process_mcp_request(request: Request) -> JSONResponse:
    """
    Mock MCP request processing that simulates the full workflow.
    
    Returns mock data in the exact format expected by backend-mcp.
    """
    request_id = str(uuid.uuid4())
    record_id = None
    session_id = None
    
    try:
        # Parse request body
        body = await request.json()
        
        record_id = body.get("record_id", "")
        session_id = body.get("session_id")
        user_request = body.get("user_request", "")
        documents_data = body.get("documents", [])
        fields_dictionary = body.get("fields_dictionary", {})
        
        # Validate required fields
        if not record_id or not record_id.strip():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_RECORD_ID",
                        "message": "record_id cannot be empty"
                    }
                }
            )
        
        safe_log(
            logger,
            logging.INFO,
            "Mock MCP request received",
            request_id=request_id,
            record_id=record_id,
            session_id=session_id or "none",
            documents_count=len(documents_data),
            fields_count=len(fields_dictionary),
            fields_dict_keys=list(fields_dictionary.keys())[:5] if fields_dictionary else []
        )
        
        # Simulate processing time (1-3 seconds)
        processing_time = random.uniform(1.0, 3.0)
        await asyncio.sleep(processing_time)
        
        # Generate mock extracted data
        extracted_data = generate_mock_extracted_data(fields_dictionary)
        
        safe_log(
            logger,
            logging.INFO,
            "Mock extracted data generated",
            request_id=request_id,
            fields_dict_count=len(fields_dictionary),
            fields_dict_keys=list(fields_dictionary.keys())[:10] if fields_dictionary else [],
            extracted_data_count=len(extracted_data),
            extracted_data_keys=list(extracted_data.keys())[:10] if extracted_data else []
        )
        
        # Generate mock confidence scores
        confidence_scores = generate_mock_confidence_scores(extracted_data, fields_dictionary)
        
        # Calculate quality score (average of confidence scores)
        if confidence_scores:
            quality_score = round(sum(confidence_scores.values()) / len(confidence_scores), 2)
        else:
            quality_score = 0.85
        
        # Generate mock OCR data
        ocr_data = generate_mock_ocr_data(documents_data)
        
        # Generate field mappings (map each field to a location in OCR text)
        field_mappings = {}
        for field_name in extracted_data.keys():
            if extracted_data[field_name] is not None:
                field_mappings[field_name] = {
                    "location": f"Page 1, Block {random.randint(1, 20)}",
                    "confidence": confidence_scores.get(field_name, 0.85)
                }
        
        safe_log(
            logger,
            logging.INFO,
            "Mock MCP request processed",
            request_id=request_id,
            record_id=record_id,
            fields_extracted=len(extracted_data),
            quality_score=quality_score,
            processing_time=processing_time
        )
        
        # Build response in exact format expected by backend-mcp
        response_data = {
            "extracted_data": extracted_data,
            "confidence_scores": confidence_scores,
            "quality_score": quality_score,
            "field_mappings": field_mappings,
            "processing_time": round(processing_time, 2),
            "ocr_text_length": ocr_data["ocr_text_length"],
            "text_blocks_count": ocr_data["text_blocks_count"]
        }
        
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
            "Error in mock MCP request processing",
            request_id=request_id,
            record_id=record_id or "unknown",
            session_id=session_id or "none",
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred in mock mode",
                    "details": str(e) if e else None
                }
            }
        )


@router.post(
    "/api/langgraph/process-mcp-request",
    status_code=status.HTTP_200_OK,
    summary="Process MCP request with LangGraph",
    description="Receives MCP request with documents and fields, processes with OCR and mapping, returns extracted data"
)
async def process_mcp_request(request: Request) -> JSONResponse:
    """
    Process MCP request using LangGraph workflow.
    
    Expected request body:
    {
        "record_id": "string",
        "session_id": "string (optional)",
        "user_request": "string",
        "documents": [
            {
                "id": "string",
                "type": "string",
                "pages": [
                    {
                        "page_number": 1,
                        "image_b64": "base64 string",
                        "image_mime": "image/jpeg"
                    }
                ]
            }
        ],
        "fields_dictionary": {
            "field_name": {
                "label": "string",
                "type": "string",
                "required": bool,
                "possibleValues": []
            }
        }
    }
    """
    # Check if mock mode is enabled
    if settings.mock_mode:
        return await mock_process_mcp_request(request)
    
    # Original LangGraph processing
    request_id = str(uuid.uuid4())
    record_id = None
    session_id = None
    
    try:
        # Parse request body
        body = await request.json()
        
        record_id = body.get("record_id", "")
        session_id = body.get("session_id")
        user_request = body.get("user_request", "")
        documents_data = body.get("documents", [])
        fields_dictionary = body.get("fields_dictionary", {})
        
        # Validate required fields
        if not record_id or not record_id.strip():
            safe_log(
                logger,
                logging.WARNING,
                "Empty record_id provided",
                request_id=request_id,
                endpoint="/api/langgraph/process-mcp-request"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_RECORD_ID",
                        "message": "record_id cannot be empty"
                    }
                }
            )
        
        if not user_request or not user_request.strip():
            safe_log(
                logger,
                logging.WARNING,
                "Empty user_request provided",
                request_id=request_id,
                record_id=record_id
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_USER_REQUEST",
                        "message": "user_request cannot be empty"
                    }
                }
            )
        
        safe_log(
            logger,
            logging.INFO,
            "MCP request received",
            request_id=request_id,
            record_id=record_id,
            session_id=session_id or "none",
            documents_count=len(documents_data),
            fields_count=len(fields_dictionary)
        )
        
        # Validate and convert documents data to Document objects
        documents = []
        documents_validation_errors = []
        
        safe_log(
            logger,
            logging.INFO,
            "Validating documents before conversion",
            request_id=request_id,
            record_id=record_id,
            documents_data_count=len(documents_data),
            documents_data_type=type(documents_data).__name__
        )
        
        for idx, doc_data in enumerate(documents_data):
            try:
                # Validate document structure
                if not isinstance(doc_data, dict):
                    documents_validation_errors.append(f"Document {idx}: not a dict, got {type(doc_data).__name__}")
                    continue
                
                doc_id = doc_data.get("id") or str(uuid.uuid4())
                doc_type = doc_data.get("type", "")
                pages_data = doc_data.get("pages", [])
                
                safe_log(
                    logger,
                    logging.DEBUG,
                    f"Processing document {idx}",
                    request_id=request_id,
                    doc_id=doc_id,
                    doc_type=doc_type,
                    pages_count=len(pages_data) if isinstance(pages_data, list) else 0
                )
                
                # Validate and convert pages
                pages = []
                if not isinstance(pages_data, list):
                    documents_validation_errors.append(f"Document {idx} ({doc_id}): pages is not a list, got {type(pages_data).__name__}")
                    continue
                
                for page_idx, page_data in enumerate(pages_data):
                    try:
                        if not isinstance(page_data, dict):
                            documents_validation_errors.append(f"Document {idx} ({doc_id}), page {page_idx}: not a dict")
                            continue
                        
                        image_b64 = page_data.get("image_b64", "")
                        if not image_b64 or not isinstance(image_b64, str):
                            documents_validation_errors.append(f"Document {idx} ({doc_id}), page {page_idx}: missing or invalid image_b64")
                            continue
                        
                        # Validate base64 format (basic check)
                        if len(image_b64) < 100:  # Base64 images should be longer
                            documents_validation_errors.append(f"Document {idx} ({doc_id}), page {page_idx}: image_b64 too short (likely invalid)")
                            continue
                        
                        pages.append(PageOCR(
                            page_number=page_data.get("page_number", page_idx + 1),
                            image_b64=image_b64,
                            image_mime=page_data.get("image_mime", "image/jpeg"),
                            processed=False
                        ))
                    except Exception as e:
                        documents_validation_errors.append(f"Document {idx} ({doc_id}), page {page_idx}: error {type(e).__name__}: {str(e)}")
                        continue
                
                if not pages:
                    documents_validation_errors.append(f"Document {idx} ({doc_id}): no valid pages found")
                    continue
                
                documents.append(Document(
                    id=doc_id,
                    type=doc_type,
                    pages=pages,
                    metadata=doc_data.get("metadata", {})
                ))
                
                safe_log(
                    logger,
                    logging.INFO,
                    f"Document {idx} converted successfully",
                    request_id=request_id,
                    doc_id=doc_id,
                    pages_count=len(pages)
                )
                
            except Exception as e:
                documents_validation_errors.append(f"Document {idx}: unexpected error {type(e).__name__}: {str(e)}")
                continue
        
        # Log validation results
        safe_log(
            logger,
            logging.INFO,
            "Documents validation completed",
            request_id=request_id,
            record_id=record_id,
            documents_count=len(documents),
            validation_errors_count=len(documents_validation_errors),
            validation_errors=documents_validation_errors[:5] if documents_validation_errors else []
        )
        
        # If no valid documents, return error
        if not documents:
            error_msg = "No valid documents found in request"
            if documents_validation_errors:
                error_msg += f". Errors: {'; '.join(documents_validation_errors[:3])}"
            
            safe_log(
                logger,
                logging.ERROR,
                "No valid documents after validation",
                request_id=request_id,
                record_id=record_id,
                validation_errors=documents_validation_errors
            )
            
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_DOCUMENTS",
                        "message": error_msg,
                        "details": documents_validation_errors[:10]  # Limit to first 10 errors
                    }
                }
            )
        
        # Initialize state
        initial_state = MCPAgentState(
            record_id=record_id,
            session_id=session_id,
            user_request=user_request,
            documents=documents,
            fields_dictionary=fields_dictionary,
            remaining_steps=50
        )
        
        # Add initial user message
        from langchain_core.messages import HumanMessage
        initial_state.messages.append(HumanMessage(content=user_request))
        
        # Initialize metrics collector
        metrics = MetricsCollector(request_id=request_id)
        memory_manager = MemoryManager()
        memory_manager.log_memory_usage("before processing")
        
        # Get compiled graph and execute
        graph = get_compiled_graph()
        
        safe_log(
            logger,
            logging.INFO,
            "Starting LangGraph execution",
            request_id=request_id,
            record_id=record_id
        )
        
        metrics.start_step("total_processing")
        start_time = datetime.utcnow()
        
        # Execute graph
        config = {"configurable": {"thread_id": f"{record_id}_{session_id or 'new'}"}}
        final_state_raw = await graph.ainvoke(initial_state, config)
        
        # Convert to MCPAgentState if it's a dict (LangGraph sometimes returns dict)
        if isinstance(final_state_raw, dict):
            final_state = MCPAgentState(**final_state_raw)
        elif isinstance(final_state_raw, MCPAgentState):
            final_state = final_state_raw
        else:
            # Fallback: try to convert
            try:
                final_state = MCPAgentState(**final_state_raw) if hasattr(final_state_raw, '__dict__') else MCPAgentState.model_validate(final_state_raw)
            except Exception as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Failed to convert final_state to MCPAgentState",
                    request_id=request_id,
                    record_id=record_id,
                    final_state_type=type(final_state_raw).__name__,
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
                raise ValueError(f"Cannot convert final_state to MCPAgentState: {type(final_state_raw)}") from e
        
        metrics.end_step("total_processing")
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Extract data from final_state with safe access
        # Use getattr for Pydantic models, .get() for dicts
        extracted_data = getattr(final_state, 'extracted_data', None) or (final_state.get('extracted_data', {}) if isinstance(final_state, dict) else {})
        confidence_scores = getattr(final_state, 'confidence_scores', None) or (final_state.get('confidence_scores', {}) if isinstance(final_state, dict) else {})
        quality_score = getattr(final_state, 'quality_score', None) or (final_state.get('quality_score') if isinstance(final_state, dict) else None)
        field_mappings = getattr(final_state, 'field_mappings', None) or (final_state.get('field_mappings', {}) if isinstance(final_state, dict) else {})
        ocr_text = getattr(final_state, 'ocr_text', None) or (final_state.get('ocr_text') if isinstance(final_state, dict) else None)
        text_blocks = getattr(final_state, 'text_blocks', None) or (final_state.get('text_blocks', []) if isinstance(final_state, dict) else [])
        
        # Record field success rates
        for field_name, value in (extracted_data.items() if extracted_data else []):
            confidence = confidence_scores.get(field_name, 0.0) if confidence_scores else 0.0
            metrics.record_field_success(field_name, value is not None, confidence)
        
        # Record final memory usage
        memory_info = memory_manager.get_memory_usage()
        if memory_info:
            metrics.record_memory_usage(memory_info)
        memory_manager.log_memory_usage("after processing")
        
        # Get metrics summary and store
        metrics_summary = metrics.get_summary()
        full_metrics = metrics.get_full_metrics()
        metrics.log_summary()
        
        # Store metrics for later retrieval
        from app.api.v1.endpoints.metrics import store_metrics
        store_metrics(request_id, full_metrics)
        
        # Log final state details before building response
        extracted_data_is_empty = not extracted_data or len(extracted_data) == 0
        extracted_data_is_none = extracted_data is None
        
        safe_log(
            logger,
            logging.INFO,
            "LangGraph execution completed",
            request_id=request_id,
            record_id=record_id,
            execution_time=execution_time,
            fields_extracted=len(extracted_data) if extracted_data else 0,
            quality_score=quality_score,
            extracted_data_is_none=extracted_data_is_none,
            extracted_data_is_empty=extracted_data_is_empty,
            extracted_data_keys=list(extracted_data.keys())[:10] if extracted_data else []
        )
        
        # Build response with proper serialization
        try:
            # Ensure all data is JSON-serializable
            def serialize_value(value):
                """Recursively serialize values for JSON"""
                if value is None:
                    return None
                elif isinstance(value, (str, int, float, bool)):
                    return value
                elif isinstance(value, dict):
                    return {k: serialize_value(v) for k, v in value.items()}
                elif isinstance(value, list):
                    return [serialize_value(item) for item in value]
                elif hasattr(value, 'model_dump'):
                    return value.model_dump()
                elif hasattr(value, 'dict'):
                    return value.dict()
                else:
                    return str(value)
            
            # Serialize field_mappings to ensure it's JSON-compatible
            serialized_field_mappings = serialize_value(field_mappings) if field_mappings else {}
            
            response_data = {
                "extracted_data": serialize_value(extracted_data) if extracted_data else {},
                "confidence_scores": serialize_value(confidence_scores) if confidence_scores else {},
                "quality_score": quality_score,
                "field_mappings": serialized_field_mappings,
                "processing_time": execution_time,
                "ocr_text_length": len(ocr_text or "") if ocr_text else 0,
                "text_blocks_count": len(text_blocks) if text_blocks else 0,
                "metrics": serialize_value(metrics_summary) if metrics_summary else {}
            }
            
            # Test JSON serialization before returning
            try:
                import json
                json.dumps(response_data, default=str, ensure_ascii=False)
            except (TypeError, ValueError) as json_error:
                safe_log(
                    logger,
                    logging.ERROR,
                    "JSON serialization test failed before returning response",
                    request_id=request_id,
                    record_id=record_id,
                    error_type=type(json_error).__name__,
                    error_message=str(json_error),
                    extracted_data_type=type(final_state.extracted_data).__name__,
                    field_mappings_type=type(final_state.field_mappings).__name__
                )
                raise ValueError(f"Response data is not JSON-serializable: {json_error}") from json_error
            
            # Log response data details before returning
            safe_log(
                logger,
                logging.INFO,
                "LangGraph response data prepared",
                request_id=request_id,
                record_id=record_id,
                response_status="success",
                extracted_data_count=len(response_data.get("extracted_data", {})),
                extracted_data_keys=list(response_data.get("extracted_data", {}).keys())[:10],
                confidence_scores_count=len(response_data.get("confidence_scores", {})),
                quality_score=response_data.get("quality_score"),
                has_extracted_data=bool(response_data.get("extracted_data")),
                extracted_data_is_empty=not response_data.get("extracted_data") or len(response_data.get("extracted_data", {})) == 0
            )
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "success",
                    "data": response_data
                }
            )
            
        except Exception as build_error:
            # Catch errors during response building
            safe_log(
                logger,
                logging.ERROR,
                "Error building response data",
                request_id=request_id,
                record_id=record_id,
                error_type=type(build_error).__name__,
                error_message=str(build_error),
                extracted_data_type=type(final_state.extracted_data).__name__ if hasattr(final_state, 'extracted_data') else "unknown",
                field_mappings_type=type(final_state.field_mappings).__name__ if hasattr(final_state, 'field_mappings') else "unknown"
            )
            import traceback
            logger.error(f"Response building traceback:\n{traceback.format_exc()}")
            raise  # Re-raise to be caught by outer exception handler
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        
        # Log to console with full traceback for debugging
        logger.error(
            f"Error processing MCP request: {type(e).__name__}: {str(e)}\n"
            f"Request ID: {request_id}\n"
            f"Record ID: {record_id or 'unknown'}\n"
            f"Full traceback:\n{error_traceback}"
        )
        
        safe_log(
            logger,
            logging.ERROR,
            "Error processing MCP request",
            request_id=request_id,
            record_id=record_id or "unknown",
            session_id=session_id or "none",
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error",
            traceback=error_traceback
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred",
                    "details": str(e) if e else None,
                    "error_type": type(e).__name__
                }
            }
        )

