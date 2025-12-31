"""Test endpoints for setting up test data"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from typing import Any, Dict, List, Optional
import logging
from pydantic import BaseModel
from pathlib import Path

from app.models.schemas import DocumentSchema, SalesforceFormFieldSchema
from app.data.mock_records import MOCK_RECORDS
from app.core.logging import get_logger, safe_log

logger = get_logger(__name__)

router = APIRouter()

# In-memory storage for test data (temporary, cleared on restart)
_test_data_storage: Dict[str, Dict[str, Any]] = {}


class SetupTestDataRequest(BaseModel):
    """Request schema for setting up test data"""
    record_id: str
    documents: List[Dict[str, Any]]  # List of document dicts with url, name, type, etc.
    fields: List[Dict[str, Any]]  # List of field dicts in SalesforceFormFieldSchema format


@router.post(
    "/api/test/setup-test-data",
    status_code=status.HTTP_200_OK,
    summary="Setup test data for a record",
    description="Stores test documents and fields temporarily for a given record_id"
)
async def setup_test_data(request: SetupTestDataRequest) -> JSONResponse:
    """
    Setup test data for a record_id.
    
    This endpoint stores documents and fields temporarily in memory.
    When get_record_data is called with this record_id, it will return this test data.
    """
    try:
        record_id = request.record_id.strip()
        
        safe_log(
            logger,
            logging.INFO,
            "Setting up test data",
            record_id=record_id,
            documents_count=len(request.documents),
            fields_count=len(request.fields)
        )
        
        # Convert documents to DocumentSchema format
        documents = []
        for i, doc_dict in enumerate(request.documents):
            documents.append(DocumentSchema(
                document_id=doc_dict.get("document_id") or doc_dict.get("id") or f"doc_{i+1}",
                name=doc_dict.get("name") or f"document_{i+1}.pdf",
                url=doc_dict.get("url") or "",
                type=doc_dict.get("type") or "application/pdf",
                indexed=doc_dict.get("indexed", True)
            ))
        
        # Convert fields to SalesforceFormFieldSchema format
        fields = []
        for field_dict in request.fields:
            fields.append(SalesforceFormFieldSchema(
                label=field_dict.get("label", ""),
                apiName=field_dict.get("apiName"),
                type=field_dict.get("type", "text"),
                required=field_dict.get("required", False),
                possibleValues=field_dict.get("possibleValues", []),
                defaultValue=field_dict.get("defaultValue")
            ))
        
        # Store test data
        from app.models.schemas import GetRecordDataResponse
        test_record = GetRecordDataResponse(
            record_id=record_id,
            record_type="Claim",
            documents=documents,
            fields=fields
        )
        
        # Store in temporary storage
        _test_data_storage[record_id] = {
            "record": test_record,
            "documents": documents,
            "fields": fields
        }
        
        # Also add to MOCK_RECORDS for compatibility
        MOCK_RECORDS[record_id] = test_record
        
        safe_log(
            logger,
            logging.INFO,
            "Test data stored successfully",
            record_id=record_id,
            stored_records_count=len(_test_data_storage)
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "message": f"Test data stored for record_id: {record_id}",
                "record_id": record_id,
                "documents_count": len(documents),
                "fields_count": len(fields)
            }
        )
        
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Error setting up test data",
            record_id=request.record_id if request else "unknown",
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": f"Failed to setup test data: {str(e) if e else 'Unknown error'}",
                    "details": None
                }
            }
        )


@router.delete(
    "/api/test/clear-test-data/{record_id}",
    status_code=status.HTTP_200_OK,
    summary="Clear test data for a record",
    description="Removes test data for a given record_id"
)
async def clear_test_data(record_id: str) -> JSONResponse:
    """Clear test data for a record_id"""
    try:
        record_id = record_id.strip()
        
        if record_id in _test_data_storage:
            del _test_data_storage[record_id]
            if record_id in MOCK_RECORDS:
                del MOCK_RECORDS[record_id]
            
            safe_log(
                logger,
                logging.INFO,
                "Test data cleared",
                record_id=record_id
            )
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "success",
                    "message": f"Test data cleared for record_id: {record_id}"
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"No test data found for record_id: {record_id}"
                    }
                }
            )
            
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Error clearing test data",
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
                    "message": f"Failed to clear test data: {str(e) if e else 'Unknown error'}"
                }
            }
        )


@router.get(
    "/documents/{filename}",
    summary="Serve test data files",
    description="Serves files from the test-data/documents directory"
)
async def serve_file(filename: str):
    """Serve a file from the test-data/documents directory"""
    try:
        # Get the test-data base path
        from app.data.file_loader import get_test_data_base_path
        test_data_path = get_test_data_base_path()
        documents_dir = test_data_path / "documents"
        file_path = documents_dir / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        safe_log(
            logger,
            logging.INFO,
            "Serving file",
            filename=filename,
            file_path=str(file_path)
        )
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/pdf"  # Default to PDF, but could detect
        )
        
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Error serving file",
            filename=filename,
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error"
        )
        raise HTTPException(status_code=500, detail="Internal server error")

