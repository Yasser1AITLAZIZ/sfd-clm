"""Form JSON normalizer for ensuring dataValue_target_AI and defaultValue consistency"""
from typing import List, Dict, Any
import logging

from app.core.logging import get_logger, safe_log

logger = get_logger(__name__)


def normalize_form_json(fields: List[Any]) -> List[Dict[str, Any]]:
    """
    Normalize form JSON: ensure dataValue_target_AI exists and defaultValue is null.
    
    Args:
        fields: List of field objects (can be dict, Pydantic model, or any object)
        
    Returns:
        List of normalized field dictionaries
    """
    normalized = []
    
    try:
        for i, field in enumerate(fields):
            try:
                # Convert field to dict
                if isinstance(field, dict):
                    field_copy = field.copy()
                elif hasattr(field, 'model_dump'):
                    # Pydantic model
                    field_copy = field.model_dump()
                elif hasattr(field, '__dict__'):
                    # Regular object
                    field_copy = field.__dict__.copy()
                else:
                    safe_log(
                        logger,
                        logging.WARNING,
                        "Skipping field with unsupported type",
                        field_index=i,
                        field_type=type(field).__name__
                    )
                    continue
                
                # Ensure dataValue_target_AI exists and is null
                if "dataValue_target_AI" not in field_copy:
                    field_copy["dataValue_target_AI"] = None
                else:
                    # Always set to null initially (even if it has a value)
                    field_copy["dataValue_target_AI"] = None
                
                # Ensure defaultValue is null
                field_copy["defaultValue"] = None
                
                normalized.append(field_copy)
                
            except Exception as e:
                safe_log(
                    logger,
                    logging.ERROR,
                    "Error normalizing field",
                    field_index=i,
                    error_type=type(e).__name__,
                    error_message=str(e) if e else "Unknown"
                )
                # Continue with next field
                continue
        
        safe_log(
            logger,
            logging.INFO,
            "Form JSON normalized",
            input_fields_count=len(fields),
            normalized_fields_count=len(normalized)
        )
        
        return normalized
        
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Error in normalize_form_json",
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown"
        )
        return []

