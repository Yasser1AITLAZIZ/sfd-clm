"""Document preprocessor for normalizing and validating documents"""
from typing import List, Dict, Any, Optional
import logging
import base64
from io import BytesIO

from app.core.logging import get_logger, safe_log
from app.models.schemas import (
    DocumentResponseSchema,
    ProcessedDocumentSchema,
    DocumentMetadataSchema
)

logger = get_logger(__name__)


class DocumentPreprocessor:
    """Preprocessor for processing and normalizing documents"""
    
    def __init__(self):
        """Initialize document preprocessor"""
        safe_log(
            logger,
            logging.INFO,
            "DocumentPreprocessor initialized"
        )
    
    async def process_documents(
        self,
        documents_list: List[DocumentResponseSchema]
    ) -> List[ProcessedDocumentSchema]:
        """
        Process and normalize documents.
        
        Args:
            documents_list: List of document schemas from Salesforce
            
        Returns:
            List of processed documents with metadata
        """
        processed_documents = []
        
        try:
            safe_log(
                logger,
                logging.INFO,
                "Processing documents",
                documents_count=len(documents_list) if documents_list else 0
            )
            
            if not documents_list:
                safe_log(
                    logger,
                    logging.WARNING,
                    "Empty documents list provided"
                )
                return []
            
            for i, doc in enumerate(documents_list):
                try:
                    processed_doc = await self._process_single_document(doc, i)
                    if processed_doc:
                        processed_documents.append(processed_doc)
                except Exception as e:
                    safe_log(
                        logger,
                        logging.ERROR,
                        "Error processing document",
                        document_index=i,
                        document_id=doc.document_id if doc else "unknown",
                        error_type=type(e).__name__,
                        error_message=str(e) if e else "Unknown"
                    )
                    # Continue with other documents
                    continue
            
            safe_log(
                logger,
                logging.INFO,
                "Documents processed successfully",
                processed_count=len(processed_documents),
                total_count=len(documents_list)
            )
            
            return processed_documents
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in process_documents",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error"
            )
            return []
    
    async def _process_single_document(
        self,
        document: DocumentResponseSchema,
        index: int
    ) -> Optional[ProcessedDocumentSchema]:
        """Process a single document"""
        try:
            # Extract metadata
            metadata = await self.extract_document_metadata(document)
            
            # Validate document quality
            quality_score = await self.validate_document_quality(document, metadata)
            
            # Build processed document
            processed_doc = ProcessedDocumentSchema(
                document_id=document.document_id if document.document_id else f"doc_{index}",
                name=document.name if document.name else f"document_{index}",
                url=document.url if document.url else "",
                type=document.type if document.type else "application/pdf",
                indexed=document.indexed if document.indexed is not None else True,
                metadata=metadata,
                quality_score=quality_score,
                processed=True
            )
            
            return processed_doc
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error processing single document",
                document_id=document.document_id if document else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return None
    
    async def extract_document_metadata(
        self,
        document: DocumentResponseSchema
    ) -> DocumentMetadataSchema:
        """
        Extract metadata from document.
        
        Args:
            document: Document schema
            
        Returns:
            Document metadata schema
        """
        try:
            # Basic metadata extraction
            metadata = DocumentMetadataSchema(
                filename=document.name if document.name else "unknown",
                size=0,  # Will be determined if document is downloaded
                mime_type=document.type if document.type else "application/pdf",
                pages_count=0,  # Will be determined for PDFs
                dimensions=None,  # Will be determined for images
                orientation=None  # Will be determined for images
            )
            
            # TODO: Implement actual metadata extraction when documents are available
            # - Download document if URL provided
            # - Extract PDF pages using PyPDF2/pdfplumber
            # - Extract image dimensions using PIL/Pillow
            # - Detect orientation for images
            
            return metadata
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error extracting document metadata",
                document_id=document.document_id if document else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            # Return minimal metadata on error
            return DocumentMetadataSchema(
                filename=document.name if document else "unknown",
                size=0,
                mime_type=document.type if document else "application/pdf",
                pages_count=0,
                dimensions=None,
                orientation=None
            )
    
    async def validate_document_quality(
        self,
        document: DocumentResponseSchema,
        metadata: DocumentMetadataSchema
    ) -> float:
        """
        Validate document quality and return score (0-100).
        
        Args:
            document: Document schema
            metadata: Document metadata
            
        Returns:
            Quality score from 0 to 100
        """
        try:
            score = 100.0
            
            # Check if document has required fields
            if not document.document_id:
                score -= 20
            if not document.name:
                score -= 10
            if not document.url:
                score -= 15
            
            # Check document type
            if document.type:
                valid_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
                if document.type.lower() not in valid_types:
                    score -= 30
            
            # Check if indexed
            if not document.indexed:
                score -= 5
            
            # Ensure score is between 0 and 100
            score = max(0.0, min(100.0, score))
            
            return score
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error validating document quality",
                document_id=document.document_id if document else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return 50.0  # Default score on error

