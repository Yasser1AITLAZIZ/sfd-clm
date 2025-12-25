"""MCP endpoint for processing requests"""
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional
import logging
import uuid
from datetime import datetime

from app.core.logging import get_logger, safe_log
from app.state import MCPAgentState, Document, PageOCR
from app.utils.singletons import get_compiled_graph

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/api/langgraph/process-mcp-request",
    status_code=status.HTTP_200_OK,
    summary="Process MCP request with LangGraph",
    description="Receives MCP request with documents and fields, processes with OCR and mapping, returns extracted data"
)
async def process_mcp_request(request: Request, http_request: Request) -> JSONResponse:
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
        
        # Get compiled graph and execute
        graph = get_compiled_graph()
        
        safe_log(
            logger,
            logging.INFO,
            "Starting LangGraph execution",
            request_id=request_id,
            record_id=record_id
        )
        
        start_time = datetime.utcnow()
        
        # Execute graph
        config = {"configurable": {"thread_id": f"{record_id}_{session_id or 'new'}"}}
        final_state = await graph.ainvoke(initial_state, config)
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        safe_log(
            logger,
            logging.INFO,
            "LangGraph execution completed",
            request_id=request_id,
            record_id=record_id,
            execution_time=execution_time,
            fields_extracted=len(final_state.extracted_data),
            quality_score=final_state.quality_score
        )
        
        # Build response
        response_data = {
            "extracted_data": final_state.extracted_data,
            "confidence_scores": final_state.confidence_scores,
            "quality_score": final_state.quality_score,
            "field_mappings": final_state.field_mappings,
            "processing_time": execution_time,
            "ocr_text_length": len(final_state.ocr_text or ""),
            "text_blocks_count": len(final_state.text_blocks)
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

