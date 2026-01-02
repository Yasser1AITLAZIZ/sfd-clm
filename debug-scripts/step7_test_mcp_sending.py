"""
Step 7: Test MCP Sending to LangGraph
Tests sending MCP message to LangGraph service
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
    format='%(asctime)s - %(name)s - %(levelname)s - [STEP7] - %(message)s',
    handlers=[
        logging.FileHandler(project_root / "debug-scripts" / "step7_output.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TEST_RECORD_ID = "001XX000001"


def load_step6_output():
    """Load step 6 output"""
    step6_output = project_root / "debug-scripts" / "step6_output.json"
    if step6_output.exists():
        try:
            with open(step6_output, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load step6 output: {e}")
    return None


async def test_mcp_conversion():
    """Test MCP message to LangGraph format conversion"""
    logger.info("=" * 80)
    logger.info("TESTING: MCP Message to LangGraph Format Conversion")
    logger.info("=" * 80)
    
    try:
        from app.services.mcp.mcp_sender import MCPSender
        from app.models.schemas import MCPMessageSchema
        
        # Load step 6 output
        step6_data = load_step6_output()
        if not step6_data:
            logger.error("❌ Step 6 output not found")
            return None
        
        logger.info("Creating MCPMessageSchema from step 6 output...")
        
        # Create MCPMessageSchema from step 6 data
        mcp_message = MCPMessageSchema(**step6_data)
        
        logger.info("✅ Created MCPMessageSchema")
        logger.info(f"  - Message ID: {mcp_message.message_id}")
        logger.info(f"  - Prompt length: {len(mcp_message.prompt)}")
        logger.info(f"  - Context documents: {len(mcp_message.context.get('documents', []))}")
        logger.info(f"  - Context fields: {len(mcp_message.context.get('fields', []))}")
        
        logger.info("\nConverting to LangGraph format...")
        sender = MCPSender()
        langgraph_format = await sender._convert_mcp_message_to_langgraph_format(mcp_message)
        
        logger.info("✅ Conversion completed")
        logger.info(f"  - Record ID: {langgraph_format.get('record_id', 'N/A')}")
        logger.info(f"  - Session ID: {langgraph_format.get('session_id', 'N/A')}")
        logger.info(f"  - User Request length: {len(langgraph_format.get('user_request', ''))}")
        logger.info(f"  - Documents: {len(langgraph_format.get('documents', []))}")
        logger.info(f"  - Fields Dictionary: {len(langgraph_format.get('fields_dictionary', {}))}")
        
        if not langgraph_format.get('documents'):
            logger.error("  ❌ WARNING: No documents in LangGraph format!")
        
        logger.info("\n  Fields Dictionary:")
        fields_dict = langgraph_format.get('fields_dictionary', {})
        if fields_dict:
            logger.info(f"    - Keys: {list(fields_dict.keys())[:5]}...")
            logger.info(f"    - Total fields: {len(fields_dict)}")
        
        # Save conversion output
        output_file = project_root / "debug-scripts" / "step7_conversion_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(langgraph_format, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"\n✅ Conversion output saved to: {output_file}")
        
        return langgraph_format
        
    except Exception as e:
        logger.error(f"❌ ERROR in conversion test: {type(e).__name__}: {str(e)}", exc_info=True)
        return None


async def test_mcp_sending():
    """Test sending MCP message to LangGraph (requires running service)"""
    logger.info("\n" + "=" * 80)
    logger.info("TESTING: MCP Sending to LangGraph (requires running service)")
    logger.info("=" * 80)
    
    try:
        from app.services.mcp.mcp_sender import MCPSender
        from app.models.schemas import MCPMessageSchema
        from app.core.config import settings
        
        # Load step 6 output
        step6_data = load_step6_output()
        if not step6_data:
            logger.error("❌ Step 6 output not found")
            return None
        
        logger.info(f"LangGraph URL: {getattr(settings, 'langgraph_url', 'NOT SET')}")
        logger.info("Sending MCP message to LangGraph...")
        
        # Create MCPMessageSchema
        mcp_message = MCPMessageSchema(**step6_data)
        
        # Send to LangGraph
        sender = MCPSender()
        result = await sender.send_to_langgraph(mcp_message)
        
        logger.info("✅ Message sent successfully")
        
        # MCPResponseSchema is a Pydantic model, access attributes directly
        message_id = getattr(result, 'message_id', 'N/A')
        status = getattr(result, 'status', 'N/A')
        logger.info(f"  - Message ID: {message_id}")
        logger.info(f"  - Status: {status}")
        
        # Check filled_form_json (NEW - Page-based implementation with per-field quality_score)
        filled_form_json = getattr(result, 'filled_form_json', []) or []
        logger.info(f"\n  - Filled Form JSON (Page-Based Implementation):")
        logger.info(f"    - Total Fields: {len(filled_form_json)}")
        
        if filled_form_json:
            # Check per-field quality_score
            fields_with_quality = [f for f in filled_form_json if f.get("quality_score") is not None]
            fields_without_quality = [f for f in filled_form_json if f.get("quality_score") is None]
            
            logger.info(f"    - Fields with quality_score: {len(fields_with_quality)}/{len(filled_form_json)}")
            if fields_without_quality:
                logger.warning(f"    ⚠️  Fields missing quality_score: {len(fields_without_quality)}")
                logger.warning(f"       Missing: {[f.get('label', 'N/A') for f in fields_without_quality[:5]]}")
            
            # Show sample fields with quality scores
            logger.info(f"\n    - Sample Fields (first 5):")
            for i, field in enumerate(filled_form_json[:5]):
                label = field.get('label', 'N/A')
                data_value = field.get('dataValue_target_AI', 'N/A')
                confidence = field.get('confidence', 'N/A')
                quality_score = field.get('quality_score', 'N/A')
                logger.info(f"      [{i+1}] {label}:")
                logger.info(f"          - dataValue_target_AI: {str(data_value)[:60]}")
                logger.info(f"          - confidence: {confidence}")
                logger.info(f"          - quality_score: {quality_score}")  # NEW: Per-field quality
            
            # Verify quality_score calculation
            if fields_with_quality:
                avg_quality = sum(f.get("quality_score", 0.0) for f in fields_with_quality) / len(fields_with_quality)
                logger.info(f"\n    - Average per-field quality_score: {avg_quality:.4f}")
        
        # Legacy extracted_data (backward compatibility)
        extracted_data = getattr(result, 'extracted_data', {}) or {}
        logger.info(f"\n  - Extracted Data (Legacy - Backward Compatibility):")
        logger.info(f"    - Fields: {len(extracted_data)}")
        if extracted_data:
            logger.info(f"    - Field names: {list(extracted_data.keys())[:5]}...")
        
        confidence_scores = getattr(result, 'confidence_scores', {}) or {}
        logger.info(f"\n  - Confidence Scores:")
        logger.info(f"    - Count: {len(confidence_scores)}")
        
        quality_score = getattr(result, 'quality_score', None)
        if quality_score is not None:
            logger.info(f"\n  - Overall Quality Score: {quality_score:.4f}")
            if filled_form_json:
                field_quality_scores = [f.get("quality_score", 0.0) for f in filled_form_json if f.get("quality_score") is not None]
                if field_quality_scores:
                    expected_avg = sum(field_quality_scores) / len(field_quality_scores)
                    logger.info(f"    - Expected (avg of per-field): {expected_avg:.4f}")
                    if abs(expected_avg - quality_score) < 0.01:
                        logger.info(f"    ✅ Overall quality_score matches average of per-field quality_scores")
                    else:
                        logger.warning(f"    ⚠️  Overall quality_score differs (diff: {abs(expected_avg - quality_score):.4f})")
        
        # Save response - convert Pydantic model to dict for JSON serialization
        if hasattr(result, 'model_dump'):
            result_dict = result.model_dump()
        elif hasattr(result, 'dict'):
            result_dict = result.dict()
        else:
            # Fallback: manually extract attributes
            result_dict = {
                'message_id': message_id,
                'status': status,
                'filled_form_json': filled_form_json,  # NEW: Primary format
                'extracted_data': extracted_data,  # Legacy: backward compatibility
                'confidence_scores': confidence_scores,
                'quality_score': quality_score,
                'error': getattr(result, 'error', None)
            }
        
        output_file = project_root / "debug-scripts" / "step7_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"\n✅ Response saved to: {output_file}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ ERROR in sending test: {type(e).__name__}: {str(e)}", exc_info=True)
        return None


async def main():
    """Main test function"""
    logger.info("=" * 80)
    logger.info("STEP 7: MCP SENDING TO LANGGRAPH TEST")
    logger.info("=" * 80)
    logger.info(f"Test Record ID: {TEST_RECORD_ID}")
    logger.info("")
    
    # Test 1: Conversion
    langgraph_format = await test_mcp_conversion()
    
    # Test 2: Sending (requires service)
    result = await test_mcp_sending()
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("STEP 7 SUMMARY")
    logger.info("=" * 80)
    
    if langgraph_format:
        logger.info("✅ Message conversion: PASSED")
        logger.info(f"    - Documents: {len(langgraph_format.get('documents', []))}")
        logger.info(f"    - Fields Dictionary: {len(langgraph_format.get('fields_dictionary', {}))}")
        if not langgraph_format.get('documents'):
            logger.error("    ⚠️  WARNING: No documents in LangGraph format!")
    else:
        logger.error("❌ Message conversion: FAILED")
    
    if result:
        logger.info("✅ MCP sending: PASSED")
        # result is MCPResponseSchema (Pydantic model), use getattr
        filled_form_json = getattr(result, 'filled_form_json', []) or []
        extracted_data = getattr(result, 'extracted_data', {}) or {}
        quality_score = getattr(result, 'quality_score', None)
        
        logger.info(f"    - Filled Form JSON Fields: {len(filled_form_json)}")
        if filled_form_json:
            fields_with_quality = [f for f in filled_form_json if f.get("quality_score") is not None]
            logger.info(f"    - Fields with quality_score: {len(fields_with_quality)}/{len(filled_form_json)}")
        logger.info(f"    - Extracted Data Fields (Legacy): {len(extracted_data)}")
        if quality_score is not None:
            logger.info(f"    - Overall Quality Score: {quality_score:.4f}")
    else:
        logger.warning("⚠️  MCP sending: SKIPPED (service not running or error)")
    
    logger.info("\n" + "=" * 80)
    logger.info("STEP 7 COMPLETE - Check step7_output.log for details")
    logger.info("=" * 80)
    logger.info("\n🔍 ROOT CAUSE ANALYSIS:")
    logger.info("If fields_dictionary is empty in step 7, trace back:")
    logger.info("  1. Check step 6: Are fields in MCP message context?")
    logger.info("  2. Check step 3: Does fields_dictionary.fields exist?")
    logger.info("  3. Check step 2: Was field conversion successful?")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

