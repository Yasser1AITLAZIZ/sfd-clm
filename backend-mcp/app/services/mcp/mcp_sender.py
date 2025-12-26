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
        self.timeout = getattr(settings, 'langgraph_timeout', 30.0)
        self.max_retries = 3
        self.retry_delays = [2.0, 4.0, 8.0]  # Backoff delays in seconds
        
        safe_log(
            logger,
            logging.INFO,
            "MCPSender initialized",
            langgraph_url=self.langgraph_url
        )
    
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
                    # #region agent log
                    import json as json_lib
                    import time
                    try:
                        response_text = e.response.text if e.response else "No response"
                        with open(r'c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log', 'a', encoding='utf-8') as f:
                            f.write(json_lib.dumps({"id":f"log_{int(time.time()*1000)}_http_error","timestamp":int(time.time()*1000),"location":"mcp_sender.py:121","message":"HTTP error from LangGraph","data":{"status_code":status_code,"response_text":response_text[:500]},"sessionId":"debug-session","runId":"run1","hypothesisId":"E"}) + "\n")
                    except: pass
                    # #endregion
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
            # #region agent log
            import json as json_lib
            import time
            import traceback
            try:
                with open(r'c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json_lib.dumps({"id":f"log_{int(time.time()*1000)}_send_error","timestamp":int(time.time()*1000),"location":"mcp_sender.py:143","message":"Error sending to LangGraph","data":{"error_type":type(e).__name__,"error_message":str(e),"traceback":traceback.format_exc()},"sessionId":"debug-session","runId":"run1","hypothesisId":"E"}) + "\n")
            except: pass
            # #endregion
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
        """Send HTTP request to Langgraph backend"""
        url = f"{self.langgraph_url.rstrip('/')}/api/langgraph/process-mcp-request"
        
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Convert MCP message to format expected by backend-langgraph
        request_body = await self._convert_mcp_message_to_langgraph_format(mcp_message)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
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
            "fields_dictionary": {...}
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
                    # Download document
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        doc_response = await client.get(doc_url)
                        doc_response.raise_for_status()
                        doc_content = doc_response.content
                    
                    # Convert to base64
                    image_b64 = base64.b64encode(doc_content).decode('utf-8')
                    
                    # Determine MIME type
                    image_mime = doc_type
                    if not image_mime or image_mime == "application/pdf":
                        # For PDFs, we'd need to extract pages, but for now treat as single page
                        # TODO: Implement PDF page extraction
                        image_mime = "application/pdf"
                    
                    # Create single page (for now, PDFs treated as single page)
                    # TODO: Split PDF into multiple pages
                    pages.append({
                        "page_number": 1,
                        "image_b64": image_b64,
                        "image_mime": image_mime
                    })
                    
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
        
        # Convert fields dictionary
        fields_dictionary = {}
        context_fields = mcp_message.context.get("fields", []) if mcp_message.context else []
        # #region agent log
        import json as json_lib
        import time
        try:
            with open(r'c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_lib.dumps({"id":f"log_{int(time.time()*1000)}_before_fields_conv","timestamp":int(time.time()*1000),"location":"mcp_sender.py:277","message":"Before fields conversion","data":{"context_fields_count":len(context_fields),"first_field_sample":context_fields[0] if context_fields else None},"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + "\n")
        except: pass
        # #endregion
        
        for i, field in enumerate(context_fields):
            if isinstance(field, dict):
                # Generate unique field_name: use apiName, field_name, or create from label/index
                field_name = field.get("field_name") or field.get("apiName")
                if not field_name or field_name == "unknown":
                    # Create field_name from label (sanitized) or use index
                    label = field.get("label", "")
                    if label:
                        # Sanitize label to create valid field name
                        import re
                        field_name = re.sub(r'[^a-zA-Z0-9_]', '_', label.lower().strip())
                        field_name = re.sub(r'_+', '_', field_name)  # Replace multiple underscores
                        field_name = field_name.strip('_')  # Remove leading/trailing underscores
                        if not field_name:
                            field_name = f"field_{i+1}"
                    else:
                        field_name = f"field_{i+1}"
                
                fields_dictionary[field_name] = {
                    "label": field.get("label", field_name),
                    "type": field.get("field_type") or field.get("type", "text"),
                    "required": field.get("required", False),
                    "possibleValues": field.get("possibleValues", field.get("possible_values", [])),
                    "defaultValue": field.get("defaultValue") or field.get("default_value")
                }
        
        # #region agent log
        try:
            with open(r'c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_lib.dumps({"id":f"log_{int(time.time()*1000)}_after_fields_conv","timestamp":int(time.time()*1000),"location":"mcp_sender.py:299","message":"After fields conversion","data":{"fields_dict_keys":list(fields_dictionary.keys()),"fields_dict_count":len(fields_dictionary)},"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + "\n")
        except: pass
        # #endregion
        
        # Build request body
        request_body = {
            "record_id": record_id,
            "session_id": session_id,
            "user_request": user_request,
            "documents": documents,
            "fields_dictionary": fields_dictionary
        }
        
        safe_log(
            logger,
            logging.INFO,
            "Converted MCP message to LangGraph format",
            record_id=record_id,
            documents_count=len(documents),
            fields_count=len(fields_dictionary)
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
            response_data = response.json()
            # #region agent log
            import json as json_lib
            import time
            try:
                with open(r'c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json_lib.dumps({"id":f"log_{int(time.time()*1000)}_response_received","timestamp":int(time.time()*1000),"location":"mcp_sender.py:342","message":"LangGraph response received","data":{"response_status":response_data.get("status"),"has_data":("data" in response_data),"data_keys":list(response_data.get("data",{}).keys()) if "data" in response_data else []},"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + "\n")
            except: pass
            # #endregion
            
            # Extract data from response structure: {"status": "success", "data": {...}}
            if response_data.get("status") == "success" and "data" in response_data:
                data = response_data["data"]
                extracted_data = data.get("extracted_data", {})
                confidence_scores = data.get("confidence_scores", {})
                quality_score = data.get("quality_score")
                # #region agent log
                try:
                    with open(r'c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json_lib.dumps({"id":f"log_{int(time.time()*1000)}_data_extracted","timestamp":int(time.time()*1000),"location":"mcp_sender.py:348","message":"Data extracted from response","data":{"extracted_data_keys":list(extracted_data.keys()),"extracted_data_count":len(extracted_data),"confidence_scores_count":len(confidence_scores)},"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + "\n")
                except: pass
                # #endregion
            else:
                # Fallback: try to parse as LanggraphResponseSchema directly
                try:
                    langgraph_response = LanggraphResponseSchema(**response_data)
                    extracted_data = langgraph_response.extracted_data if langgraph_response.extracted_data else {}
                    confidence_scores = langgraph_response.confidence_scores if langgraph_response.confidence_scores else {}
                    quality_score = langgraph_response.quality_score
                except Exception:
                    # Last resort: extract from top level
                    extracted_data = response_data.get("extracted_data", {})
                    confidence_scores = response_data.get("confidence_scores", {})
                    quality_score = response_data.get("quality_score")
            
            # Build MCP response
            mcp_response = MCPResponseSchema(
                message_id="",  # Will be set by caller
                extracted_data=extracted_data,
                confidence_scores=confidence_scores,
                status="success"
            )
            # #region agent log
            try:
                with open(r'c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json_lib.dumps({"id":f"log_{int(time.time()*1000)}_mcp_response_built","timestamp":int(time.time()*1000),"location":"mcp_sender.py:364","message":"MCPResponseSchema built","data":{"extracted_data_count":len(mcp_response.extracted_data),"confidence_scores_count":len(mcp_response.confidence_scores),"status":mcp_response.status},"sessionId":"debug-session","runId":"run1","hypothesisId":"D"}) + "\n")
            except: pass
            # #endregion
            
            safe_log(
                logger,
                logging.INFO,
                "Langgraph response handled",
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
                extracted_data={},
                confidence_scores={}
            )

