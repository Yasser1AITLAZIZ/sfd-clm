"""Preprocessing pipeline for coordinating document and fields preprocessing"""
from typing import Dict, Any
import logging
from datetime import datetime

from app.core.logging import get_logger, safe_log
from app.models.schemas import (
    SalesforceDataResponseSchema,
    PreprocessedDataSchema,
    ContextSummarySchema
)
from .document_preprocessor import DocumentPreprocessor
from .form_json_normalizer import normalize_form_json

logger = get_logger(__name__)


class PreprocessingPipeline:
    """Pipeline for coordinating preprocessing steps"""
    
    def __init__(self):
        """Initialize preprocessing pipeline"""
        self.document_preprocessor = DocumentPreprocessor()
        
        safe_log(
            logger,
            logging.INFO,
            "PreprocessingPipeline initialized"
        )
    
    async def execute_preprocessing(
        self,
        salesforce_data: Any
    ) -> PreprocessedDataSchema:
        """
        Execute complete preprocessing pipeline.
        
        Steps:
        1. Process documents
        2. Normalize form JSON (ensure dataValue_target_AI exists, defaultValue is null)
        3. Cross-validation
        4. Generate context summary
        
        Args:
            salesforce_data: Salesforce data response schema (can be Pydantic model or dict)
            
        Returns:
            Preprocessed data schema
        """
        start_time = datetime.utcnow()
        
        try:
            # Handle both Pydantic model and dict
            if not salesforce_data:
                raise ValueError("salesforce_data cannot be None or empty")
            
            # Try to access as dict first (most common case)
            try:
                if isinstance(salesforce_data, dict):
                    record_id = salesforce_data.get("record_id", "unknown")
                    record_type = salesforce_data.get("record_type", "Claim")
                    documents = salesforce_data.get("documents", [])
                    fields_to_fill = salesforce_data.get("fields_to_fill", [])
                elif hasattr(salesforce_data, 'get') and callable(getattr(salesforce_data, 'get', None)):
                    # Dict-like object
                    record_id = salesforce_data.get("record_id", "unknown")
                    record_type = salesforce_data.get("record_type", "Claim")
                    documents = salesforce_data.get("documents", [])
                    fields_to_fill = salesforce_data.get("fields_to_fill", [])
                else:
                    raise AttributeError("Not a dict")
            except (AttributeError, TypeError) as e:
                # Pydantic model - use getattr for safe access
                record_id = getattr(salesforce_data, 'record_id', None) or "unknown"
                record_type = getattr(salesforce_data, 'record_type', None) or "Claim"
                documents = getattr(salesforce_data, 'documents', None) or []
                fields_to_fill = getattr(salesforce_data, 'fields_to_fill', None) or []
            
            safe_log(
                logger,
                logging.INFO,
                "Preprocessing pipeline started",
                record_id=record_id,
                record_type=record_type
            )
            
            # Step 1: Process documents
            safe_log(
                logger,
                logging.INFO,
                "Step 1: Processing documents",
                record_id=record_id
            )
            
            processed_documents = []
            if documents:
                processed_documents = await self.document_preprocessor.process_documents(
                    documents
                )
            
            safe_log(
                logger,
                logging.INFO,
                "Documents processed",
                record_id=record_id,
                processed_count=len(processed_documents)
            )
            
            # Step 2: Normalize form JSON
            safe_log(
                logger,
                logging.INFO,
                "Step 2: Normalizing form JSON",
                record_id=record_id
            )
            
            # Normalize form JSON: ensure dataValue_target_AI exists and defaultValue is null
            normalized_fields = normalize_form_json(fields_to_fill)
            
            safe_log(
                logger,
                logging.INFO,
                "Form JSON normalized",
                record_id=record_id,
                input_fields_count=len(fields_to_fill) if fields_to_fill else 0,
                normalized_fields_count=len(normalized_fields)
            )
            
            # Handle empty fields gracefully (don't block workflow)
            if not normalized_fields:
                safe_log(
                    logger,
                    logging.WARNING,
                    "No fields to process - empty fields list",
                    record_id=record_id
                )
                # Continue with empty list, don't raise error
            
            # Step 3: Cross-validation
            safe_log(
                logger,
                logging.INFO,
                "Step 3: Cross-validation",
                record_id=record_id
            )
            
            validation_results = await self._cross_validate(
                processed_documents,
                normalized_fields
            )
            
            safe_log(
                logger,
                logging.INFO,
                "Cross-validation completed",
                record_id=record_id,
                validation_passed=validation_results.get("passed", False)
            )
            
            # Step 4: Generate context summary
            safe_log(
                logger,
                logging.INFO,
                "Step 4: Generating context summary",
                record_id=record_id
            )
            
            context_summary = await self.generate_context_summary(
                record_type,
                processed_documents,
                normalized_fields
            )
            
            safe_log(
                logger,
                logging.INFO,
                "Context summary generated",
                record_id=record_id
            )
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            # Calculate data size (approximate)
            data_size = self._calculate_data_size(processed_documents, normalized_fields)
            
            # Rebuild salesforce_data with normalized fields
            # Handle both dict and Pydantic model
            if isinstance(salesforce_data, dict):
                salesforce_data_with_normalized = {
                    **salesforce_data,
                    "fields_to_fill": normalized_fields
                }
                salesforce_data_obj = SalesforceDataResponseSchema(**salesforce_data_with_normalized)
            else:
                # Pydantic model - create new with normalized fields
                salesforce_data_dict = salesforce_data.model_dump() if hasattr(salesforce_data, 'model_dump') else salesforce_data.__dict__
                salesforce_data_dict["fields_to_fill"] = normalized_fields
                salesforce_data_obj = SalesforceDataResponseSchema(**salesforce_data_dict)
            
            # Build preprocessed data
            preprocessed_data = PreprocessedDataSchema(
                record_id=record_id,
                record_type=record_type,
                processed_documents=processed_documents,
                salesforce_data=salesforce_data_obj,
                context_summary=context_summary,
                validation_results=validation_results,
                metrics={
                    "processing_time_seconds": processing_time,
                    "data_size_bytes": data_size,
                    "documents_count": len(processed_documents),
                    "fields_count": len(normalized_fields)
                }
            )
            
            safe_log(
                logger,
                logging.INFO,
                "Preprocessing pipeline completed",
                record_id=record_id,
                processing_time=processing_time,
                data_size=data_size
            )
            
            return preprocessed_data
            
        except Exception as e:
            # Extract record_id and record_type safely - use try/except to be extra defensive
            try:
                if salesforce_data and isinstance(salesforce_data, dict):
                    record_id = salesforce_data.get("record_id") or "unknown"
                    record_type = salesforce_data.get("record_type") or "Claim"
                elif salesforce_data:
                    # Use getattr to safely access attributes (works for both Pydantic models and objects)
                    record_id = getattr(salesforce_data, 'record_id', None) or "unknown"
                    record_type = getattr(salesforce_data, 'record_type', None) or "Claim"
                else:
                    record_id = "unknown"
                    record_type = "Claim"
            except Exception as extract_err:
                # If even extracting record_id fails, use defaults
                record_id = "unknown"
                record_type = "Claim"
            
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in preprocessing pipeline",
                record_id=record_id,
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error"
            )
            # Return minimal preprocessed data on error
            empty_salesforce_data = SalesforceDataResponseSchema(
                record_id=record_id,
                record_type=record_type,
                documents=[],
                fields_to_fill=[]
            )
            
            return PreprocessedDataSchema(
                record_id=record_id,
                record_type=record_type,
                processed_documents=[],
                salesforce_data=empty_salesforce_data,
                context_summary=ContextSummarySchema(
                    record_type=record_type,
                    objective="",
                    documents_available=[],
                    fields_to_extract=[],
                    business_rules=[]
                ),
                validation_results={"passed": False, "errors": [str(e)]},
                metrics={
                    "processing_time_seconds": 0,
                    "data_size_bytes": 0,
                    "documents_count": 0,
                    "fields_count": 0
                }
            )
    
    async def _cross_validate(
        self,
        processed_documents: list,
        normalized_fields: list
    ) -> Dict[str, Any]:
        """
        Cross-validate consistency between documents and fields.
        
        Args:
            processed_documents: List of processed documents
            normalized_fields: List of normalized field dictionaries
            
        Returns:
            Validation results
        """
        try:
            errors = []
            warnings = []
            
            # Basic validation: check if we have documents and fields
            if not processed_documents:
                warnings.append("No documents available for processing")
            
            if not normalized_fields:
                warnings.append("No fields to fill")
            
            # TODO: Add more sophisticated cross-validation
            # - Check if document types match expected formats
            # - Validate field types against document content
            # - Check for missing required fields
            
            passed = len(errors) == 0
            
            return {
                "passed": passed,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error in cross-validation",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return {
                "passed": False,
                "errors": [str(e) if e else "Unknown error"],
                "warnings": []
            }
    
    async def generate_context_summary(
        self,
        record_type: str,
        processed_documents: list,
        normalized_fields: list
    ) -> ContextSummarySchema:
        """
        Generate context summary for LLM.
        
        Args:
            record_type: Type of record
            processed_documents: List of processed documents
            normalized_fields: List of normalized field dictionaries
            
        Returns:
            Context summary schema
        """
        try:
            # Build documents list
            documents_available = []
            for doc in processed_documents:
                documents_available.append({
                    "document_id": doc.document_id if hasattr(doc, 'document_id') else "unknown",
                    "name": doc.name if hasattr(doc, 'name') else "unknown",
                    "type": doc.type if hasattr(doc, 'type') else "unknown"
                })
            
            # Build fields list from normalized fields
            fields_to_extract = []
            for field in normalized_fields:
                if isinstance(field, dict):
                    fields_to_extract.append({
                        "label": field.get("label", "Unknown"),
                        "type": field.get("type", "text"),
                        "required": field.get("required", False),
                        "apiName": field.get("apiName")
                    })
                else:
                    # Handle Pydantic model
                    fields_to_extract.append({
                        "label": getattr(field, 'label', 'Unknown'),
                        "type": getattr(field, 'type', 'text'),
                        "required": getattr(field, 'required', False),
                        "apiName": getattr(field, 'apiName', None)
                    })
            
            # Determine objective based on record type
            objective = f"Extraire et remplir les champs manquants pour un {record_type}"
            
            # Business rules based on record type
            business_rules = [
                "Tous les champs requis doivent être remplis",
                "Les montants doivent être positifs",
                "Les dates doivent être au format ISO (YYYY-MM-DD)",
                "Les données doivent être cohérentes entre documents"
            ]
            
            summary = ContextSummarySchema(
                record_type=record_type,
                objective=objective,
                documents_available=documents_available,
                fields_to_extract=fields_to_extract,
                business_rules=business_rules
            )
            
            return summary
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error generating context summary",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return ContextSummarySchema(
                record_type=record_type or "Claim",
                objective="",
                documents_available=[],
                fields_to_extract=[],
                business_rules=[]
            )
    
    def _calculate_data_size(
        self,
        processed_documents: list,
        normalized_fields: list
    ) -> int:
        """Calculate approximate data size in bytes"""
        try:
            size = 0
            
            # Estimate document size (rough)
            for doc in processed_documents:
                size += 1024  # 1KB per document estimate
            
            # Estimate fields size
            if normalized_fields:
                size += len(normalized_fields) * 256  # 256 bytes per field estimate
            
            return size
            
        except Exception:
            return 0
    
    async def prepare_for_llm(
        self,
        preprocessed_data: PreprocessedDataSchema
    ) -> Dict[str, Any]:
        """
        Prepare preprocessed data in optimized format for LLM.
        
        Args:
            preprocessed_data: Preprocessed data schema
            
        Returns:
            Optimized JSON structure for LLM
        """
        try:
            return {
                "record_id": preprocessed_data.record_id,
                "record_type": preprocessed_data.record_type,
                "context_summary": preprocessed_data.context_summary.model_dump() if hasattr(preprocessed_data.context_summary, 'model_dump') else {},
                "documents": [
                    {
                        "id": doc.document_id if hasattr(doc, 'document_id') else "unknown",
                        "name": doc.name if hasattr(doc, 'name') else "unknown",
                        "type": doc.type if hasattr(doc, 'type') else "unknown"
                    }
                    for doc in preprocessed_data.processed_documents
                ],
                "form_json": preprocessed_data.salesforce_data.fields_to_fill if hasattr(preprocessed_data, 'salesforce_data') and hasattr(preprocessed_data.salesforce_data, 'fields_to_fill') else []
            }
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error preparing data for LLM",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return {}

