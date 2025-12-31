"""File loader for dynamically loading documents and fields from test-data directories"""
from pathlib import Path
from typing import List, Optional
import json
import mimetypes
import logging

from app.models.schemas import DocumentSchema, SalesforceFormFieldSchema
from app.core.logging import get_logger, safe_log
from app.core.config import settings

logger = get_logger(__name__)


def get_test_data_base_path() -> Path:
    """
    Get the base path to test-data directory.
    
    In Docker: test-data is mounted at /app/test-data
    In local dev: test-data is at project root level, relative to mock-salesforce
    """
    # First, check if we're in Docker with test-data mounted at /app/test-data
    docker_test_data = Path("/app/test-data")
    if docker_test_data.exists():
        return docker_test_data
    
    # Otherwise, calculate from file location (local development)
    # Get the directory where this file is located (mock-salesforce/app/data)
    current_file = Path(__file__)
    # Go up: app/data -> app -> mock-salesforce -> project root
    project_root = current_file.parent.parent.parent.parent
    test_data_path = project_root / "test-data"
    return test_data_path


def detect_mime_type(filename: str) -> str:
    """
    Detect MIME type from filename extension.
    Returns default 'application/pdf' if detection fails.
    """
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        return mime_type
    
    # Fallback based on extension
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    mime_map = {
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'zip': 'application/zip',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }
    return mime_map.get(ext, 'application/pdf')


def load_documents_for_record(
    record_id: str,
    base_path: Optional[Path] = None,
    file_server_url: Optional[str] = None
) -> List[DocumentSchema]:
    """
    Load documents for a given record_id from test-data/documents/.
    
    Looks for files matching pattern: {record_id}_*
    
    Args:
        record_id: Salesforce record ID
        base_path: Base path to test-data directory (defaults to auto-detection)
        file_server_url: URL of file server (defaults to settings.FILE_SERVER_URL)
    
    Returns:
        List of DocumentSchema objects with URLs pointing to file server
    """
    if base_path is None:
        base_path = get_test_data_base_path()
    
    if file_server_url is None:
        file_server_url = getattr(settings, 'file_server_url', 'http://localhost:8003')
    
    documents_dir = base_path / "documents"
    documents = []
    
    if not documents_dir.exists():
        safe_log(
            logger,
            logging.WARNING,
            "Documents directory not found",
            record_id=record_id,
            documents_dir=str(documents_dir)
        )
        return documents
    
    # Pattern: {record_id}_*
    prefix = f"{record_id}_"
    
    try:
        # Find all files starting with the prefix
        matching_files = list(documents_dir.glob(f"{prefix}*"))
        
        if not matching_files:
            safe_log(
                logger,
                logging.WARNING,
                "No documents found for record_id",
                record_id=record_id,
                pattern=f"{prefix}*",
                documents_dir=str(documents_dir)
            )
            return documents
        
        # Sort files for consistent ordering
        matching_files.sort()
        
        for idx, file_path in enumerate(matching_files, 1):
            if not file_path.is_file():
                continue
            
            filename = file_path.name
            mime_type = detect_mime_type(filename)
            
            # Generate URL pointing to file server
            url = f"{file_server_url}/documents/{filename}"
            
            # Create document schema
            doc = DocumentSchema(
                document_id=f"doc_{idx}",
                name=filename,
                url=url,
                type=mime_type,
                indexed=True
            )
            documents.append(doc)
        
        safe_log(
            logger,
            logging.INFO,
            "Documents loaded for record",
            record_id=record_id,
            documents_count=len(documents),
            documents_dir=str(documents_dir)
        )
        
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Error loading documents for record",
            record_id=record_id,
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error"
        )
    
    return documents


def load_fields_for_record(
    record_id: str,
    base_path: Optional[Path] = None
) -> List[SalesforceFormFieldSchema]:
    """
    Load fields for a given record_id from test-data/fields/{record_id}_fields.json.
    Falls back to {record_id}.json if _fields.json doesn't exist.
    
    Args:
        record_id: Salesforce record ID
        base_path: Base path to test-data directory (defaults to auto-detection)
    
    Returns:
        List of SalesforceFormFieldSchema objects
    """
    if base_path is None:
        base_path = get_test_data_base_path()
    
    fields_dir = base_path / "fields"
    # Try {record_id}_fields.json first (actual naming convention)
    fields_file = fields_dir / f"{record_id}_fields.json"
    # Fallback to {record_id}.json for backward compatibility
    if not fields_file.exists():
        fields_file = fields_dir / f"{record_id}.json"
    
    fields = []
    
    if not fields_file.exists():
        safe_log(
            logger,
            logging.WARNING,
            "Fields file not found for record_id",
            record_id=record_id,
            fields_file=str(fields_file),
            tried_patterns=[f"{record_id}_fields.json", f"{record_id}.json"]
        )
        return fields
    
    try:
        with open(fields_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract fields array from JSON
        fields_data = data.get("fields", [])
        
        if not fields_data:
            safe_log(
                logger,
                logging.WARNING,
                "Fields array is empty in JSON file",
                record_id=record_id,
                fields_file=str(fields_file)
            )
            return fields
        
        # Convert each field dict to SalesforceFormFieldSchema
        for field_data in fields_data:
            try:
                field = SalesforceFormFieldSchema(
                    label=field_data.get("label", ""),
                    apiName=field_data.get("apiName"),
                    type=field_data.get("type", "text"),
                    required=field_data.get("required", False),
                    possibleValues=field_data.get("possibleValues", []),
                    defaultValue=field_data.get("defaultValue")
                )
                fields.append(field)
            except Exception as e:
                safe_log(
                    logger,
                    logging.WARNING,
                    "Error parsing field from JSON",
                    record_id=record_id,
                    field_data=field_data,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown error"
                )
                continue
        
        safe_log(
            logger,
            logging.INFO,
            "Fields loaded for record",
            record_id=record_id,
            fields_count=len(fields),
            fields_file=str(fields_file)
        )
        
    except json.JSONDecodeError as e:
        safe_log(
            logger,
            logging.ERROR,
            "Invalid JSON in fields file",
            record_id=record_id,
            fields_file=str(fields_file),
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error"
        )
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Error loading fields for record",
            record_id=record_id,
            fields_file=str(fields_file),
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error"
        )
    
    return fields


def get_record_type_from_config(record_id: str) -> str:
    """
    Get record type for a given record_id.
    Currently returns default "Claim", but can be extended to read from config.
    
    Args:
        record_id: Salesforce record ID
    
    Returns:
        Record type string (default: "Claim")
    """
    # Default to "Claim" for now
    # Can be extended to read from a config file if needed
    return "Claim"

