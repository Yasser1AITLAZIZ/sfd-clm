"""Fields dictionary preprocessor for enriching field metadata"""
from typing import List, Dict, Any, Optional
import logging

from app.core.logging import get_logger, safe_log
from app.core.exceptions import WorkflowError
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
    
    def _get_field_attr(self, field: Any, attr: str, default: Any = None) -> Any:
        """Safely get attribute from field (dict or object)"""
        if isinstance(field, dict):
            return field.get(attr, default)
        return getattr(field, attr, default)
    
    async def prepare_fields_dictionary(
        self,
        fields_to_fill: List[Any],
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
                    logging.ERROR,
                    "Empty fields list provided - blocking workflow"
                )
                from app.core.exceptions import WorkflowError
                raise WorkflowError("No fields to process - empty fields list")
            
            enriched_fields = []
            empty_fields = []
            prefilled_fields = []
            
            # Process each field
            for field in fields_to_fill:
                try:
                    enriched_field = await self.enrich_field_metadata(field, record_type)
                    enriched_fields.append(enriched_field)
                    
                    # Categorize fields - get value safely
                    field_value = self._get_field_attr(field, "value")
                    if field_value is None or (isinstance(field_value, str) and not field_value.strip()):
                        empty_fields.append(enriched_field)
                    else:
                        prefilled_fields.append(enriched_field)
                        
                except Exception as e:
                    field_name = self._get_field_attr(field, "field_name", "unknown")
                    safe_log(
                        logger,
                        logging.ERROR,
                        "Error enriching field",
                        field_name=field_name,
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
            import traceback
            safe_log(
                logger,
                logging.ERROR,
                "Unexpected error in prepare_fields_dictionary",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error",
                traceback=traceback.format_exc()
            )
            return FieldsDictionarySchema(
                fields=[],
                empty_fields=[],
                prefilled_fields=[],
                prioritized_fields=[]
            )
    
    async def enrich_field_metadata(
        self,
        field: Any,
        record_type: str = "Claim"
    ) -> EnrichedFieldSchema:
        """
        Enrich field with metadata and context (can be dict or FieldToFillResponseSchema).
        
        Args:
            field: Field to enrich (dict or object)
            record_type: Type of record
            
        Returns:
            Enriched field schema
        """
        try:
            # Get field attributes safely
            field_type = self._get_field_attr(field, "field_type", "text")
            field_name = self._get_field_attr(field, "field_name", "unknown")
            field_value = self._get_field_attr(field, "value")
            field_required = self._get_field_attr(field, "required")
            if field_required is None:
                field_required = True
            field_label = self._get_field_attr(field, "label")
            if not field_label:
                field_label = field_name if field_name != "unknown" else "Unknown"
            
            # Get template for record type
            template = self._get_field_template(field_type, record_type)
            
            # Build enriched field
            enriched = EnrichedFieldSchema(
                field_name=field_name,
                field_type=field_type,
                value=field_value,
                required=field_required,
                label=field_label,
                description=template.get("description", ""),
                expected_format=template.get("format", ""),
                examples=template.get("examples", []),
                validation_rules=template.get("validation_rules", {}),
                business_context=template.get("business_context", "")
            )
            
            return enriched
            
        except Exception as e:
            field_name = self._get_field_attr(field, "field_name", "unknown")
            field_type = self._get_field_attr(field, "field_type", "text")
            field_value = self._get_field_attr(field, "value")
            field_required = self._get_field_attr(field, "required", True)
            field_label = self._get_field_attr(field, "label", "Unknown")
            safe_log(
                logger,
                logging.ERROR,
                "Error enriching field metadata",
                field_name=field_name,
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            # Return minimal enriched field on error
            return EnrichedFieldSchema(
                field_name=field_name,
                field_type=field_type,
                value=field_value,
                required=field_required,
                label=field_label,
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

