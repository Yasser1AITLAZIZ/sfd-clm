"""
Step 6: Test MCP Message Formatting
Tests MCP message formatting with documents and form_json
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
    format='%(asctime)s - %(name)s - %(levelname)s - [STEP6] - %(message)s',
    handlers=[
        logging.FileHandler(project_root / "debug-scripts" / "step6_output.log", encoding='utf-8'),
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


def load_step4_output():
    """Load step 4 output"""
    step4_output = project_root / "debug-scripts" / "step4_output.json"
    if not step4_output.exists():
        raise FileNotFoundError(
            f"Step 4 output not found: {step4_output}\n"
            "Please run step4_test_prompt_building.py first"
        )
    try:
        with open(step4_output, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Could not load step4 output: {e}")


def extract_documents_from_preprocessed_data(preprocessed_data: any) -> list:
    """Helper function to extract documents (same as in workflow_orchestrator)"""
    if not preprocessed_data:
        return []
    
    if hasattr(preprocessed_data, 'model_dump'):
        data = preprocessed_data.model_dump()
    elif isinstance(preprocessed_data, dict):
        data = preprocessed_data
    else:
        if hasattr(preprocessed_data, 'processed_documents'):
            return preprocessed_data.processed_documents
        return []
    
    return data.get("processed_documents", [])


def extract_form_json_from_preprocessed_data(preprocessed_data: any) -> list:
    """Helper function to extract form_json from salesforce_data.fields_to_fill"""
    if not preprocessed_data:
        return []
    
    if hasattr(preprocessed_data, 'model_dump'):
        data = preprocessed_data.model_dump()
    elif isinstance(preprocessed_data, dict):
        data = preprocessed_data
    else:
        # Try to access directly
        if hasattr(preprocessed_data, 'salesforce_data'):
            salesforce_data = preprocessed_data.salesforce_data
            if hasattr(salesforce_data, 'fields_to_fill'):
                return salesforce_data.fields_to_fill
        return []
    
    # Extract from nested structure
    salesforce_data = data.get("salesforce_data", {})
    if isinstance(salesforce_data, dict):
        return salesforce_data.get("fields_to_fill", [])
    elif hasattr(salesforce_data, 'fields_to_fill'):
        return salesforce_data.fields_to_fill
    
    return []


async def test_mcp_message_formatter():
    """Test MCP message formatting"""
    logger.info("=" * 80)
    logger.info("TESTING: MCP Message Formatting")
    logger.info("=" * 80)
    
    try:
        from app.services.mcp.mcp_message_formatter import MCPMessageFormatter
        from datetime import datetime
        
        # Load step 4 output (prompt)
        step4_data = load_step4_output()
        prompt = step4_data.get("prompt", "")
        if not prompt:
            raise ValueError("No prompt found in step 4 output")
        
        logger.info(f"Prompt length: {len(prompt)} characters")
        
        # Load step 3 output (for context)
        step3_data = load_step3_output()
        
        # Extract form_json and documents using helper functions
        logger.info("\nExtracting form_json and documents from preprocessed data...")
        form_json = extract_form_json_from_preprocessed_data(step3_data)
        documents = extract_documents_from_preprocessed_data(step3_data)
        
        logger.info(f"  - Form JSON fields extracted: {len(form_json)}")
        logger.info(f"  - Documents extracted: {len(documents)}")
        
        if not form_json:
            raise ValueError("No form_json extracted! Check if salesforce_data.fields_to_fill exists in step3 output")
        
        if not documents:
            logger.warning("  ⚠️  WARNING: No documents extracted!")
        
        # Verify form_json structure
        logger.info("\n--- Form JSON Structure Verification ---")
        for i, field in enumerate(form_json[:3], 1):  # Show first 3
            logger.info(f"\n  Field {i}:")
            if isinstance(field, dict):
                logger.info(f"    - Label: {field.get('label', 'N/A')}")
                logger.info(f"    - Type: {field.get('type', 'N/A')}")
                logger.info(f"    - dataValue_target_AI: {field.get('dataValue_target_AI', 'N/A')}")
                logger.info(f"    - defaultValue: {field.get('defaultValue', 'N/A')}")
            else:
                logger.info(f"    - Field object: {type(field).__name__}")
        
        # Prepare context (new architecture: form_json instead of fields)
        context = {
            "documents": documents,
            "form_json": form_json,  # New architecture: form_json
            "session_id": None
        }
        
        # Prepare metadata
        metadata = {
            "record_id": TEST_RECORD_ID,
            "record_type": step3_data.get("record_type", "Claim"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info("\nFormatting MCP message...")
        formatter = MCPMessageFormatter()
        mcp_message = formatter.format_message(
            prompt=prompt,
            context=context,
            metadata=metadata
        )
        
        logger.info("✅ MCP message formatted successfully")
        logger.info(f"  - Message ID: {mcp_message.message_id}")
        logger.info(f"  - Prompt length: {len(mcp_message.prompt)} characters")
        
        # Check context
        if hasattr(mcp_message, 'context') and mcp_message.context:
            context_data = mcp_message.context
            logger.info(f"  - Context keys: {list(context_data.keys())}")
            
            # Check form_json in context
            if "form_json" in context_data:
                form_json_in_context = context_data["form_json"]
                logger.info(f"  - Form JSON in context: {len(form_json_in_context)} fields")
                
                # Verify normalization
                for field in form_json_in_context[:2]:  # Check first 2
                    if isinstance(field, dict):
                        if field.get("dataValue_target_AI") is not None:
                            logger.warning(f"    ⚠️  Field has non-null dataValue_target_AI: {field.get('dataValue_target_AI')}")
                        if field.get("defaultValue") is not None:
                            logger.warning(f"    ⚠️  Field has non-null defaultValue: {field.get('defaultValue')}")
            else:
                logger.warning("  ⚠️  form_json not found in context!")
        else:
            logger.warning("  ⚠️  Context is empty or missing!")
        
        # Save output
        # Convert Pydantic models to dicts for JSON serialization
        metadata_dict = {}
        if hasattr(mcp_message, 'metadata') and mcp_message.metadata:
            if hasattr(mcp_message.metadata, 'model_dump'):
                metadata_dict = mcp_message.metadata.model_dump()
            elif isinstance(mcp_message.metadata, dict):
                metadata_dict = mcp_message.metadata
            else:
                # Fallback: try to convert to dict
                metadata_dict = dict(mcp_message.metadata) if hasattr(mcp_message.metadata, '__dict__') else {}
        
        context_dict = {}
        if hasattr(mcp_message, 'context') and mcp_message.context:
            if isinstance(mcp_message.context, dict):
                context_dict = mcp_message.context
            else:
                # If it's a Pydantic model, convert it
                context_dict = mcp_message.context.model_dump() if hasattr(mcp_message.context, 'model_dump') else {}
        
        output_data = {
            "message_id": mcp_message.message_id,
            "prompt": mcp_message.prompt,
            "context": context_dict,
            "metadata": metadata_dict,  # Now a dict, not a string
            "metadata_info": {
                "record_id": TEST_RECORD_ID,
                "record_type": step3_data.get("record_type", "Claim"),
                "form_json_fields_count": len(form_json),
                "documents_count": len(documents)
            }
        }
        
        output_file = project_root / "debug-scripts" / "step6_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"\n✅ Output saved to: {output_file}")
        
        return mcp_message
        
    except Exception as e:
        logger.error(f"❌ ERROR in MCP formatting test: {type(e).__name__}: {str(e)}", exc_info=True)
        raise


async def main():
    """Main test function"""
    logger.info("=" * 80)
    logger.info("STEP 6: MCP MESSAGE FORMATTING TEST")
    logger.info("=" * 80)
    logger.info(f"Test Record ID: {TEST_RECORD_ID}")
    logger.info("")
    
    try:
        mcp_message = await test_mcp_message_formatter()
        
        logger.info("\n" + "=" * 80)
        logger.info("STEP 6 SUMMARY")
        logger.info("=" * 80)
        logger.info("✅ MCP message formatting: PASSED")
        logger.info(f"  - Message ID: {mcp_message.message_id}")
        logger.info(f"  - Form JSON fields: {len(mcp_message.context.get('form_json', []))}")
        
    except Exception as e:
        logger.error(f"❌ STEP 6 FAILED: {type(e).__name__}: {str(e)}")
        raise
    
    logger.info("\n" + "=" * 80)
    logger.info("STEP 6 COMPLETE - Check step6_output.log and step6_output.json for details")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
