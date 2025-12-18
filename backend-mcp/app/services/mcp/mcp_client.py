"""MCP client for connection to Langgraph backend"""
from typing import Optional, Dict, Any
import logging
import httpx
from datetime import datetime

from app.core.logging import get_logger, safe_log
from app.core.config import settings
from app.core.exceptions import MCPError

logger = get_logger(__name__)


class MCPClient:
    """Client for MCP communication with Langgraph backend"""
    
    def __init__(self):
        """Initialize MCP client"""
        self.langgraph_url = getattr(settings, 'langgraph_url', 'http://localhost:8002')
        self.api_key = getattr(settings, 'langgraph_api_key', None)
        self.timeout = getattr(settings, 'langgraph_timeout', 30.0)
        
        # Create HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        
        self.connected = False
        
        safe_log(
            logger,
            logging.INFO,
            "MCPClient initialized",
            langgraph_url=self.langgraph_url,
            timeout=self.timeout
        )
    
    async def connect(self) -> bool:
        """
        Connect to Langgraph backend.
        
        Returns:
            True if connected successfully
        """
        try:
            # Test connection with ping
            result = await self.ping_langgraph_backend()
            
            if result and result.get("status") == "ok":
                self.connected = True
                safe_log(
                    logger,
                    logging.INFO,
                    "MCPClient connected to Langgraph backend"
                )
                return True
            else:
                self.connected = False
                safe_log(
                    logger,
                    logging.WARNING,
                    "MCPClient connection failed",
                    result=result
                )
                return False
                
        except Exception as e:
            self.connected = False
            safe_log(
                logger,
                logging.ERROR,
                "Error connecting to Langgraph backend",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Langgraph backend"""
        try:
            await self.client.aclose()
            self.connected = False
            
            safe_log(
                logger,
                logging.INFO,
                "MCPClient disconnected"
            )
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error disconnecting MCPClient",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
    
    async def ping_langgraph_backend(self) -> Optional[Dict[str, Any]]:
        """
        Ping Langgraph backend for health check.
        
        Returns:
            Health check response or None on error
        """
        try:
            url = f"{self.langgraph_url}/health"
            
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                safe_log(
                    logger,
                    logging.INFO,
                    "Langgraph backend health check successful"
                )
                return result
            else:
                safe_log(
                    logger,
                    logging.WARNING,
                    "Langgraph backend health check failed",
                    status_code=response.status_code
                )
                return {"status": "error", "message": f"HTTP {response.status_code}"}
                
        except httpx.TimeoutException as e:
            safe_log(
                logger,
                logging.ERROR,
                "Timeout pinging Langgraph backend",
                timeout=self.timeout,
                error_message=str(e) if e else "Unknown"
            )
            return {"status": "error", "message": "Timeout"}
            
        except httpx.ConnectError as e:
            safe_log(
                logger,
                logging.ERROR,
                "Connection error pinging Langgraph backend",
                langgraph_url=self.langgraph_url,
                error_message=str(e) if e else "Unknown"
            )
            return {"status": "error", "message": "Connection error"}
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error pinging Langgraph backend",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return {"status": "error", "message": "Unknown error"}

