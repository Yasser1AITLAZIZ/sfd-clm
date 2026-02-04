"""Document upload endpoints"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import os
import uuid
from pathlib import Path
from datetime import datetime

from app.core.logging import get_logger, safe_log
from app.core.config import settings

logger = get_logger(__name__)

router = APIRouter()

# Create uploads directory if it doesn't exist
UPLOADS_DIR = Path(settings.uploads_dir if hasattr(settings, 'uploads_dir') else 'uploads')
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "/api/documents/upload",
    status_code=status.HTTP_200_OK,
    summary="Upload document",
    description="Upload a document file (PDF, image) for a given record_id"
)
async def upload_document(
    file: UploadFile = File(...),
    record_id: str = Form(...)
) -> JSONResponse:
    """
    Upload a document file.
    
    Args:
        file: The file to upload (PDF, PNG, JPG)
        record_id: Salesforce record ID
        
    Returns:
        JSON response with document_id and url
    """
    try:
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
        
        # Validate file type
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
        if file.content_type not in allowed_types:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_FILE_TYPE",
                        "message": f"Invalid file type. Allowed types: {', '.join(allowed_types)}",
                        "details": None
                    }
                }
            )
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        if len(file_content) > max_size:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "FILE_TOO_LARGE",
                        "message": f"File size exceeds {max_size / (1024 * 1024)}MB limit",
                        "details": None
                    }
                }
            )
        
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Determine file extension
        file_extension = Path(file.filename).suffix if file.filename else '.pdf'
        if not file_extension:
            file_extension = '.pdf' if file.content_type == 'application/pdf' else '.jpg'
        
        # Get original filename without extension
        original_filename = Path(file.filename).stem if file.filename else 'document'
        # Clean filename (remove special characters, keep only alphanumeric, dash, underscore)
        import re
        original_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', original_filename)
        
        # Create filename with format: {record_id}_{original_filename}{extension}
        filename = f"{record_id}_{original_filename}{file_extension}"
        file_path = UPLOADS_DIR / filename
        
        # Save file to uploads directory
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Also copy to test-data/documents/ for Mock Salesforce to find it
        # In Docker, test-data is mounted at /app/test-data
        # In local dev, calculate from project root
        docker_test_data = Path("/app/test-data")
        if docker_test_data.exists():
            test_data_documents_dir = docker_test_data / "documents"
        else:
            # Local development: calculate from file location
            current_file = Path(__file__)
            # Go up: app/api/v1/endpoints -> app/api/v1 -> app/api -> app -> backend-mcp -> project root
            project_root = current_file.parent.parent.parent.parent.parent.parent
            test_data_documents_dir = project_root / "test-data" / "documents"
        
        test_data_documents_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy file to test-data/documents/ with the same filename
        test_data_file_path = test_data_documents_dir / filename
        with open(test_data_file_path, 'wb') as f:
            f.write(file_content)
        
        safe_log(
            logger,
            logging.INFO,
            "Document copied to test-data/documents",
            record_id=record_id,
            filename=filename,
            test_data_path=str(test_data_file_path)
        )
        
        # Generate URL (use absolute URL for backend-mcp service)
        # In Docker, this will be accessible via the backend-mcp service
        file_url = f"http://backend-mcp:8000/uploads/{filename}"
        # For local development, use localhost
        if os.getenv("ENVIRONMENT", "production") == "development":
            file_url = f"http://localhost:8000/uploads/{filename}"
        
        safe_log(
            logger,
            logging.INFO,
            "Document uploaded successfully",
            document_id=document_id,
            record_id=record_id,
            filename=filename,
            file_size=len(file_content),
            content_type=file.content_type
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "data": {
                    "document_id": document_id,
                    "url": file_url,
                    "filename": filename,
                    "size": len(file_content),
                    "content_type": file.content_type
                }
            }
        )
        
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Error uploading document",
            record_id=record_id if 'record_id' in locals() else "unknown",
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error": {
                    "code": "UPLOAD_ERROR",
                    "message": "Failed to upload document",
                    "details": str(e) if e else None
                }
            }
        )

