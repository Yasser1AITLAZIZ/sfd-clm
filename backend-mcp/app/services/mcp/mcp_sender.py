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
        """Send HTTP request to Langgraph"""
        url = f"{self.langgraph_url}/api/process"
        
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        message_dict = mcp_message.model_dump() if hasattr(mcp_message, 'model_dump') else {}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=message_dict, headers=headers)
            response.raise_for_status()
            return response
    
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
            
            # Validate structure
            langgraph_response = LanggraphResponseSchema(**response_data)
            
            # Extract data
            extracted_data = langgraph_response.extracted_data if langgraph_response.extracted_data else {}
            confidence_scores = langgraph_response.confidence_scores if langgraph_response.confidence_scores else {}
            
            # Build MCP response
            mcp_response = MCPResponseSchema(
                message_id="",  # Will be set by caller
                extracted_data=extracted_data,
                confidence_scores=confidence_scores,
                status="success"
            )
            
            safe_log(
                logger,
                logging.INFO,
                "Langgraph response handled",
                extracted_fields_count=len(extracted_data),
                confidence_scores_count=len(confidence_scores)
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

