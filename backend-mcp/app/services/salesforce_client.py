"""Salesforce client for fetching data from mock Salesforce"""
import httpx
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger, safe_log
from app.core.exceptions import SalesforceClientError
from app.models.schemas import (
    SalesforceDataResponseSchema, 
    DocumentResponseSchema, 
    FieldToFillResponseSchema,
    SalesforceFormFieldSchema,
    SalesforceFormFieldsResponseSchema
)

logger = get_logger(__name__)


async def fetch_salesforce_data(record_id: str) -> SalesforceDataResponseSchema:
    """
    Fetch Salesforce data from mock service.
    
    Implements robust error handling and defensive logging.
    """
    if not record_id or not record_id.strip():
        safe_log(
            logger,
            logging.ERROR,
            "Empty record_id provided to fetch_salesforce_data",
            record_id=record_id or "none"
        )
        raise ValueError("record_id cannot be None or empty")
    
    record_id = record_id.strip()
    start_time = datetime.utcnow()
    
    try:
       
        # Validate URL is configured
        if not settings.mock_salesforce_url or not settings.mock_salesforce_url.strip():
            safe_log(
                logger,
                logging.ERROR,
                "Mock Salesforce URL not configured",
                record_id=record_id
            )
            raise SalesforceClientError("Mock Salesforce URL not configured")
        
        url = f"{settings.mock_salesforce_url.strip().rstrip('/')}/mock/salesforce/get-record-data"
        timeout = settings.salesforce_request_timeout
        
        
        
        safe_log(
            logger,
            logging.INFO,
            "Fetching Salesforce data",
            record_id=record_id,
            url=url,
            timeout=timeout
        )
        
        # Make HTTP request with timeout
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    url,
                    json={"record_id": record_id},
                    headers={"Content-Type": "application/json"}
                )
            except httpx.TimeoutException as e:
                # Timeout error
                duration = (datetime.utcnow() - start_time).total_seconds()
                safe_log(
                    logger,
                    logging.ERROR,
                    "Timeout fetching Salesforce data",
                    record_id=record_id,
                    timeout=timeout,
                    duration=duration,
                    error_type="TimeoutException"
                )
                raise SalesforceClientError(f"Request timeout after {timeout}s") from e
            except httpx.ConnectError as e:
                # Connection error
                duration = (datetime.utcnow() - start_time).total_seconds()
               
                safe_log(
                    logger,
                    logging.ERROR,
                    "Connection error fetching Salesforce data",
                    record_id=record_id,
                    url=url,
                    duration=duration,
                    error_type="ConnectError"
                )
                raise SalesforceClientError(f"Failed to connect to mock Salesforce service") from e
            except httpx.HTTPStatusError as e:
                # HTTP error (404, 500, etc.)
                duration = (datetime.utcnow() - start_time).total_seconds()
                status_code = e.response.status_code if e.response else 0
                safe_log(
                    logger,
                    logging.ERROR,
                    "HTTP error fetching Salesforce data",
                    record_id=record_id,
                    status_code=status_code,
                    duration=duration,
                    error_type="HTTPStatusError"
                )
                if status_code == 404:
                    raise SalesforceClientError(f"Record {record_id} not found") from e
                else:
                    raise SalesforceClientError(f"HTTP error {status_code} from mock Salesforce") from e
            except Exception as e:
                # Other HTTP errors
                duration = (datetime.utcnow() - start_time).total_seconds()
                safe_log(
                    logger,
                    logging.ERROR,
                    "Unexpected HTTP error",
                    record_id=record_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown",
                    duration=duration
                )
                raise SalesforceClientError(f"Unexpected error: {str(e)}") from e
        
        # Validate response status
        if response.status_code != 200:
            duration = (datetime.utcnow() - start_time).total_seconds()
            safe_log(
                logger,
                logging.ERROR,
                "Non-200 status code from mock Salesforce",
                record_id=record_id,
                status_code=response.status_code,
                duration=duration
            )
            raise SalesforceClientError(f"Received status {response.status_code} from mock Salesforce")
        
        # Parse and validate response JSON
        try:
            response_data = response.json()
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            safe_log(
                logger,
                logging.ERROR,
                "Failed to parse JSON response",
                record_id=record_id,
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown",
                duration=duration
            )
            raise SalesforceClientError("Invalid JSON response from mock Salesforce") from e
        
        # Validate response structure
        if not response_data or not isinstance(response_data, dict):
            duration = (datetime.utcnow() - start_time).total_seconds()
            safe_log(
                logger,
                logging.ERROR,
                "Invalid response structure",
                record_id=record_id,
                response_type=type(response_data).__name__,
                duration=duration
            )
            raise SalesforceClientError("Invalid response structure from mock Salesforce")
        
        # Extract data from response
        data = response_data.get("data")
        if not data or not isinstance(data, dict):
            duration = (datetime.utcnow() - start_time).total_seconds()
            safe_log(
                logger,
                logging.ERROR,
                "Missing or invalid data in response",
                record_id=record_id,
                has_data="data" in response_data,
                duration=duration
            )
            raise SalesforceClientError("Missing data in response from mock Salesforce")
        
        # Validate required fields
        if "record_id" not in data or not data["record_id"]:
            safe_log(
                logger,
                logging.ERROR,
                "Missing record_id in response data",
                record_id=record_id
            )
            raise SalesforceClientError("Missing record_id in response data")
        
        # Build response schema with defensive checks
        documents = []
        if "documents" in data and isinstance(data["documents"], list):
            for i, doc in enumerate(data["documents"], 1):
                if not isinstance(doc, dict):
                    continue
                documents.append(DocumentResponseSchema(
                    document_id=doc.get("document_id") or f"doc_{i}",
                    name=doc.get("name") or "unknown.pdf",
                    url=doc.get("url") or "",
                    type=doc.get("type") or "application/pdf",
                    indexed=doc.get("indexed") if doc.get("indexed") is not None else True
                ))
        
        fields_to_fill = []
        
        # Support both old format (fields_to_fill) and new format (fields)
        if "fields" in data and isinstance(data["fields"], list):
            # New format: {"fields": [{"label": "...", "apiName": "...", ...}]}
            safe_log(
                logger,
                logging.INFO,
                "Detected new Salesforce format (fields)",
                record_id=record_id,
                fields_count=len(data["fields"])
            )
            try:
                # Parse as SalesforceFormFieldsResponseSchema
                form_fields_response = SalesforceFormFieldsResponseSchema(fields=data["fields"])
                
                safe_log(
                    logger,
                    logging.INFO,
                    "Parsing new format fields",
                    record_id=record_id,
                    fields_count=len(form_fields_response.fields)
                )
                
                # Convert each field
                for i, field in enumerate(form_fields_response.fields, 1):
                    try:
                        # Log field details before conversion
                        field_label = field.label if hasattr(field, 'label') else 'unknown'
                        field_api_name = field.apiName if hasattr(field, 'apiName') else None
                        
                        safe_log(
                            logger,
                            logging.DEBUG,
                            "Converting Salesforce form field",
                            record_id=record_id,
                            field_index=i,
                            field_label=field_label,
                            field_api_name=field_api_name,
                            field_type=field.type if hasattr(field, 'type') else 'unknown'
                        )
                        
                        converted_field = FieldToFillResponseSchema.from_salesforce_form_field(field)
                        fields_to_fill.append(converted_field)
                        
                        safe_log(
                            logger,
                            logging.DEBUG,
                            "Field converted successfully",
                            record_id=record_id,
                            field_index=i,
                            converted_field_name=converted_field.field_name,
                            converted_field_type=converted_field.field_type
                        )
                    except Exception as e:
                        safe_log(
                            logger,
                            logging.WARNING,
                            "Failed to convert Salesforce form field",
                            record_id=record_id,
                            field_index=i,
                            field_label=field.label if hasattr(field, 'label') else 'unknown',
                            field_api_name=field.apiName if hasattr(field, 'apiName') else None,
                            error_type=type(e).__name__,
                            error_message=str(e) if e else "Unknown"
                        )
                        continue
                
                safe_log(
                    logger,
                    logging.INFO,
                    "Fields conversion completed",
                    record_id=record_id,
                    original_fields_count=len(form_fields_response.fields),
                    converted_fields_count=len(fields_to_fill)
                )
            except Exception as e:
                safe_log(
                    logger,
                    logging.WARNING,
                    "Failed to parse new format, falling back to old format",
                    record_id=record_id,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                # Fall through to old format handling
        
        if "fields_to_fill" in data and isinstance(data["fields_to_fill"], list):
            # Old format: {"fields_to_fill": [{"field_name": "...", ...}]}
            safe_log(
                logger,
                logging.INFO,
                "Using old Salesforce format (fields_to_fill)",
                record_id=record_id,
                fields_count=len(data["fields_to_fill"])
            )
            for i, field in enumerate(data["fields_to_fill"], 1):
                if not isinstance(field, dict):
                    continue
                fields_to_fill.append(FieldToFillResponseSchema(
                    field_name=field.get("field_name") or f"field_{i}",
                    field_type=field.get("field_type") or "text",
                    value=field.get("value") if field.get("value") is not None else None,
                    required=field.get("required") if field.get("required") is not None else True,
                    label=field.get("label") or field.get("field_name") or f"Field {i}",
                    metadata=field.get("metadata", {})
                ))
        
        salesforce_data = SalesforceDataResponseSchema(
            record_id=data.get("record_id") or record_id,
            record_type=data.get("record_type") or "Claim",
            documents=documents,
            fields_to_fill=fields_to_fill
        )
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        safe_log(
            logger,
            logging.INFO,
            "Salesforce data fetched successfully",
            record_id=record_id,
            documents_count=len(documents),
            fields_count=len(fields_to_fill),
            duration=duration
        )
        
        return salesforce_data
        
    except SalesforceClientError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        duration = (datetime.utcnow() - start_time).total_seconds()
        safe_log(
            logger,
            logging.ERROR,
            "Unexpected error in fetch_salesforce_data",
            record_id=record_id,
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error",
            duration=duration
        )
        raise SalesforceClientError(f"Unexpected error: {str(e)}") from e

