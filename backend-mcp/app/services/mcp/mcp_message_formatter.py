"""MCP message formatter for formatting messages according to MCP protocol"""
from typing import Dict, Any, List, Optional
import logging
import uuid
from datetime import datetime
import base64

from app.core.logging import get_logger, safe_log
from app.models.schemas import (
    MCPMessageSchema,
    MCPMetadataSchema,
    ProcessedDocumentSchema
)

logger = get_logger(__name__)

# MCP protocol limits
MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB


class MCPMessageFormatter:
    """Formatter for MCP messages"""
    
    def __init__(self):
        """Initialize MCP message formatter"""
        safe_log(
            logger,
            logging.INFO,
            "MCPMessageFormatter initialized"
        )
    
    def format_message(
        self,
        prompt: str,
        context: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> MCPMessageSchema:
        """
        Format message according to MCP protocol.
        
        Args:
            prompt: Prompt text
            context: Context dictionary with documents, fields, session_id
            metadata: Metadata dictionary with record_id, record_type, timestamp
            
        Returns:
            MCP message schema
        """
        try:
            message_id = str(uuid.uuid4())
            
            # Serialize documents for MCP
            serialized_documents = self.serialize_documents_for_mcp(
                context.get("documents", [])
            )
            
            # Build message
            message = MCPMessageSchema(
                message_id=message_id,
                prompt=prompt,
                context={
                    "documents": serialized_documents,
                    "fields": context.get("fields", []),
                    "session_id": context.get("session_id")
                },
                metadata=MCPMetadataSchema(
                    record_id=metadata.get("record_id", "unknown"),
                    record_type=metadata.get("record_type", "Claim"),
                    timestamp=metadata.get("timestamp", datetime.utcnow().isoformat())
                )
            )
            
            # Validate message size
            message_size = self._estimate_message_size(message)
            if message_size > MAX_MESSAGE_SIZE:
                safe_log(
                    logger,
                    logging.WARNING,
                    "Message exceeds size limit",
                    message_size=message_size,
                    max_size=MAX_MESSAGE_SIZE
                )
                # Truncate prompt if needed
                max_prompt_size = MAX_MESSAGE_SIZE - (message_size - len(prompt))
                if max_prompt_size > 0:
                    message.prompt = prompt[:max_prompt_size]
                else:
                    raise ValueError(f"Message too large: {message_size} bytes")
            
            safe_log(
                logger,
                logging.INFO,
                "MCP message formatted",
                message_id=message_id,
                message_size=message_size
            )
            
            return message
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error formatting MCP message",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error"
            )
            raise
    
    def serialize_documents_for_mcp(
        self,
        documents: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Serialize documents for MCP protocol.
        Handles both Pydantic models and dictionaries (from JSON).
        
        Args:
            documents: List of processed documents (can be Pydantic models or dicts)
            
        Returns:
            List of serialized document dictionaries
        """
        try:
            serialized = []
            
            for doc in documents:
                # Handle dictionaries (from JSON deserialization)
                if isinstance(doc, dict):
                    doc_dict = {
                        "document_id": doc.get("document_id", "unknown"),
                        "name": doc.get("name", "unknown"),
                        "type": doc.get("type", "application/pdf"),
                        "url": doc.get("url", ""),
                        "metadata": doc.get("metadata", {})
                    }
                else:
                    # Handle Pydantic models or objects with attributes
                    doc_dict = {
                        "document_id": getattr(doc, 'document_id', None) or "unknown",
                        "name": getattr(doc, 'name', None) or "unknown",
                        "type": getattr(doc, 'type', None) or "application/pdf",
                        "url": getattr(doc, 'url', None) or "",
                        "metadata": {}
                    }
                    
                    # Add metadata if available
                    if hasattr(doc, 'metadata') and doc.metadata:
                        if hasattr(doc.metadata, 'model_dump'):
                            doc_dict["metadata"] = doc.metadata.model_dump()
                        elif isinstance(doc.metadata, dict):
                            doc_dict["metadata"] = doc.metadata
                
                serialized.append(doc_dict)
            
            safe_log(
                logger,
                logging.INFO,
                "Documents serialized for MCP",
                documents_count=len(serialized)
            )
            
            return serialized
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error serializing documents for MCP",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return []
    
    def add_metadata(
        self,
        message: MCPMessageSchema,
        metadata_dict: Dict[str, Any]
    ) -> MCPMessageSchema:
        """
        Add metadata to message.
        
        Args:
            message: MCP message schema
            metadata_dict: Dictionary of metadata to add
            
        Returns:
            Updated message schema
        """
        try:
            # Merge metadata
            if message.metadata:
                current_metadata = message.metadata.model_dump() if hasattr(message.metadata, 'model_dump') else {}
                current_metadata.update(metadata_dict)
                message.metadata = MCPMetadataSchema(**current_metadata)
            else:
                message.metadata = MCPMetadataSchema(**metadata_dict)
            
            return message
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error adding metadata to message",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return message
    
    def _estimate_message_size(self, message: MCPMessageSchema) -> int:
        """Estimate message size in bytes"""
        try:
            import json
            message_dict = message.model_dump() if hasattr(message, 'model_dump') else {}
            return len(json.dumps(message_dict).encode('utf-8'))
        except Exception:
            return 0

