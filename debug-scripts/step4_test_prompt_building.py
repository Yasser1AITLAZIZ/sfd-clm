"""
Step 4: Test Prompt Building
Tests prompt construction from preprocessed data
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
    if step3_output.exists():
        try:
            with open(step3_output, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load step3 output: {e}")
    return None


async def test_prompt_building():
    """Test prompt building"""
    logger.info("=" * 80)
    logger.info("TESTING: Prompt Building")
    logger.info("=" * 80)
    
    try:
        from app.services.prompting.prompt_builder import PromptBuilder
        
        # Load step 3 output
        step3_data = load_step3_output()
        if not step3_data:
            logger.error("❌ Step 3 output not found")
            return None
        
        prompt_builder = PromptBuilder()
        
        # Extract data
        record_id = step3_data.get("record_id", TEST_RECORD_ID)
        record_type = step3_data.get("record_type", "Claim")
        processed_documents = step3_data.get("processed_documents", [])
        fields_dictionary = step3_data.get("fields_dictionary", {})
        fields = fields_dictionary.get("fields", []) if isinstance(fields_dictionary, dict) else []
        
        logger.info(f"Building prompt for:")
        logger.info(f"  - Record ID: {record_id}")
        logger.info(f"  - Record Type: {record_type}")
        logger.info(f"  - Documents: {len(processed_documents)}")
        logger.info(f"  - Fields: {len(fields)}")
        
        # Build prompt using the correct method signature
        user_message = "Remplis tous les champs manquants"
        prompt_result = await prompt_builder.build_prompt(
            user_message=user_message,
            preprocessed_data=step3_data,  # Pass the full preprocessed_data dict
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
        
        logger.info("✅ Prompt built successfully")
        logger.info(f"  - Prompt length: {len(prompt)} characters")
        logger.info(f"  - Estimated tokens: ~{len(prompt) // 4}")
        
        # Save output
        output_data = {
            "prompt": prompt,
            "scenario_type": scenario_type,
            "metadata": {
                "record_id": record_id,
                "record_type": record_type,
                "prompt_length": len(prompt),
                "estimated_tokens": len(prompt) // 4,
                "documents_count": len(processed_documents),
                "fields_count": len(fields)
            }
        }
        
        output_file = project_root / "debug-scripts" / "step4_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"\n✅ Output saved to: {output_file}")
        
        return prompt
        
    except Exception as e:
        logger.error(f"❌ ERROR in prompt building test: {type(e).__name__}: {str(e)}", exc_info=True)
        return None


async def main():
    """Main test function"""
    logger.info("=" * 80)
    logger.info("STEP 4: PROMPT BUILDING TEST")
    logger.info("=" * 80)
    logger.info(f"Test Record ID: {TEST_RECORD_ID}")
    logger.info("")
    
    prompt = await test_prompt_building()
    
    logger.info("\n" + "=" * 80)
    logger.info("STEP 4 SUMMARY")
    logger.info("=" * 80)
    
    if prompt:
        logger.info("✅ Prompt building: PASSED")
        logger.info(f"  - Prompt length: {len(prompt)} characters")
    else:
        logger.error("❌ Prompt building: FAILED")
    
    logger.info("\n" + "=" * 80)
    logger.info("STEP 4 COMPLETE - Check step4_output.log and step4_output.json for details")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

