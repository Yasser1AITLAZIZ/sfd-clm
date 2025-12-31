"""
Step 3: Test Preprocessing Pipeline
Tests document and field preprocessing
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
    if step2_output.exists():
        try:
            with open(step2_output, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load step2 output: {e}")
    return None


async def test_preprocessing_pipeline():
    """Test preprocessing pipeline"""
    logger.info("=" * 80)
    logger.info("TESTING: Preprocessing Pipeline")
    logger.info("=" * 80)
    
    try:
        from app.services.preprocessing.preprocessing_pipeline import PreprocessingPipeline
        from app.models.schemas import SalesforceDataResponseSchema, DocumentResponseSchema, FieldToFillResponseSchema
        
        # Load step 2 output
        step2_data = load_step2_output()
        if not step2_data:
            logger.error("❌ Step 2 output not found")
            return None
        
        # Convert to schema
        salesforce_data_dict = step2_data
        try:
            salesforce_data = SalesforceDataResponseSchema(**salesforce_data_dict)
        except Exception as e:
            logger.warning(f"Could not create schema object, using dict: {e}")
            salesforce_data = salesforce_data_dict
        
        logger.info(f"Input data:")
        logger.info(f"  - Record ID: {salesforce_data_dict.get('record_id', 'N/A')}")
        logger.info(f"  - Documents: {len(salesforce_data_dict.get('documents', []))}")
        logger.info(f"  - Fields to Fill: {len(salesforce_data_dict.get('fields_to_fill', []))}")
        
        pipeline = PreprocessingPipeline()
        preprocessed_data = await pipeline.execute_preprocessing(salesforce_data)
        
        logger.info("✅ Preprocessing completed")
        logger.info(f"  - Record ID: {preprocessed_data.record_id if hasattr(preprocessed_data, 'record_id') else 'N/A'}")
        logger.info(f"  - Record Type: {preprocessed_data.record_type if hasattr(preprocessed_data, 'record_type') else 'N/A'}")
        logger.info(f"  - Processed Documents: {len(preprocessed_data.processed_documents) if hasattr(preprocessed_data, 'processed_documents') and preprocessed_data.processed_documents else 0}")
        
        # Check fields_dictionary
        fields_dict = preprocessed_data.fields_dictionary if hasattr(preprocessed_data, 'fields_dictionary') else None
        if fields_dict:
            fields_count = len(fields_dict.fields) if hasattr(fields_dict, 'fields') and fields_dict.fields else 0
            logger.info(f"  - Fields Dictionary Fields: {fields_count}")
        else:
            logger.error("  ❌ Fields Dictionary is None!")
        
        # Convert to dict for saving
        if hasattr(preprocessed_data, 'model_dump'):
            data_dict = preprocessed_data.model_dump()
        else:
            data_dict = {
                "record_id": getattr(preprocessed_data, 'record_id', None),
                "record_type": getattr(preprocessed_data, 'record_type', None),
                "processed_documents": [doc.__dict__ if hasattr(doc, '__dict__') else str(doc) for doc in (getattr(preprocessed_data, 'processed_documents', []) or [])],
                "fields_dictionary": fields_dict.__dict__ if fields_dict and hasattr(fields_dict, '__dict__') else None
            }
        
        # Save output for next step
        output_file = project_root / "debug-scripts" / "step3_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"\n✅ Output saved to: {output_file}")
        
        return preprocessed_data
        
    except Exception as e:
        logger.error(f"❌ ERROR in preprocessing test: {type(e).__name__}: {str(e)}", exc_info=True)
        return None


async def main():
    """Main test function"""
    logger.info("=" * 80)
    logger.info("STEP 3: PREPROCESSING PIPELINE TEST")
    logger.info("=" * 80)
    logger.info(f"Test Record ID: {TEST_RECORD_ID}")
    logger.info("")
    
    preprocessed_data = await test_preprocessing_pipeline()
    
    logger.info("\n" + "=" * 80)
    logger.info("STEP 3 SUMMARY")
    logger.info("=" * 80)
    
    if preprocessed_data:
        logger.info("✅ Preprocessing pipeline: PASSED")
    else:
        logger.error("❌ Preprocessing pipeline: FAILED")
    
    logger.info("\n" + "=" * 80)
    logger.info("STEP 3 COMPLETE - Check step3_output.log and step3_output.json for details")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

