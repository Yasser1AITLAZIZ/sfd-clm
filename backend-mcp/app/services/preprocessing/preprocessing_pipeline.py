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
from .fields_preprocessor import FieldsDictionaryPreprocessor

logger = get_logger(__name__)


class PreprocessingPipeline:
    """Pipeline for coordinating preprocessing steps"""
    
    def __init__(self):
        """Initialize preprocessing pipeline"""
        self.document_preprocessor = DocumentPreprocessor()
        self.fields_preprocessor = FieldsDictionaryPreprocessor()
        
        safe_log(
            logger,
            logging.INFO,
            "PreprocessingPipeline initialized"
        )
    
    async def execute_preprocessing(
        self,
        salesforce_data: SalesforceDataResponseSchema
    ) -> PreprocessedDataSchema:
        """
        Execute complete preprocessing pipeline.
        
        Steps:
        1. Process documents
        2. Prepare fields dictionary
        3. Cross-validation
        4. Generate context summary
        
        Args:
            salesforce_data: Salesforce data response schema
            
        Returns:
            Preprocessed data schema
        """
        start_time = datetime.utcnow()
        
        try:
            record_id = salesforce_data.record_id if salesforce_data.record_id else "unknown"
            record_type = salesforce_data.record_type if salesforce_data.record_type else "Claim"
            
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
            if salesforce_data.documents:
                processed_documents = await self.document_preprocessor.process_documents(
                    salesforce_data.documents
                )
            
            safe_log(
                logger,
                logging.INFO,
                "Documents processed",
                record_id=record_id,
                processed_count=len(processed_documents)
            )
            
            # Step 2: Prepare fields dictionary
            safe_log(
                logger,
                logging.INFO,
                "Step 2: Preparing fields dictionary",
                record_id=record_id
            )
            
            fields_dictionary = await self.fields_preprocessor.prepare_fields_dictionary(
                salesforce_data.fields_to_fill if salesforce_data.fields_to_fill else [],
                record_type
            )
            
            safe_log(
                logger,
                logging.INFO,
                "Fields dictionary prepared",
                record_id=record_id,
                fields_count=len(fields_dictionary.fields)
            )
            
            # Step 3: Cross-validation
            safe_log(
                logger,
                logging.INFO,
                "Step 3: Cross-validation",
                record_id=record_id
            )
            
            validation_results = await self._cross_validate(
                processed_documents,
                fields_dictionary
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
                fields_dictionary
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
            data_size = self._calculate_data_size(processed_documents, fields_dictionary)
            
            # Build preprocessed data
            preprocessed_data = PreprocessedDataSchema(
                record_id=record_id,
                record_type=record_type,
                processed_documents=processed_documents,
                fields_dictionary=fields_dictionary,
                context_summary=context_summary,
                validation_results=validation_results,
                metrics={
                    "processing_time_seconds": processing_time,
                    "data_size_bytes": data_size,
                    "documents_count": len(processed_documents),
                    "fields_count": len(fields_dictionary.fields)
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
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in preprocessing pipeline",
                record_id=salesforce_data.record_id if salesforce_data else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error"
            )
            # Return minimal preprocessed data on error
            from app.services.preprocessing.fields_preprocessor import FieldsDictionaryPreprocessor
            temp_preprocessor = FieldsDictionaryPreprocessor()
            empty_fields_dict = await temp_preprocessor.prepare_fields_dictionary([])
            
            return PreprocessedDataSchema(
                record_id=salesforce_data.record_id if salesforce_data else "unknown",
                record_type=salesforce_data.record_type if salesforce_data else "Claim",
                processed_documents=[],
                fields_dictionary=empty_fields_dict,
                context_summary=ContextSummarySchema(
                    record_type=salesforce_data.record_type if salesforce_data else "Claim",
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
        fields_dictionary: Any
    ) -> Dict[str, Any]:
        """
        Cross-validate consistency between documents and fields.
        
        Args:
            processed_documents: List of processed documents
            fields_dictionary: Fields dictionary schema
            
        Returns:
            Validation results
        """
        try:
            errors = []
            warnings = []
            
            # Basic validation: check if we have documents and fields
            if not processed_documents:
                warnings.append("No documents available for processing")
            
            if not fields_dictionary.fields:
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
        fields_dictionary: Any
    ) -> ContextSummarySchema:
        """
        Generate context summary for LLM.
        
        Args:
            record_type: Type of record
            processed_documents: List of processed documents
            fields_dictionary: Fields dictionary schema
            
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
                    "type": doc.type if hasattr(doc, 'type') else "unknown",
                    "quality_score": doc.quality_score if hasattr(doc, 'quality_score') else 0
                })
            
            # Build fields list
            fields_to_extract = []
            for field in fields_dictionary.prioritized_fields:
                fields_to_extract.append({
                    "field_name": field.field_name if hasattr(field, 'field_name') else "unknown",
                    "field_type": field.field_type if hasattr(field, 'field_type') else "text",
                    "required": field.required if hasattr(field, 'required') else True,
                    "label": field.label if hasattr(field, 'label') else "Unknown"
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
        fields_dictionary: Any
    ) -> int:
        """Calculate approximate data size in bytes"""
        try:
            size = 0
            
            # Estimate document size (rough)
            for doc in processed_documents:
                size += 1024  # 1KB per document estimate
            
            # Estimate fields size
            if fields_dictionary and hasattr(fields_dictionary, 'fields'):
                size += len(fields_dictionary.fields) * 256  # 256 bytes per field estimate
            
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
                        "type": doc.type if hasattr(doc, 'type') else "unknown",
                        "quality": doc.quality_score if hasattr(doc, 'quality_score') else 0
                    }
                    for doc in preprocessed_data.processed_documents
                ],
                "fields": [
                    {
                        "name": field.field_name if hasattr(field, 'field_name') else "unknown",
                        "type": field.field_type if hasattr(field, 'field_type') else "text",
                        "required": field.required if hasattr(field, 'required') else True,
                        "label": field.label if hasattr(field, 'label') else "Unknown",
                        "description": field.description if hasattr(field, 'description') else "",
                        "examples": field.examples if hasattr(field, 'examples') else []
                    }
                    for field in preprocessed_data.fields_dictionary.prioritized_fields
                ]
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

