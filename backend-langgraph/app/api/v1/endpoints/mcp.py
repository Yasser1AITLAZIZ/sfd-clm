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
        
        # Convert documents data to Document objects
        documents = []
        for doc_data in documents_data:
            pages = []
            for page_data in doc_data.get("pages", []):
                pages.append(PageOCR(
                    page_number=page_data.get("page_number", 1),
                    image_b64=page_data.get("image_b64", ""),
                    image_mime=page_data.get("image_mime", "image/jpeg"),
                    processed=False
                ))
            
            documents.append(Document(
                id=doc_data.get("id", str(uuid.uuid4())),
                type=doc_data.get("type", ""),
                pages=pages,
                metadata=doc_data.get("metadata", {})
            ))
        
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
        final_state = await graph.ainvoke(initial_state, config)
        
        metrics.end_step("total_processing")
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Record field success rates
        for field_name, value in final_state.extracted_data.items():
            confidence = final_state.confidence_scores.get(field_name, 0.0)
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
        extracted_data_is_empty = not final_state.extracted_data or len(final_state.extracted_data) == 0
        extracted_data_is_none = final_state.extracted_data is None
        
        safe_log(
            logger,
            logging.INFO,
            "LangGraph execution completed",
            request_id=request_id,
            record_id=record_id,
            execution_time=execution_time,
            fields_extracted=len(final_state.extracted_data) if final_state.extracted_data else 0,
            quality_score=final_state.quality_score,
            extracted_data_is_none=extracted_data_is_none,
            extracted_data_is_empty=extracted_data_is_empty,
            extracted_data_keys=list(final_state.extracted_data.keys())[:10] if final_state.extracted_data else []
        )
        
        # Build response
        response_data = {
            "extracted_data": final_state.extracted_data,
            "confidence_scores": final_state.confidence_scores,
            "quality_score": final_state.quality_score,
            "field_mappings": final_state.field_mappings,
            "processing_time": execution_time,
            "ocr_text_length": len(final_state.ocr_text or ""),
            "text_blocks_count": len(final_state.text_blocks),
            "metrics": metrics_summary
        }
        
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
        
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Error processing MCP request",
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
                    "message": "An internal server error occurred",
                    "details": str(e) if e else None
                }
            }
        )

