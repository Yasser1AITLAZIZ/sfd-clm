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
    
    def _get_document_attr(self, doc: Any, attr: str, default: Any = None) -> Any:
        """Safely get attribute from document (dict or object)"""
        if isinstance(doc, dict):
            return doc.get(attr, default)
        return getattr(doc, attr, default)
    
    async def process_documents(
        self,
        documents_list: List[Any]
    ) -> List[ProcessedDocumentSchema]:
        """
        Process and normalize documents.
        
        Args:
            documents_list: List of document schemas from Salesforce (can be dict or DocumentResponseSchema)
            
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
                    doc_id = self._get_document_attr(doc, "document_id", "unknown")
                    safe_log(
                        logger,
                        logging.ERROR,
                        "Error processing document",
                        document_index=i,
                        document_id=doc_id,
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
            import traceback
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in process_documents",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error",
                traceback=traceback.format_exc()
            )
            return []
    
    async def _process_single_document(
        self,
        document: Any,
        index: int
    ) -> Optional[ProcessedDocumentSchema]:
        """Process a single document (can be dict or DocumentResponseSchema)"""
        try:
            # Extract metadata
            metadata = await self.extract_document_metadata(document)
            
            # Get document attributes safely
            doc_id = self._get_document_attr(document, "document_id") or f"doc_{index}"
            doc_name = self._get_document_attr(document, "name") or f"document_{index}"
            doc_url = self._get_document_attr(document, "url") or ""
            doc_type = self._get_document_attr(document, "type") or "application/pdf"
            doc_indexed = self._get_document_attr(document, "indexed")
            if doc_indexed is None:
                doc_indexed = True
            
            # Build processed document
            processed_doc = ProcessedDocumentSchema(
                document_id=doc_id,
                name=doc_name,
                url=doc_url,
                type=doc_type,
                indexed=doc_indexed,
                metadata=metadata,
                processed=True
            )
            
            return processed_doc
            
        except Exception as e:
            doc_id = self._get_document_attr(document, "document_id", "unknown")
            safe_log(
                logger,
                logging.ERROR,
                "Error processing single document",
                document_id=doc_id,
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return None
    
    async def extract_document_metadata(
        self,
        document: Any
    ) -> DocumentMetadataSchema:
        """
        Extract metadata from document (can be dict or DocumentResponseSchema).
        
        Args:
            document: Document schema or dict
            
        Returns:
            Document metadata schema
        """
        try:
            # Get document attributes safely
            doc_name = self._get_document_attr(document, "name", "unknown")
            doc_type = self._get_document_attr(document, "type", "application/pdf")
            
            # Basic metadata extraction
            metadata = DocumentMetadataSchema(
                filename=doc_name,
                size=0,  # Will be determined if document is downloaded
                mime_type=doc_type,
                pages_count=0,  # Will be determined for PDFs
                dimensions=None,  # Will be determined for images
                orientation=None  # Will be determined for images
            )
            
            # Note: Actual page count extraction happens during PDF processing in mcp_sender.py
            # using PDFProcessor. This method provides basic metadata.
            # For full metadata including page count, see PDFProcessor.extract_pdf_pages()
            
            return metadata
            
        except Exception as e:
            doc_id = self._get_document_attr(document, "document_id", "unknown")
            doc_name = self._get_document_attr(document, "name", "unknown")
            doc_type = self._get_document_attr(document, "type", "application/pdf")
            safe_log(
                logger,
                logging.ERROR,
                "Error extracting document metadata",
                document_id=doc_id,
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            # Return minimal metadata on error
            return DocumentMetadataSchema(
                filename=doc_name,
                size=0,
                mime_type=doc_type,
                pages_count=0,
                dimensions=None,
                orientation=None
            )
    

