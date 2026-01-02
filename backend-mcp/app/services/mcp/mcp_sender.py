"""MCP sender for sending messages to Langgraph backend"""
from typing import Dict, Any, Optional
import logging
import httpx
from datetime import datetime
import asyncio

from app.core.logging import get_logger, safe_log
from app.core.config import settings
from app.core.exceptions import MCPError
from app.models.schemas import (
    MCPMessageSchema,
    MCPResponseSchema,
    LanggraphResponseSchema
)
from app.services.preprocessing.pdf_processor import PDFProcessor
from .mcp_client import MCPClient

logger = get_logger(__name__)


class MCPSender:
    """Sender for MCP messages to Langgraph"""
    
    def __init__(self, mcp_client: Optional[MCPClient] = None):
        """
        Initialize MCP sender.
        
        Args:
            mcp_client: MCP client instance (creates new if None)
        """
        self.client = mcp_client if mcp_client else MCPClient()
        self.langgraph_url = getattr(settings, 'langgraph_url', 'http://localhost:8002')
        self.api_key = getattr(settings, 'langgraph_api_key', None)
        self.base_timeout = getattr(settings, 'langgraph_timeout', 30.0)
        self.max_retries = 3
        self.retry_delays = [2.0, 4.0, 8.0]  # Backoff delays in seconds
        self.pdf_processor = PDFProcessor()
        
        safe_log(
            logger,
            logging.INFO,
            "MCPSender initialized",
            langgraph_url=self.langgraph_url,
            base_timeout=self.base_timeout
        )
    
    def calculate_timeout(self, fields_count: int = 0, documents_count: int = 0) -> float:
        """
        Calculate adaptive timeout based on form complexity.
        
        Args:
            fields_count: Number of fields to extract
            documents_count: Number of documents to process
            
        Returns:
            Calculated timeout in seconds
        """
        timeout_base = getattr(settings, 'timeout_base', 30.0)
        timeout_per_field = getattr(settings, 'timeout_per_field', 0.5)
        timeout_per_document = getattr(settings, 'timeout_per_document', 10.0)
        timeout_max = getattr(settings, 'timeout_max', 300.0)
        
        fields_factor = fields_count * timeout_per_field
        documents_factor = documents_count * timeout_per_document
        calculated_timeout = timeout_base + fields_factor + documents_factor
        
        # Cap at maximum timeout
        final_timeout = min(calculated_timeout, timeout_max)
        
        safe_log(
            logger,
            logging.INFO,
            "Timeout calculated",
            fields_count=fields_count,
            documents_count=documents_count,
            calculated_timeout=calculated_timeout,
            final_timeout=final_timeout
        )
        
        return final_timeout
    
    async def send_to_langgraph(
        self,
        mcp_message: MCPMessageSchema,
        async_mode: bool = False
    ) -> MCPResponseSchema:
        """
        Send message to Langgraph backend.
        
        Args:
            mcp_message: MCP message schema
            async_mode: If True, returns immediately (for async queue)
            
        Returns:
            MCP response schema
        """
        message_id = mcp_message.message_id if mcp_message.message_id else "unknown"
        
        try:
            safe_log(
                logger,
                logging.INFO,
                "Sending message to Langgraph",
                message_id=message_id
            )
            
            if async_mode:
                # For async mode, just return acknowledgment
                return MCPResponseSchema(
                    message_id=message_id,
                    status="pending",
                    extracted_data={},
                    confidence_scores={}
                )
            
            # Send synchronously with retry
            start_time = datetime.utcnow()
            
            for attempt in range(self.max_retries):
                try:
                    response = await self._send_request(mcp_message)
                    
                    # Calculate round-trip time
                    end_time = datetime.utcnow()
                    round_trip_time = (end_time - start_time).total_seconds()
                    
                    # Handle response
                    handled_response = await self.handle_langgraph_response(response)
                    handled_response.message_id = message_id
                    
                    safe_log(
                        logger,
                        logging.INFO,
                        "Message sent successfully",
                        message_id=message_id,
                        round_trip_time=round_trip_time,
                        attempt=attempt + 1
                    )
                    
                    return handled_response
                    
                except httpx.TimeoutException as e:
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delays[attempt]
                        safe_log(
                            logger,
                            logging.WARNING,
                            "Timeout sending message, retrying",
                            message_id=message_id,
                            attempt=attempt + 1,
                            delay=delay
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise
                        
                except httpx.HTTPStatusError as e:
                    status_code = e.response.status_code if e.response else 0
                    response_text = e.response.text if e.response else "No response"
                    response_preview = response_text[:1000] if response_text else "No response"
                    safe_log(
                        logger,
                        logging.WARNING,
                        "HTTP error from LangGraph",
                        message_id=message_id,
                        status_code=status_code,
                        response_text_length=len(response_text) if response_text else 0,
                        response_preview=response_preview,
                        error_type=type(e).__name__
                    )
                    if status_code >= 500 and attempt < self.max_retries - 1:
                        # Server error, retry
                        delay = self.retry_delays[attempt]
                        safe_log(
                            logger,
                            logging.WARNING,
                            "Server error, retrying",
                            message_id=message_id,
                            status_code=status_code,
                            attempt=attempt + 1,
                            delay=delay
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise
            
            # Should not reach here
            raise MCPError("Failed to send message after retries")
            
        except Exception as e:
            import traceback
            safe_log(
                logger,
                logging.ERROR,
                "Error sending message to Langgraph",
                message_id=message_id,
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error"
            )
            
            return MCPResponseSchema(
                message_id=message_id,
                status="error",
                error=str(e) if e else "Unknown error",
                extracted_data={},
                confidence_scores={}
            )
    
    async def _send_request(self, mcp_message: MCPMessageSchema) -> httpx.Response:
        """Send HTTP request to Langgraph backend with adaptive timeout"""
        url = f"{self.langgraph_url.rstrip('/')}/api/langgraph/process-mcp-request"
        
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Convert MCP message to format expected by backend-langgraph
        request_body = await self._convert_mcp_message_to_langgraph_format(mcp_message)
        
        # Calculate adaptive timeout based on complexity
        form_json_count = len(request_body.get("form_json", []))
        documents_count = len(request_body.get("documents", []))
        calculated_timeout = self.calculate_timeout(form_json_count, documents_count)
        
        async with httpx.AsyncClient(timeout=calculated_timeout) as client:
            response = await client.post(url, json=request_body, headers=headers)
            response.raise_for_status()
            return response
    
    async def _convert_mcp_message_to_langgraph_format(
        self,
        mcp_message: MCPMessageSchema
    ) -> Dict[str, Any]:
        """
        Convert MCP message to format expected by backend-langgraph endpoint.
        
        Expected format:
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
            "form_json": [...]
        }
        """
        import base64
        
        # Extract metadata
        record_id = mcp_message.metadata.record_id if mcp_message.metadata else "unknown"
        record_type = mcp_message.metadata.record_type if mcp_message.metadata else "Claim"
        
        # Extract user request from prompt
        user_request = mcp_message.prompt or ""
        
        # Extract session_id from context
        session_id = mcp_message.context.get("session_id") if mcp_message.context else None
        
        # Convert documents
        documents = []
        context_documents = mcp_message.context.get("documents", []) if mcp_message.context else []
        
        for doc_data in context_documents:
            doc_id = doc_data.get("document_id") or doc_data.get("id", "unknown")
            doc_type = doc_data.get("type", "application/pdf")
            doc_url = doc_data.get("url", "")
            
            # Download document and convert to base64 if URL provided
            pages = []
            if doc_url:
                try:
                    # Validate URL format before attempting download
                    if not doc_url or not isinstance(doc_url, str) or not doc_url.strip():
                        safe_log(
                            logger,
                            logging.WARNING,
                            "Invalid document URL, skipping",
                            document_id=doc_id,
                            document_url=doc_url or "empty"
                        )
                        continue
                    
                    # Normalize URL (handle relative paths and Docker service names)
                    normalized_url = doc_url.strip()
                    # If URL starts with /uploads/, it might be a relative path
                    # In Docker, we need to use the service name
                    if normalized_url.startswith("/uploads/"):
                        # Try to construct full URL using backend-mcp service
                        base_url = settings.langgraph_url.replace(":8002", ":8000") if ":8002" in settings.langgraph_url else "http://backend-mcp:8000"
                        normalized_url = f"{base_url}{normalized_url}"
                    elif normalized_url.startswith("http://localhost") or normalized_url.startswith("http://127.0.0.1"):
                        # Replace localhost with service name in Docker
                        normalized_url = normalized_url.replace("http://localhost:8000", "http://backend-mcp:8000")
                        normalized_url = normalized_url.replace("http://127.0.0.1:8000", "http://backend-mcp:8000")
                    
                    # Download document with improved error handling
                    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                        try:
                            doc_response = await client.get(normalized_url)
                            doc_response.raise_for_status()
                            doc_content = doc_response.content
                        except httpx.TimeoutException:
                            safe_log(
                                logger,
                                logging.WARNING,
                                "Document download timeout, skipping",
                                document_id=doc_id,
                                document_url=normalized_url,
                                timeout_seconds=30.0
                            )
                            continue
                        except httpx.HTTPStatusError as http_err:
                            safe_log(
                                logger,
                                logging.WARNING,
                                "Document download HTTP error, skipping",
                                document_id=doc_id,
                                document_url=normalized_url,
                                status_code=http_err.response.status_code,
                                error_message=str(http_err)
                            )
                            continue
                        except httpx.RequestError as req_err:
                            safe_log(
                                logger,
                                logging.WARNING,
                                "Document download request error, skipping",
                                document_id=doc_id,
                                document_url=normalized_url,
                                error_type=type(req_err).__name__,
                                error_message=str(req_err)
                            )
                            continue
                    
                    # Validate document size (50MB limit)
                    max_size = 50 * 1024 * 1024  # 50MB
                    if len(doc_content) > max_size:
                        safe_log(
                            logger,
                            logging.WARNING,
                            "Document size exceeds limit, skipping",
                            document_id=doc_id,
                            document_size_mb=round(len(doc_content) / (1024 * 1024), 2),
                            max_size_mb=50
                        )
                        continue
                    
                    # Determine MIME type
                    image_mime = doc_type
                    if not image_mime:
                        image_mime = "application/pdf"
                    
                    # Handle PDF documents - extract all pages
                    if image_mime == "application/pdf":
                        safe_log(
                            logger,
                            logging.INFO,
                            "Processing PDF document",
                            document_id=doc_id
                        )
                        pages = self.pdf_processor.extract_pdf_pages(doc_content)
                        
                        if not pages:
                            safe_log(
                                logger,
                                logging.WARNING,
                                "No pages extracted from PDF, treating as single page",
                                document_id=doc_id
                            )
                            # Fallback: treat as single page
                            image_b64 = base64.b64encode(doc_content).decode('utf-8')
                            pages.append({
                                "page_number": 1,
                                "image_b64": image_b64,
                                "image_mime": "application/pdf"
                            })
                    else:
                        # For non-PDF images, treat as single page
                        image_b64 = base64.b64encode(doc_content).decode('utf-8')
                        pages.append({
                            "page_number": 1,
                            "image_b64": image_b64,
                            "image_mime": image_mime
                        })
                    
                    safe_log(
                        logger,
                        logging.INFO,
                        "Document processed successfully",
                        document_id=doc_id,
                        pages_count=len(pages),
                        document_type=image_mime
                    )
                    
                except Exception as e:
                    safe_log(
                        logger,
                        logging.WARNING,
                        "Failed to download document, skipping",
                        document_id=doc_id,
                        document_url=doc_url,
                        error_type=type(e).__name__,
                        error_message=str(e) if e else "Unknown"
                    )
                    # Continue without this document
                    continue
            
            if pages:
                documents.append({
                    "id": doc_id,
                    "type": doc_type,
                    "pages": pages,
                    "metadata": doc_data.get("metadata", {})
                })
        
        # Extract form_json from context (send as-is, no conversion)
        form_json = mcp_message.context.get("form_json", []) if mcp_message.context else []
        
        safe_log(
            logger,
            logging.INFO,
            "Extracting form_json from context",
            record_id=record_id,
            form_json_count=len(form_json) if isinstance(form_json, list) else 0,
            form_json_type=type(form_json).__name__
        )
        
        # Validate documents before sending
        documents_validation_errors = []
        valid_documents = []
        
        for idx, doc in enumerate(documents):
            try:
                if not isinstance(doc, dict):
                    documents_validation_errors.append(f"Document {idx}: not a dict")
                    continue
                
                doc_id = doc.get("id", "unknown")
                pages = doc.get("pages", [])
                
                if not isinstance(pages, list):
                    documents_validation_errors.append(f"Document {idx} ({doc_id}): pages is not a list")
                    continue
                
                if not pages:
                    documents_validation_errors.append(f"Document {idx} ({doc_id}): no pages")
                    continue
                
                # Validate pages have image_b64
                valid_pages = []
                for page_idx, page in enumerate(pages):
                    if not isinstance(page, dict):
                        documents_validation_errors.append(f"Document {idx} ({doc_id}), page {page_idx}: not a dict")
                        continue
                    
                    image_b64 = page.get("image_b64", "")
                    if not image_b64 or not isinstance(image_b64, str) or len(image_b64) < 100:
                        documents_validation_errors.append(f"Document {idx} ({doc_id}), page {page_idx}: invalid or missing image_b64")
                        continue
                    
                    valid_pages.append(page)
                
                if not valid_pages:
                    documents_validation_errors.append(f"Document {idx} ({doc_id}): no valid pages")
                    continue
                
                # Update document with only valid pages
                doc["pages"] = valid_pages
                valid_documents.append(doc)
                
            except Exception as e:
                documents_validation_errors.append(f"Document {idx}: error {type(e).__name__}: {str(e)}")
                continue
        
        # Log validation results
        safe_log(
            logger,
            logging.INFO,
            "Documents validation before sending to LangGraph",
            record_id=record_id,
            total_documents=len(documents),
            valid_documents=len(valid_documents),
            validation_errors_count=len(documents_validation_errors),
            validation_errors=documents_validation_errors[:5] if documents_validation_errors else []
        )
        
        # Build request body with validated documents
        request_body = {
            "record_id": record_id,
            "session_id": session_id,
            "user_request": user_request,  # Prompt as-is
            "documents": valid_documents,
            "form_json": form_json  # Form JSON as-is, no fields_dictionary
        }
        
        safe_log(
            logger,
            logging.INFO,
            "Converted MCP message to LangGraph format",
            record_id=record_id,
            documents_count=len(valid_documents),
            total_pages=sum(len(doc.get("pages", [])) for doc in valid_documents),
            form_json_count=len(form_json) if isinstance(form_json, list) else 0,
            has_validation_errors=len(documents_validation_errors) > 0
        )
        
        # Warn if documents were filtered
        if documents_validation_errors:
            safe_log(
                logger,
                logging.WARNING,
                "Some documents were filtered due to validation errors",
                record_id=record_id,
                filtered_count=len(documents) - len(valid_documents),
                errors=documents_validation_errors[:10]
            )
        
        return request_body
    
    async def handle_langgraph_response(
        self,
        response: httpx.Response
    ) -> MCPResponseSchema:
        """
        Handle response from Langgraph backend.
        
        Args:
            response: HTTP response from Langgraph
            
        Returns:
            MCP response schema
        """
        try:
            # Parse JSON response
            response_text = response.text
            response_data = response.json()
            
            # Log raw response details
            safe_log(
                logger,
                logging.INFO,
                "LangGraph raw HTTP response received",
                status_code=response.status_code,
                response_text_length=len(response_text),
                response_text_preview=response_text[:1000] if response_text else "No response text"
            )
            
            # Log full response structure (first level)
            safe_log(
                logger,
                logging.DEBUG,
                "LangGraph response JSON structure",
                response_keys=list(response_data.keys()) if isinstance(response_data, dict) else [],
                response_status=response_data.get("status") if isinstance(response_data, dict) else None,
                has_data_key="data" in response_data if isinstance(response_data, dict) else False
            )
            
            # Log full response structure for debugging
            data_section = response_data.get("data", {}) if "data" in response_data else {}
            extracted_data_in_response = data_section.get("extracted_data", {}) if "extracted_data" in data_section else {}
            
            safe_log(
                logger,
                logging.INFO,
                "LangGraph response received",
                response_status=response_data.get("status"),
                has_data=("data" in response_data),
                data_keys=list(data_section.keys()) if data_section else [],
                has_extracted_data_in_data=("extracted_data" in data_section),
                extracted_data_type=type(extracted_data_in_response).__name__,
                extracted_data_keys=list(extracted_data_in_response.keys())[:10] if extracted_data_in_response else [],
                extracted_data_count=len(extracted_data_in_response) if extracted_data_in_response else 0,
                extracted_data_sample=str(dict(list(extracted_data_in_response.items())[:3])) if extracted_data_in_response and isinstance(extracted_data_in_response, dict) else str(extracted_data_in_response)[:200],
                response_data_keys=list(response_data.keys())
            )
            
            # Extract data from response structure: {"status": "success", "data": {...}}
            if response_data.get("status") == "success" and "data" in response_data:
                data = response_data["data"]
                filled_form_json = data.get("filled_form_json", [])  # Primary: filled form JSON
                extracted_data = data.get("extracted_data", {})  # Deprecated: kept for backward compatibility
                confidence_scores = data.get("confidence_scores", {})
                quality_score = data.get("quality_score")
                
                # Check if extracted_data is null or empty
                extracted_data_is_none = extracted_data is None
                extracted_data_is_empty = not extracted_data or len(extracted_data) == 0
                
                safe_log(
                    logger,
                    logging.INFO,
                    "Data extracted from LangGraph response",
                    extracted_data_keys=list(extracted_data.keys())[:10] if extracted_data else [],
                    extracted_data_count=len(extracted_data) if extracted_data else 0,
                    extracted_data_is_none=extracted_data_is_none,
                    extracted_data_is_empty=extracted_data_is_empty,
                    confidence_scores_count=len(confidence_scores) if confidence_scores else 0,
                    quality_score=quality_score,
                    has_extracted_data=bool(extracted_data)
                )
            else:
                # Fallback: try to parse as LanggraphResponseSchema directly
                try:
                    langgraph_response = LanggraphResponseSchema(**response_data)
                    filled_form_json = langgraph_response.filled_form_json if langgraph_response.filled_form_json else []
                    extracted_data = langgraph_response.extracted_data if langgraph_response.extracted_data else {}
                    confidence_scores = langgraph_response.confidence_scores if langgraph_response.confidence_scores else {}
                    quality_score = langgraph_response.quality_score
                except Exception:
                    # Last resort: extract from top level
                    filled_form_json = response_data.get("filled_form_json", [])
                    extracted_data = response_data.get("extracted_data", {})
                    confidence_scores = response_data.get("confidence_scores", {})
                    quality_score = response_data.get("quality_score")
            
            # Build MCP response
            mcp_response = MCPResponseSchema(
                message_id="",  # Will be set by caller
                filled_form_json=filled_form_json,  # Same structure as input
                extracted_data=extracted_data,  # Deprecated: kept for backward compatibility
                confidence_scores=confidence_scores,
                quality_score=quality_score,  # Include quality_score in response
                status="success"
            )
            
            safe_log(
                logger,
                logging.INFO,
                "Langgraph response handled",
                filled_form_json_count=len(filled_form_json) if filled_form_json else 0,
                extracted_fields_count=len(extracted_data),
                confidence_scores_count=len(confidence_scores),
                quality_score=quality_score
            )
            
            return mcp_response
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error handling Langgraph response",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown",
                response_status=response.status_code if response else "unknown"
            )
            
            return MCPResponseSchema(
                message_id="",
                status="error",
                error=f"Invalid response: {str(e) if e else 'Unknown error'}",
                filled_form_json=[],
                extracted_data={},
                confidence_scores={}
            )

