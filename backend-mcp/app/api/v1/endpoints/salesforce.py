"""Salesforce MCP endpoints"""
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional
import logging

from app.models.schemas import (
    ReceiveRequestSchema,
    RequestSalesforceDataSchema,
    InitializationResponseSchema,
    ContinuationResponseSchema,
    ErrorResponseSchema
)
from app.services.session_router import validate_and_route
from app.services.salesforce_client import fetch_salesforce_data
from app.services.workflow_orchestrator import WorkflowOrchestrator
from app.core.exceptions import (
    SalesforceClientError,
    SessionNotFoundError,
    InvalidRequestError
)
from app.core.logging import get_logger, safe_log

logger = get_logger(__name__)

router = APIRouter()

# Global workflow orchestrator instance
_workflow_orchestrator: Optional[WorkflowOrchestrator] = None


def get_workflow_orchestrator() -> WorkflowOrchestrator:
    """Get or create workflow orchestrator instance"""
    global _workflow_orchestrator
    if _workflow_orchestrator is None:
        _workflow_orchestrator = WorkflowOrchestrator()
    return _workflow_orchestrator


@router.post(
    "/api/mcp/receive-request",
    status_code=status.HTTP_200_OK,
    summary="Receive user request from Salesforce",
    description="Main endpoint receiving record_id, session_id, and user_message. Routes to initialization or continuation flow."
)
async def receive_request(request: ReceiveRequestSchema, http_request: Request) -> JSONResponse:
    """
    Receive request from Salesforce Apex Controller.
    
    Implements robust error handling and defensive logging.
    """
    record_id = None
    session_id = None
    user_message = None
    
    try:
        # Validate input
        if not request:
            safe_log(
                logger,
                logging.ERROR,
                "Invalid request object",
                endpoint="/api/mcp/receive-request"
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
        
        # Extract and validate fields
        record_id = request.record_id if request.record_id else None
        session_id = request.session_id if request.session_id else None
        user_message = request.user_message if request.user_message else None
        
        # #region agent log
        with open(r"c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log", "a") as f:
            import json
            from datetime import datetime
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"salesforce.py:225","message":"Validation check - record_id","data":{"record_id":record_id if record_id else "none","is_empty":not record_id or not record_id.strip()},"timestamp":int(datetime.utcnow().timestamp()*1000)}) + "\n")
        # #endregion
        # Validate required fields
        if not record_id or not record_id.strip():
            safe_log(
                logger,
                logging.WARNING,
                "Empty record_id provided",
                endpoint="/api/mcp/receive-request",
                session_id=session_id or "none"
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
        
        if not user_message or not user_message.strip():
            safe_log(
                logger,
                logging.WARNING,
                "Empty user_message provided",
                endpoint="/api/mcp/receive-request",
                record_id=record_id or "none",
                session_id=session_id or "none"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_USER_MESSAGE",
                        "message": "user_message cannot be empty",
                        "details": None
                    }
                }
            )
        
        record_id = record_id.strip()
        user_message = user_message.strip()
        if session_id:
            session_id = session_id.strip()
        
        # Store in request state for logging
        http_request.state.record_id = record_id
        http_request.state.session_id = session_id or "none"
        
        # Log request
        safe_log(
            logger,
            logging.INFO,
            "Request received",
            record_id=record_id,
            session_id=session_id or "none",
            user_message_length=len(user_message),
            endpoint="/api/mcp/receive-request"
        )
        
        # Execute workflow using WorkflowOrchestrator
        try:
            workflow_orchestrator = get_workflow_orchestrator()
            
            # Prepare request data for workflow
            request_data = {
                "record_id": record_id,
                "session_id": session_id,
                "user_message": user_message
            }
            
            # Execute workflow
            workflow_result = await workflow_orchestrator.execute_workflow(request_data)
            
            # Extract routing result from workflow data
            routing_result = workflow_result.get("data", {}).get("routing", {})
            
            # If workflow failed, return error
            if workflow_result.get("status") == "failed":
                errors = workflow_result.get("errors", [])
                error_msg = errors[0].get("error", "Workflow execution failed") if errors else "Workflow execution failed"
                
                safe_log(
                    logger,
                    logging.ERROR,
                    "Workflow execution failed",
                    record_id=record_id,
                    session_id=session_id or "none",
                    errors=errors
                )
                
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": "error",
                        "error": {
                            "code": "WORKFLOW_ERROR",
                            "message": error_msg,
                            "details": {
                                "workflow_id": workflow_result.get("workflow_id"),
                                "errors": errors
                            }
                        }
                    }
                )
        except InvalidRequestError as e:
            safe_log(
                logger,
                logging.WARNING,
                "Invalid request error in routing",
                record_id=record_id,
                session_id=session_id or "none",
                error_type="InvalidRequestError",
                error_message=str(e) if e else "Unknown"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": str(e) if e else "Invalid request parameters",
                        "details": None
                    }
                }
            )
        except SessionNotFoundError as e:
            safe_log(
                logger,
                logging.WARNING,
                "Session not found",
                record_id=record_id,
                session_id=session_id or "none",
                error_type="SessionNotFoundError",
                error_message=str(e) if e else "Unknown"
            )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": "error",
                    "error": {
                        "code": "SESSION_NOT_FOUND",
                        "message": str(e) if e else "Session not found",
                        "details": None
                    }
                }
            )
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error in routing",
                record_id=record_id,
                session_id=session_id or "none",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error"
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "error": {
                        "code": "ROUTING_ERROR",
                        "message": "Error during request routing",
                        "details": None
                    }
                }
            )
        
        # Validate routing result
        if not routing_result or not isinstance(routing_result, dict):
            safe_log(
                logger,
                logging.ERROR,
                "Invalid routing result",
                record_id=record_id,
                session_id=session_id or "none"
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Invalid routing result",
                        "details": None
                    }
                }
            )
        
        # Ensure status is present
        if "status" not in routing_result:
            routing_result["status"] = "unknown"
        
        # Log success
        safe_log(
            logger,
            logging.INFO,
            "Request processed successfully",
            record_id=record_id,
            session_id=session_id or "none",
            routing_status=routing_result.get("status", "unknown")
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "data": routing_result
            }
        )
        
    except Exception as e:
        # Catch-all for unexpected errors
        safe_log(
            logger,
            logging.ERROR,
            "Unexpected error in receive_request",
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


@router.post(
    "/api/mcp/request-salesforce-data",
    status_code=status.HTTP_200_OK,
    summary="Request Salesforce data (internal endpoint)",
    description="Internal endpoint for fetching Salesforce data. Called during initialization flow."
)
async def request_salesforce_data(
    request: RequestSalesforceDataSchema,
    http_request: Request
) -> JSONResponse:
    """
    Request Salesforce data from mock service.
    
    Internal endpoint called during initialization flow.
    """
    record_id = None
    
    try:
        # Validate input
        if not request or not hasattr(request, "record_id"):
            safe_log(
                logger,
                logging.ERROR,
                "Invalid request object",
                endpoint="/api/mcp/request-salesforce-data"
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
        
        record_id = request.record_id if request.record_id else None
        
        # Validate record_id
        if not record_id or not record_id.strip():
            safe_log(
                logger,
                logging.WARNING,
                "Empty record_id provided",
                endpoint="/api/mcp/request-salesforce-data"
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
        
        record_id = record_id.strip()
        http_request.state.record_id = record_id
        
        # Log request
        safe_log(
            logger,
            logging.INFO,
            "Requesting Salesforce data",
            record_id=record_id,
            endpoint="/api/mcp/request-salesforce-data"
        )
        
        # Fetch Salesforce data
        try:
            salesforce_data = await fetch_salesforce_data(record_id)
        except SalesforceClientError as e:
            error_message = str(e) if e else "Unknown error"
            safe_log(
                logger,
                logging.ERROR,
                "Salesforce client error",
                record_id=record_id,
                error_type="SalesforceClientError",
                error_message=error_message
            )
            
            # Determine status code based on error
            if "not found" in error_message.lower():
                status_code = status.HTTP_404_NOT_FOUND
                error_code = "RECORD_NOT_FOUND"
            elif "timeout" in error_message.lower():
                status_code = status.HTTP_504_GATEWAY_TIMEOUT
                error_code = "TIMEOUT"
            elif "connect" in error_message.lower():
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                error_code = "SERVICE_UNAVAILABLE"
            else:
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                error_code = "SALESFORCE_ERROR"
            
            return JSONResponse(
                status_code=status_code,
                content={
                    "status": "error",
                    "error": {
                        "code": error_code,
                        "message": error_message,
                        "details": None
                    }
                }
            )
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error fetching Salesforce data",
                record_id=record_id,
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error"
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Failed to fetch Salesforce data",
                        "details": None
                    }
                }
            )
        
        # Validate salesforce_data
        if not salesforce_data:
            safe_log(
                logger,
                logging.ERROR,
                "Salesforce data is None or empty",
                record_id=record_id
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Invalid Salesforce data received",
                        "details": None
                    }
                }
            )
        
        # Build response data with defensive checks
        response_data = {
            "record_id": salesforce_data.record_id if salesforce_data.record_id else record_id,
            "record_type": salesforce_data.record_type if salesforce_data.record_type else "Claim",
            "documents": [
                {
                    "document_id": doc.document_id if doc.document_id else f"doc_{i}",
                    "name": doc.name if doc.name else "unknown.pdf",
                    "url": doc.url if doc.url else "",
                    "type": doc.type if doc.type else "application/pdf",
                    "indexed": doc.indexed if doc.indexed is not None else True
                }
                for i, doc in enumerate(salesforce_data.documents or [], 1)
            ],
            "fields_to_fill": [
                {
                    "field_name": field.field_name if field.field_name else f"field_{i}",
                    "field_type": field.field_type if field.field_type else "text",
                    "value": field.value if field.value is not None else None,
                    "required": field.required if field.required is not None else True,
                    "label": field.label if field.label else field.field_name if field.field_name else f"Field {i}"
                }
                for i, field in enumerate(salesforce_data.fields_to_fill or [], 1)
            ]
        }
        
        # Log success
        safe_log(
            logger,
            logging.INFO,
            "Salesforce data retrieved successfully",
            record_id=record_id,
            documents_count=len(response_data.get("documents", [])),
            fields_count=len(response_data.get("fields_to_fill", []))
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
            "Unexpected error in request_salesforce_data",
            record_id=record_id or "unknown",
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

