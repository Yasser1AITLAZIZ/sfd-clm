"""Salesforce mock endpoints"""
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict
import logging

from app.models.schemas import GetRecordDataRequest, GetRecordDataResponse
from app.data.mock_records import get_mock_record
from app.core.exceptions import RecordNotFoundError, InvalidRecordIdError
from app.core.logging import get_logger, safe_log
from app.core.config import settings

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/mock/salesforce/get-record-data",
    response_model=GetRecordDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Get mock Salesforce record data",
    description="Returns mock documents and fields to fill for a given record_id"
)
async def get_record_data(request: GetRecordDataRequest) -> JSONResponse:
    """
    Get mock record data for a given record_id.
    
    Implements robust error handling and defensive logging.
    """
    record_id = None
    try:
        # Validate input
        if not request or not hasattr(request, "record_id"):
            safe_log(
                logger,
                logging.ERROR,
                "Invalid request object",
                endpoint="/mock/salesforce/get-record-data"
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
        
        # Validate record_id is not None/undefined
        if record_id is None or not record_id.strip():
            safe_log(
                logger,
                logging.WARNING,
                "Empty record_id provided",
                endpoint="/mock/salesforce/get-record-data"
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
        
        # Log request
        safe_log(
            logger,
            logging.INFO,
            "Request received for record data",
            record_id=record_id,
            endpoint="/mock/salesforce/get-record-data"
        )
        
        # Get mock data
        try:
            mock_data = get_mock_record(record_id)
        except KeyError as e:
            # Record not found
            safe_log(
                logger,
                logging.WARNING,
                "Record not found in mock data",
                record_id=record_id,
                error_type="KeyError",
                error_message=str(e) if e else "Unknown"
            )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": "error",
                    "error": {
                        "code": "RECORD_NOT_FOUND",
                        "message": f"Record {record_id} not found in mock data",
                        "details": None
                    }
                }
            )
        except ValueError as e:
            # Invalid record_id format
            safe_log(
                logger,
                logging.WARNING,
                "Invalid record_id format",
                record_id=record_id or "none",
                error_type="ValueError",
                error_message=str(e) if e else "Unknown"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_RECORD_ID",
                        "message": str(e) if e else "Invalid record_id format",
                        "details": None
                    }
                }
            )
        
        # Validate mock_data is complete
        if not mock_data:
            safe_log(
                logger,
                logging.ERROR,
                "Mock data is None or empty",
                record_id=record_id
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Failed to retrieve mock data",
                        "details": None
                    }
                }
            )
        
        # Use new format with "fields" instead of "fields_to_fill"
        # Convert to dict using new format method
        if mock_data.fields:
            # New format available
            response_data = mock_data.to_dict_new_format()
            fields_count = len(mock_data.fields)
        elif mock_data.fields_to_fill:
            # Fallback to old format if new format not available
            response_data = mock_data.to_dict_old_format()
            fields_count = len(mock_data.fields_to_fill)
        else:
            # No fields at all
            response_data = {
                "record_id": mock_data.record_id if mock_data.record_id else record_id,
                "record_type": mock_data.record_type if mock_data.record_type else "Claim",
                "documents": [
                    {
                        "document_id": doc.document_id if doc.document_id else f"doc_{i}",
                        "name": doc.name if doc.name else "unknown.pdf",
                        "url": doc.url if doc.url else "",
                        "type": doc.type if doc.type else "application/pdf",
                        "indexed": doc.indexed if doc.indexed is not None else True
                    }
                    for i, doc in enumerate(mock_data.documents or [], 1)
                ],
                "fields": []
            }
            fields_count = 0
        
        # Log success
        safe_log(
            logger,
            logging.INFO,
            "Record data retrieved successfully",
            record_id=record_id,
            documents_count=len(response_data.get("documents", [])),
            fields_count=fields_count,
            format="new" if "fields" in response_data else "old"
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
            "Unexpected error in get_record_data",
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


@router.post(
    "/mock/salesforce/add-document",
    status_code=status.HTTP_200_OK,
    summary="Add document to record",
    description="Add a document to a record by copying it to test-data/documents/"
)
async def add_document_to_record(request_obj: Request) -> JSONResponse:
    """
    Add a document to a record by downloading it from URL and saving to test-data/documents/.
    
    Request body:
        record_id: Salesforce record ID
        document_url: URL of the document to download
        document_name: Name of the document (will be prefixed with record_id)
        document_type: MIME type of the document (optional, defaults to application/pdf)
        
    Returns:
        JSON response with success status
    """
    try:
        import httpx
        from pathlib import Path
        from app.data.file_loader import get_test_data_base_path
        
        # Parse request body
        try:
            request_data = await request_obj.json()
        except Exception as json_error:
            safe_log(
                logger,
                logging.ERROR,
                "Failed to parse request body as JSON",
                error_type=type(json_error).__name__,
                error_message=str(json_error)
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_JSON",
                        "message": f"Failed to parse request body: {str(json_error)}",
                        "details": None
                    }
                }
            )
        
        # Extract parameters from request body
        record_id = request_data.get("record_id")
        document_url = request_data.get("document_url")
        document_name = request_data.get("document_name")
        document_type = request_data.get("document_type", "application/pdf")
        
        safe_log(
            logger,
            logging.INFO,
            "Received add-document request",
            record_id=record_id,
            document_name=document_name,
            document_url=document_url[:100] if document_url else None,  # Log first 100 chars
            document_type=document_type
        )
        
        # Validate record_id
        if not record_id or not record_id.strip():
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
        
        # Validate document_url and document_name
        if not document_url or not document_url.strip():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_DOCUMENT_URL",
                        "message": "document_url cannot be empty",
                        "details": None
                    }
                }
            )
        
        if not document_name or not document_name.strip():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_DOCUMENT_NAME",
                        "message": "document_name cannot be empty",
                        "details": None
                    }
                }
            )
        
        document_url = document_url.strip()
        document_name = document_name.strip()
        
        # Get test-data base path
        test_data_base = get_test_data_base_path()
        documents_dir = test_data_base / "documents"
        documents_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename with format: {record_id}_{document_name}
        # Clean document name (remove extension if present, we'll add it back)
        import re
        from pathlib import Path as PathLib
        doc_path = PathLib(document_name)
        clean_name = doc_path.stem  # Get name without extension
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', clean_name)
        extension = doc_path.suffix  # Get extension
        if not extension:
            # Determine extension from document_type
            if 'pdf' in document_type.lower():
                extension = '.pdf'
            elif 'jpeg' in document_type.lower() or 'jpg' in document_type.lower():
                extension = '.jpg'
            elif 'png' in document_type.lower():
                extension = '.png'
            else:
                extension = '.pdf'  # Default
        
        # IMPORTANT: backend-mcp already copies the file to test-data/documents/ with format:
        # {record_id}_{original_filename}{extension}
        # So we should first check if the file already exists there
        
        # Try to find existing file first (backend-mcp pattern: {record_id}_*)
        existing_files = list(documents_dir.glob(f"{record_id}_*"))
        file_content = None
        file_path = None
        filename = None
        
        if existing_files:
            # Use the most recent file (likely the one just uploaded)
            existing_file = max(existing_files, key=lambda p: p.stat().st_mtime)
            safe_log(
                logger,
                logging.INFO,
                "Found existing document in test-data (uploaded by backend-mcp), using it",
                record_id=record_id,
                existing_file=str(existing_file),
                file_size=existing_file.stat().st_size
            )
            with open(existing_file, 'rb') as f:
                file_content = f.read()
            filename = existing_file.name
            file_path = existing_file
        else:
            # File doesn't exist, try to create it from the document_name
            # This is a fallback in case backend-mcp didn't copy it
            filename = f"{record_id}_{clean_name}{extension}"
            file_path = documents_dir / filename
            
            # Try to download from URL as fallback
            normalized_url = document_url
            
            # Handle relative URLs
            if normalized_url.startswith("/uploads/"):
                # Try to construct full URL
                import os
                if os.getenv("ENVIRONMENT", "production") == "development":
                    normalized_url = f"http://localhost:8000{normalized_url}"
                else:
                    normalized_url = f"http://backend-mcp:8000{normalized_url}"
            elif normalized_url.startswith("http://localhost:8000") or normalized_url.startswith("http://127.0.0.1:8000"):
                # In Docker, replace localhost with service name
                import os
                if os.getenv("ENVIRONMENT", "production") != "development":
                    normalized_url = normalized_url.replace("http://localhost:8000", "http://backend-mcp:8000")
                    normalized_url = normalized_url.replace("http://127.0.0.1:8000", "http://backend-mcp:8000")
            
            try:
                safe_log(
                    logger,
                    logging.INFO,
                    "Downloading document from URL (fallback - file not found in test-data)",
                    record_id=record_id,
                    document_url=normalized_url,
                    original_url=document_url
                )
                
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    response = await client.get(normalized_url)
                    response.raise_for_status()
                    file_content = response.content
                
                # Save downloaded file
                with open(file_path, 'wb') as f:
                    f.write(file_content)
                
                safe_log(
                    logger,
                    logging.INFO,
                    "Document downloaded and saved successfully",
                    record_id=record_id,
                    document_url=normalized_url,
                    file_size=len(file_content),
                    file_path=str(file_path)
                )
            except httpx.HTTPError as http_error:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Failed to download document from URL",
                    record_id=record_id,
                    document_url=normalized_url,
                    original_url=document_url,
                    error_type=type(http_error).__name__,
                    error_message=str(http_error)
                )
                # If download fails, this is an error - we can't proceed
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to add document: File not found in test-data/documents/ and failed to download from URL. Error: {str(http_error)}"
                )
        
        safe_log(
            logger,
            logging.INFO,
            "Document added to record",
            record_id=record_id,
            filename=filename,
            document_url=document_url,
            file_size=len(file_content)
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "data": {
                    "record_id": record_id,
                    "filename": filename,
                    "file_path": str(file_path),
                    "size": len(file_content),
                    "document_type": document_type
                }
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        safe_log(
            logger,
            logging.ERROR,
            "Error adding document to record",
            record_id=record_id if 'record_id' in locals() else "unknown",
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error",
            traceback=error_traceback
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error": {
                    "code": "ADD_DOCUMENT_ERROR",
                    "message": f"Failed to add document to record: {str(e)}",
                    "details": error_traceback if settings.debug else None
                }
            }
        )