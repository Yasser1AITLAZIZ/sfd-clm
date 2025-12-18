"""Mock Apex endpoints for simulating Salesforce Apex Controller"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Any, Dict
import logging
import uuid
from datetime import datetime

from app.models.schemas import SendUserRequestSchema, SendUserRequestResponseSchema
from app.core.logging import get_logger, safe_log

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/mock/apex/send-user-request",
    response_model=SendUserRequestResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Mock Apex - Send user request",
    description="Simulates Salesforce Apex Controller sending user request to MCP backend"
)
async def send_user_request(request: SendUserRequestSchema) -> JSONResponse:
    """
    Mock endpoint simulating Apex Controller sending user request.
    
    This endpoint simulates the behavior of Salesforce Apex Controller
    sending record_id, session_id, and user_request to the MCP backend.
    """
    record_id = None
    session_id = None
    user_request = None
    
    try:
        # Validate input
        if not request:
            safe_log(
                logger,
                logging.ERROR,
                "Invalid request object",
                endpoint="/mock/apex/send-user-request"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "Invalid request format",
                        "details": None
                    }
                }
            )
        
        # Extract fields with defensive checks
        record_id = request.record_id if request.record_id else None
        session_id = request.session_id if request.session_id else None
        user_request = request.user_request if request.user_request else None
        
        # Validate required fields
        if not record_id or not record_id.strip():
            safe_log(
                logger,
                logging.WARNING,
                "Empty record_id provided",
                endpoint="/mock/apex/send-user-request"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_RECORD_ID",
                        "message": "record_id cannot be empty",
                        "details": None
                    }
                }
            )
        
        if not user_request or not user_request.strip():
            safe_log(
                logger,
                logging.WARNING,
                "Empty user_request provided",
                endpoint="/mock/apex/send-user-request",
                record_id=record_id or "none"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_USER_REQUEST",
                        "message": "user_request cannot be empty",
                        "details": None
                    }
                }
            )
        
        record_id = record_id.strip()
        user_request = user_request.strip()
        if session_id:
            session_id = session_id.strip()
        
        # Generate request_id
        request_id = str(uuid.uuid4())
        
        # Log request
        safe_log(
            logger,
            logging.INFO,
            "User request received from mock Apex",
            request_id=request_id,
            record_id=record_id,
            session_id=session_id or "none",
            user_request_length=len(user_request),
            endpoint="/mock/apex/send-user-request"
        )
        
        # Simulate sending to MCP backend (in real scenario, this would be an HTTP call)
        # For now, we just return acknowledgment
        
        # Build response
        response_data = {
            "status": "sent",
            "request_id": request_id,
            "record_id": record_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        safe_log(
            logger,
            logging.INFO,
            "User request sent successfully",
            request_id=request_id,
            record_id=record_id,
            session_id=session_id or "none"
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "data": response_data
            }
        )
        
    except Exception as e:
        # Catch-all for unexpected errors
        safe_log(
            logger,
            logging.ERROR,
            "Unexpected error in send_user_request",
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
                    "details": None
                }
            }
        )

