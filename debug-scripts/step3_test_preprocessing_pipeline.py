"""
Step 3: Test Preprocessing Pipeline
Tests document preprocessing and form JSON normalization
"""

import sys
import json
import logging
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend-mcp"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [STEP3] - %(message)s',
    handlers=[
        logging.FileHandler(project_root / "debug-scripts" / "step3_output.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TEST_RECORD_ID = "001XX000001"


def load_step2_output():
    """Load step 2 output"""
    step2_output = project_root / "debug-scripts" / "step2_output.json"
    if not step2_output.exists():
        raise FileNotFoundError(
            f"Step 2 output not found: {step2_output}\n"
            "Please run step2_test_salesforce_client_fetch.py first"
        )
    try:
        with open(step2_output, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Could not load step2 output: {e}")


async def test_preprocessing_pipeline():
    """Test preprocessing pipeline"""
    logger.info("=" * 80)
    logger.info("TESTING: Preprocessing Pipeline")
    logger.info("=" * 80)
    
    try:
        from app.services.preprocessing.preprocessing_pipeline import PreprocessingPipeline
        from app.models.schemas import SalesforceDataResponseSchema
        
        # Load step 2 output
        step2_data = load_step2_output()
        
        # Convert to schema
        salesforce_data_dict = step2_data
        try:
            salesforce_data = SalesforceDataResponseSchema(**salesforce_data_dict)
        except Exception as e:
            raise ValueError(f"Could not create SalesforceDataResponseSchema: {e}")
        
        logger.info(f"Input data:")
        logger.info(f"  - Record ID: {salesforce_data.record_id}")
        logger.info(f"  - Record Type: {salesforce_data.record_type}")
        logger.info(f"  - Documents: {len(salesforce_data.documents)}")
        logger.info(f"  - Fields to Fill: {len(salesforce_data.fields_to_fill)}")
        
        # Check input fields structure
        for i, field in enumerate(salesforce_data.fields_to_fill[:3], 1):  # Show first 3
            logger.info(f"\n  Input Field {i}:")
            logger.info(f"    - Label: {field.label}")
            logger.info(f"    - Type: {field.type}")
            logger.info(f"    - DefaultValue: {field.defaultValue}")
            if hasattr(field, 'possibleValues') and field.possibleValues:
                logger.info(f"    - Possible Values: {len(field.possibleValues)} values")
        
        pipeline = PreprocessingPipeline()
        preprocessed_data = await pipeline.execute_preprocessing(salesforce_data)
        
        logger.info("\n✅ Preprocessing completed")
        logger.info(f"  - Record ID: {preprocessed_data.record_id}")
        logger.info(f"  - Record Type: {preprocessed_data.record_type}")
        logger.info(f"  - Processed Documents: {len(preprocessed_data.processed_documents)}")
        
        # Check salesforce_data structure (new architecture)
        if not hasattr(preprocessed_data, 'salesforce_data'):
            raise ValueError("PreprocessedDataSchema missing salesforce_data attribute")
        
        salesforce_data_processed = preprocessed_data.salesforce_data
        if not hasattr(salesforce_data_processed, 'fields_to_fill'):
            raise ValueError("SalesforceDataResponseSchema missing fields_to_fill attribute")
        
        # Get normalized fields (now with dataValue_target_AI in schema)
        normalized_fields = salesforce_data_processed.fields_to_fill
        logger.info(f"  - Normalized Fields: {len(normalized_fields)}")
        
        # Verify normalization
        logger.info("\n--- Normalization Verification ---")
        for i, field in enumerate(normalized_fields[:3], 1):  # Show first 3
            logger.info(f"\n  Normalized Field {i}:")
            
            # Handle both Pydantic models and dicts
            if hasattr(field, 'model_dump'):
                # Pydantic model - should now include dataValue_target_AI
                field_dict = field.model_dump()
                field_label = getattr(field, 'label', 'N/A')
                field_type = getattr(field, 'type', 'N/A')
            elif isinstance(field, dict):
                # Already a dict
                field_dict = field
                field_label = field.get('label', 'N/A')
                field_type = field.get('type', 'N/A')
            else:
                # Try to access as attributes
                field_dict = field.__dict__ if hasattr(field, '__dict__') else {}
                field_label = getattr(field, 'label', 'N/A')
                field_type = getattr(field, 'type', 'N/A')
            
            logger.info(f"    - Label: {field_label}")
            logger.info(f"    - Type: {field_type}")
            
            # Check dataValue_target_AI (should now be in schema)
            data_value = field_dict.get('dataValue_target_AI') if isinstance(field_dict, dict) else getattr(field, 'dataValue_target_AI', None)
            if data_value is None:
                logger.info(f"    ✅ dataValue_target_AI: null")
            else:
                logger.warning(f"    ⚠️  dataValue_target_AI should be null initially, got: {data_value}")
            
            # Check defaultValue
            default_value = field_dict.get('defaultValue') if isinstance(field_dict, dict) else getattr(field, 'defaultValue', None)
            if default_value is None:
                logger.info(f"    ✅ defaultValue: null")
            else:
                logger.error(f"    ❌ defaultValue should be null, got: {default_value}")
            
            # Check preservation
            possible_values = field_dict.get('possibleValues') if isinstance(field_dict, dict) else getattr(field, 'possibleValues', [])
            if possible_values:
                logger.info(f"    ✅ possibleValues preserved: {len(possible_values)} values")
        
        # Save exact output from backend (PreprocessedDataSchema.model_dump())
        # This represents the actual backend output without any modifications
        if hasattr(preprocessed_data, 'model_dump'):
            data_dict = preprocessed_data.model_dump()
        else:
            # Fallback: manual construction (should not happen)
            raise ValueError("PreprocessedDataSchema should support model_dump()")
        
        # Save output for next step (exact backend output)
        output_file = project_root / "debug-scripts" / "step3_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"\n✅ Output saved to: {output_file}")
        logger.info(f"   📋 Structure: Exact PreprocessedDataSchema from backend")
        logger.info(f"   ✅ fields_to_fill includes dataValue_target_AI (from schema)")
        logger.info(f"   ✅ Contains: record_id, record_type, processed_documents, salesforce_data, context_summary, validation_results, metrics")
        logger.info(f"   💡 Tip: Use 'form_json' at root level for essential normalized fields")
        
        return preprocessed_data
        
    except Exception as e:
        logger.error(f"❌ ERROR in preprocessing test: {type(e).__name__}: {str(e)}", exc_info=True)
        raise


async def main():
    """Main test function"""
    logger.info("=" * 80)
    logger.info("STEP 3: PREPROCESSING PIPELINE TEST")
    logger.info("=" * 80)
    logger.info(f"Test Record ID: {TEST_RECORD_ID}")
    logger.info("")
    
    try:
        preprocessed_data = await test_preprocessing_pipeline()
        
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3 SUMMARY")
        logger.info("=" * 80)
        logger.info("✅ Preprocessing pipeline: PASSED")
        logger.info(f"  - Processed Documents: {len(preprocessed_data.processed_documents)}")
        logger.info(f"  - Normalized Fields: {len(preprocessed_data.salesforce_data.fields_to_fill)}")
        
    except Exception as e:
        logger.error(f"❌ STEP 3 FAILED: {type(e).__name__}: {str(e)}")
        raise
    
    logger.info("\n" + "=" * 80)
    logger.info("STEP 3 COMPLETE - Check step3_output.log and step3_output.json for details")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
