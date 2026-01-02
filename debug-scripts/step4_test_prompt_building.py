"""
Step 4: Test Prompt Building
Tests prompt construction from preprocessed data with form_json
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
    format='%(asctime)s - %(name)s - %(levelname)s - [STEP4] - %(message)s',
    handlers=[
        logging.FileHandler(project_root / "debug-scripts" / "step4_output.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TEST_RECORD_ID = "001XX000001"


def load_step3_output():
    """Load step 3 output"""
    step3_output = project_root / "debug-scripts" / "step3_output.json"
    if not step3_output.exists():
        raise FileNotFoundError(
            f"Step 3 output not found: {step3_output}\n"
            "Please run step3_test_preprocessing_pipeline.py first"
        )
    try:
        with open(step3_output, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Could not load step3 output: {e}")


async def test_prompt_building():
    """Test prompt building"""
    logger.info("=" * 80)
    logger.info("TESTING: Prompt Building")
    logger.info("=" * 80)
    
    try:
        from app.services.prompting.prompt_builder import PromptBuilder
        from app.models.schemas import PreprocessedDataSchema
        
        # Load step 3 output
        step3_data = load_step3_output()
        
        # Convert to PreprocessedDataSchema
        try:
            preprocessed_data = PreprocessedDataSchema(**step3_data)
        except Exception as e:
            raise ValueError(f"Could not create PreprocessedDataSchema: {e}")
        
        # Extract data from nested structure
        record_id = preprocessed_data.record_id
        record_type = preprocessed_data.record_type
        processed_documents = preprocessed_data.processed_documents
        salesforce_data = preprocessed_data.salesforce_data
        fields_to_fill = salesforce_data.fields_to_fill
        
        logger.info(f"Building prompt for:")
        logger.info(f"  - Record ID: {record_id}")
        logger.info(f"  - Record Type: {record_type}")
        logger.info(f"  - Documents: {len(processed_documents)}")
        logger.info(f"  - Fields to Fill: {len(fields_to_fill)}")
        
        # Verify fields structure (now with dataValue_target_AI)
        logger.info("\n--- Fields Structure Verification ---")
        for i, field in enumerate(fields_to_fill[:3], 1):  # Show first 3
            logger.info(f"\n  Field {i}:")
            # Handle both Pydantic models and dicts
            if hasattr(field, 'model_dump'):
                field_dict = field.model_dump()
                logger.info(f"    - Label: {field.label}")
                logger.info(f"    - Type: {field.type}")
                logger.info(f"    - dataValue_target_AI: {field_dict.get('dataValue_target_AI', 'N/A')}")
                logger.info(f"    - defaultValue: {field_dict.get('defaultValue', 'N/A')}")
            elif isinstance(field, dict):
                logger.info(f"    - Label: {field.get('label', 'N/A')}")
                logger.info(f"    - Type: {field.get('type', 'N/A')}")
                logger.info(f"    - dataValue_target_AI: {field.get('dataValue_target_AI', 'N/A')}")
                logger.info(f"    - defaultValue: {field.get('defaultValue', 'N/A')}")
            else:
                logger.info(f"    - Field object: {type(field).__name__}")
        
        prompt_builder = PromptBuilder()
        
        # Build prompt using the correct method signature
        # Use build_prompt (wrapper method used by workflow orchestrator)
        user_message = "Remplis tous les champs manquants"
        prompt_result = await prompt_builder.build_prompt(
            user_message=user_message,
            preprocessed_data=preprocessed_data,
            routing_status="initialization"
        )
        
        # Extract prompt from result
        if isinstance(prompt_result, dict):
            prompt = prompt_result.get("prompt", "")
            scenario_type = prompt_result.get("scenario_type", "initialization")
        else:
            # If it's a PromptResponseSchema object
            prompt = getattr(prompt_result, 'prompt', str(prompt_result))
            scenario_type = getattr(prompt_result, 'scenario_type', "initialization")
        
        logger.info("\n✅ Prompt built successfully")
        logger.info(f"  - Prompt length: {len(prompt)} characters")
        logger.info(f"  - Estimated tokens: ~{len(prompt) // 4}")
        logger.info(f"  - Scenario type: {scenario_type}")
        
        # Check if form_json is embedded in prompt
        if "form_json" in prompt.lower() or '"dataValue_target_AI"' in prompt:
            logger.info("  ✅ form_json appears to be embedded in prompt")
        else:
            logger.warning("  ⚠️  form_json might not be embedded in prompt")
        
        # Show a snippet of the prompt
        logger.info("\n--- Prompt Snippet (first 500 chars) ---")
        logger.info(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        
        # Save output
        output_data = {
            "prompt": prompt,
            "scenario_type": scenario_type,
            "metadata": {
                "record_id": record_id,
                "record_type": record_type,
                "documents_count": len(processed_documents),
                "fields_count": len(fields_to_fill),
                "prompt_length": len(prompt),
                "estimated_tokens": len(prompt) // 4
            }
        }
        
        output_file = project_root / "debug-scripts" / "step4_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"\n✅ Output saved to: {output_file}")
        
        return prompt_result
        
    except Exception as e:
        logger.error(f"❌ ERROR in prompt building test: {type(e).__name__}: {str(e)}", exc_info=True)
        raise


async def main():
    """Main test function"""
    logger.info("=" * 80)
    logger.info("STEP 4: PROMPT BUILDING TEST")
    logger.info("=" * 80)
    logger.info(f"Test Record ID: {TEST_RECORD_ID}")
    logger.info("")
    
    try:
        prompt_result = await test_prompt_building()
        
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4 SUMMARY")
        logger.info("=" * 80)
        logger.info("✅ Prompt building: PASSED")
        
    except Exception as e:
        logger.error(f"❌ STEP 4 FAILED: {type(e).__name__}: {str(e)}")
        raise
    
    logger.info("\n" + "=" * 80)
    logger.info("STEP 4 COMPLETE - Check step4_output.log and step4_output.json for details")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
