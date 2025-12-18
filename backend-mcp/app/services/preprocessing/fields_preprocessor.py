"""Fields dictionary preprocessor for enriching field metadata"""
from typing import List, Dict, Any, Optional
import logging

from app.core.logging import get_logger, safe_log
from app.models.schemas import (
    FieldToFillResponseSchema,
    EnrichedFieldSchema,
    FieldsDictionarySchema
)

logger = get_logger(__name__)


class FieldsDictionaryPreprocessor:
    """Preprocessor for preparing and enriching fields dictionary"""
    
    def __init__(self):
        """Initialize fields preprocessor"""
        safe_log(
            logger,
            logging.INFO,
            "FieldsDictionaryPreprocessor initialized"
        )
    
    async def prepare_fields_dictionary(
        self,
        fields_to_fill: List[FieldToFillResponseSchema],
        record_type: str = "Claim"
    ) -> FieldsDictionarySchema:
        """
        Prepare and enrich fields dictionary.
        
        Args:
            fields_to_fill: List of fields to fill
            record_type: Type of record (Claim, Invoice, etc.)
            
        Returns:
            Enriched fields dictionary schema
        """
        try:
            safe_log(
                logger,
                logging.INFO,
                "Preparing fields dictionary",
                fields_count=len(fields_to_fill) if fields_to_fill else 0,
                record_type=record_type or "unknown"
            )
            
            if not fields_to_fill:
                safe_log(
                    logger,
                    logging.WARNING,
                    "Empty fields list provided"
                )
                return FieldsDictionarySchema(
                    fields=[],
                    empty_fields=[],
                    prefilled_fields=[],
                    prioritized_fields=[]
                )
            
            enriched_fields = []
            empty_fields = []
            prefilled_fields = []
            
            # Process each field
            for field in fields_to_fill:
                try:
                    enriched_field = await self.enrich_field_metadata(field, record_type)
                    enriched_fields.append(enriched_field)
                    
                    # Categorize fields
                    if field.value is None or not field.value.strip():
                        empty_fields.append(enriched_field)
                    else:
                        prefilled_fields.append(enriched_field)
                        
                except Exception as e:
                    safe_log(
                        logger,
                        logging.ERROR,
                        "Error enriching field",
                        field_name=field.field_name if field else "unknown",
                        error_type=type(e).__name__,
                        error_message=str(e) if e else "Unknown"
                    )
                    continue
            
            # Prioritize fields
            prioritized_fields = await self.prioritize_fields(enriched_fields)
            
            result = FieldsDictionarySchema(
                fields=enriched_fields,
                empty_fields=empty_fields,
                prefilled_fields=prefilled_fields,
                prioritized_fields=prioritized_fields
            )
            
            safe_log(
                logger,
                logging.INFO,
                "Fields dictionary prepared",
                total_fields=len(enriched_fields),
                empty_fields=len(empty_fields),
                prefilled_fields=len(prefilled_fields)
            )
            
            return result
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in prepare_fields_dictionary",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error"
            )
            return FieldsDictionarySchema(
                fields=[],
                empty_fields=[],
                prefilled_fields=[],
                prioritized_fields=[]
            )
    
    async def enrich_field_metadata(
        self,
        field: FieldToFillResponseSchema,
        record_type: str = "Claim"
    ) -> EnrichedFieldSchema:
        """
        Enrich field with metadata and context.
        
        Args:
            field: Field to enrich
            record_type: Type of record
            
        Returns:
            Enriched field schema
        """
        try:
            # Get template for record type
            template = self._get_field_template(field.field_type, record_type)
            
            # Build enriched field
            enriched = EnrichedFieldSchema(
                field_name=field.field_name if field.field_name else "unknown",
                field_type=field.field_type if field.field_type else "text",
                value=field.value,
                required=field.required if field.required is not None else True,
                label=field.label if field.label else field.field_name if field.field_name else "Unknown",
                description=template.get("description", ""),
                expected_format=template.get("format", ""),
                examples=template.get("examples", []),
                validation_rules=template.get("validation_rules", {}),
                business_context=template.get("business_context", "")
            )
            
            return enriched
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error enriching field metadata",
                field_name=field.field_name if field else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            # Return minimal enriched field on error
            return EnrichedFieldSchema(
                field_name=field.field_name if field else "unknown",
                field_type=field.field_type if field else "text",
                value=field.value if field else None,
                required=field.required if field else True,
                label=field.label if field else "Unknown",
                description="",
                expected_format="",
                examples=[],
                validation_rules={},
                business_context=""
            )
    
    def _get_field_template(
        self,
        field_type: str,
        record_type: str
    ) -> Dict[str, Any]:
        """Get template for field enrichment based on type"""
        templates = {
            "currency": {
                "description": "Montant monétaire",
                "format": "Decimal avec 2 décimales (ex: 1250.50)",
                "examples": ["1250.50", "999.99", "0.00"],
                "validation_rules": {
                    "type": "decimal",
                    "min": 0,
                    "max": 999999.99,
                    "regex": r"^\d+\.\d{2}$"
                },
                "business_context": "Montant doit être positif et en euros"
            },
            "date": {
                "description": "Date au format ISO",
                "format": "YYYY-MM-DD (ex: 2024-01-15)",
                "examples": ["2024-01-15", "2023-12-31"],
                "validation_rules": {
                    "type": "date",
                    "format": "ISO",
                    "regex": r"^\d{4}-\d{2}-\d{2}$"
                },
                "business_context": "Date doit être valide et dans le passé pour les factures"
            },
            "text": {
                "description": "Texte libre",
                "format": "Chaîne de caractères",
                "examples": ["Nom du bénéficiaire", "Description"],
                "validation_rules": {
                    "type": "string",
                    "min_length": 1,
                    "max_length": 255
                },
                "business_context": "Texte doit être non vide"
            }
        }
        
        return templates.get(field_type.lower(), {
            "description": f"Champ de type {field_type}",
            "format": "Format à déterminer",
            "examples": [],
            "validation_rules": {},
            "business_context": ""
        })
    
    async def prioritize_fields(
        self,
        fields: List[EnrichedFieldSchema]
    ) -> List[EnrichedFieldSchema]:
        """
        Prioritize fields for filling order.
        
        Priority:
        1. Required empty fields
        2. Required prefilled fields (for validation)
        3. Optional empty fields
        4. Optional prefilled fields
        
        Args:
            fields: List of enriched fields
            
        Returns:
            Prioritized list of fields
        """
        try:
            # Separate by required/optional and empty/prefilled
            required_empty = []
            required_prefilled = []
            optional_empty = []
            optional_prefilled = []
            
            for field in fields:
                is_empty = field.value is None or not str(field.value).strip()
                
                if field.required:
                    if is_empty:
                        required_empty.append(field)
                    else:
                        required_prefilled.append(field)
                else:
                    if is_empty:
                        optional_empty.append(field)
                    else:
                        optional_prefilled.append(field)
            
            # Combine in priority order
            prioritized = required_empty + required_prefilled + optional_empty + optional_prefilled
            
            safe_log(
                logger,
                logging.INFO,
                "Fields prioritized",
                total_fields=len(fields),
                required_empty=len(required_empty),
                required_prefilled=len(required_prefilled)
            )
            
            return prioritized
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error prioritizing fields",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return fields  # Return original order on error

