"""
Step 5: Test Prompt Optimization
Tests prompt optimization
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
    format='%(asctime)s - %(name)s - %(levelname)s - [STEP5] - %(message)s',
    handlers=[
        logging.FileHandler(project_root / "debug-scripts" / "step5_output.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TEST_RECORD_ID = "001XX000001"


def load_step4_output():
    """Load step 4 output"""
    step4_output = project_root / "debug-scripts" / "step4_output.json"
    if step4_output.exists():
        try:
            with open(step4_output, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load step4 output: {e}")
    return None


async def test_prompt_optimization():
    """Test prompt optimization"""
    logger.info("=" * 80)
    logger.info("TESTING: Prompt Optimization")
    logger.info("=" * 80)
    
    try:
        from app.services.prompting.prompt_optimizer import PromptOptimizer
        
        # Load step 4 output
        step4_data = load_step4_output()
        if not step4_data:
            logger.error("❌ Step 4 output not found")
            return None
        
        prompt = step4_data.get("prompt", "")
        if not prompt:
            logger.error("❌ No prompt found in step 4 output")
            return None
        
        logger.info(f"Original prompt length: {len(prompt)} characters")
        
        optimizer = PromptOptimizer()
        
        # Use optimize() method which returns OptimizedPromptSchema with all metadata
        from app.models.schemas import PromptResponseSchema
        
        prompt_response = PromptResponseSchema(
            prompt=prompt,
            scenario_type=step4_data.get("scenario_type", "initialization"),
            metadata=step4_data.get("metadata", {})
        )
        
        optimized_result = await optimizer.optimize(prompt_response)
        
        logger.info("✅ Prompt optimized")
        logger.info(f"  - Original length: {optimized_result.original_length}")
        logger.info(f"  - Optimized length: {optimized_result.optimized_length}")
        logger.info(f"  - Tokens estimated: {optimized_result.tokens_estimated}")
        logger.info(f"  - Quality score: {optimized_result.quality_score}")
        logger.info(f"  - Optimizations applied: {len(optimized_result.optimizations_applied) if optimized_result.optimizations_applied else 0}")
        
        # Save output
        output_data = {
            "prompt": optimized_result.prompt if optimized_result.prompt else prompt,
            "original_length": optimized_result.original_length,
            "optimized_length": optimized_result.optimized_length,
            "tokens_estimated": optimized_result.tokens_estimated,
            "quality_score": optimized_result.quality_score,
            "optimizations_applied": optimized_result.optimizations_applied if optimized_result.optimizations_applied else [],
            "cost_estimated": optimized_result.cost_estimated if hasattr(optimized_result, 'cost_estimated') else None
        }
        
        output_file = project_root / "debug-scripts" / "step5_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"\n✅ Output saved to: {output_file}")
        
        return optimized_result
        
    except Exception as e:
        logger.error(f"❌ ERROR in prompt optimization test: {type(e).__name__}: {str(e)}", exc_info=True)
        return None


async def main():
    """Main test function"""
    logger.info("=" * 80)
    logger.info("STEP 5: PROMPT OPTIMIZATION TEST")
    logger.info("=" * 80)
    logger.info(f"Test Record ID: {TEST_RECORD_ID}")
    logger.info("")
    
    optimized_result = await test_prompt_optimization()
    
    logger.info("\n" + "=" * 80)
    logger.info("STEP 5 SUMMARY")
    logger.info("=" * 80)
    
    if optimized_result:
        logger.info("✅ Prompt optimization: PASSED")
        logger.info(f"  - Length reduction: {optimized_result.original_length - optimized_result.optimized_length} characters")
    else:
        logger.error("❌ Prompt optimization: FAILED")
    
    logger.info("\n" + "=" * 80)
    logger.info("STEP 5 COMPLETE - Check step5_output.log and step5_output.json for details")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

