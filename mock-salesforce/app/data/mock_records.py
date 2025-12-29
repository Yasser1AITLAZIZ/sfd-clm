"""Mock datasets for different record IDs - now loads dynamically from test-data directories"""
from typing import Dict, Any
from app.models.schemas import (
    GetRecordDataResponse, 
    DocumentSchema, 
    FieldToFillSchema,
    SalesforceFormFieldSchema
)
from app.data.file_loader import (
    load_documents_for_record,
    load_fields_for_record,
    get_record_type_from_config
)
from app.core.logging import get_logger, safe_log
import logging

logger = get_logger(__name__)

# Legacy: Keep MOCK_RECORDS for backward compatibility if needed
# But it's now empty as we load dynamically from test-data directories
MOCK_RECORDS: Dict[str, GetRecordDataResponse] = {}


def get_mock_record(record_id: str) -> GetRecordDataResponse:
    """
    Get mock record data by record_id.
    Now loads dynamically from test-data/documents/ and test-data/fields/.
    
    Args:
        record_id: Salesforce record ID
    
    Returns:
        GetRecordDataResponse with documents and fields loaded from files
    
    Raises:
        ValueError: If record_id is empty
        KeyError: If record_id is not found (when no files exist for it)
    """
    if not record_id:
        raise ValueError("record_id cannot be None or empty")
    
    record_id = record_id.strip()
    
    safe_log(
        logger,
        logging.INFO,
        "Loading mock record data dynamically",
        record_id=record_id
    )
    
    # Load documents and fields dynamically
    documents = load_documents_for_record(record_id)
    fields = load_fields_for_record(record_id)
    record_type = get_record_type_from_config(record_id)
    
    # Check if we have any data
    if not documents and not fields:
        # Check if it exists in legacy MOCK_RECORDS as fallback
        if record_id in MOCK_RECORDS:
            safe_log(
                logger,
                logging.INFO,
                "Using legacy mock data as fallback",
                record_id=record_id
            )
            return MOCK_RECORDS[record_id]
        
        # No data found at all
        safe_log(
            logger,
            logging.WARNING,
            "No data found for record_id (no documents or fields)",
            record_id=record_id
        )
        raise KeyError(f"Record {record_id} not found in mock data")
    
    # Build response dynamically
    response = GetRecordDataResponse(
        record_id=record_id,
        record_type=record_type,
        documents=documents,
        fields=fields,
        fields_to_fill=[]  # Empty for new format
    )
    
    safe_log(
        logger,
        logging.INFO,
        "Mock record data loaded successfully",
        record_id=record_id,
        documents_count=len(documents),
        fields_count=len(fields),
        record_type=record_type
    )
    
    return response

