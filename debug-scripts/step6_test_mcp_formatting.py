"""
Step 6: Test MCP Message Formatting
Tests MCP message formatting with documents and fields
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
    if step3_output.exists():
        try:
            with open(step3_output, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load step3 output: {e}")
    return None


def load_step5_output():
    """Load step 5 output"""
    step5_output = project_root / "debug-scripts" / "step5_output.json"
    if step5_output.exists():
        try:
            with open(step5_output, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load step5 output: {e}")
    return None


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


def extract_fields_from_preprocessed_data(preprocessed_data: any) -> list:
    """Helper function to extract fields"""
    if not preprocessed_data:
        return []
    
    if hasattr(preprocessed_data, 'model_dump'):
        data = preprocessed_data.model_dump()
    elif isinstance(preprocessed_data, dict):
        data = preprocessed_data
    else:
        if hasattr(preprocessed_data, 'fields_dictionary'):
            fields_dict = preprocessed_data.fields_dictionary
            if hasattr(fields_dict, 'fields'):
                return fields_dict.fields
            elif isinstance(fields_dict, dict):
                return fields_dict.get("fields", [])
        return []
    
    fields_dictionary = data.get("fields_dictionary", {})
    if isinstance(fields_dictionary, dict):
        return fields_dictionary.get("fields", [])
    elif hasattr(fields_dictionary, 'fields'):
        return fields_dictionary.fields
    
    return []


async def test_mcp_message_formatter():
    """Test MCP message formatting"""
    logger.info("=" * 80)
    logger.info("TESTING: MCP Message Formatting")
    logger.info("=" * 80)
    
    try:
        from app.services.mcp.mcp_message_formatter import MCPMessageFormatter
        from datetime import datetime
        
        # Load step 5 output (optimized prompt)
        step5_data = load_step5_output()
        if not step5_data:
            logger.error("❌ Step 5 output not found - cannot test formatting")
            return None
        
        optimized_prompt = step5_data.get("prompt", "")
        if not optimized_prompt:
            logger.error("❌ No prompt found in step 5 output")
            return None
        
        logger.info(f"Optimized prompt length: {len(optimized_prompt)} characters")
        
        # Load step 3 output (for context)
        step3_data = load_step3_output()
        if not step3_data:
            logger.error("❌ Step 3 output not found - cannot get context")
            return None
        
        # Extract fields and documents using helper functions
        logger.info("\nExtracting fields and documents from preprocessed data...")
        fields = extract_fields_from_preprocessed_data(step3_data)
        documents = extract_documents_from_preprocessed_data(step3_data)
        
        logger.info(f"  - Fields extracted: {len(fields)}")
        logger.info(f"  - Documents extracted: {len(documents)}")
        
        if not fields:
            logger.error("  ❌ WARNING: No fields extracted! This will cause problems!")
            logger.error("     Check if fields_dictionary.fields exists in step3 output")
        
        if not documents:
            logger.warning("  ⚠️  WARNING: No documents extracted!")
        
        # Prepare context
        context = {
            "documents": documents,
            "fields": fields,
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
            prompt=optimized_prompt,
            context=context,
            metadata=metadata
        )
        
        logger.info("✅ MCP message formatted successfully")
        logger.info(f"  - Message ID: {mcp_message.message_id}")
        logger.info(f"  - Prompt length: {len(mcp_message.prompt)} characters")
        
        # Check context
        if hasattr(mcp_message, 'context') and mcp_message.context:
            context_docs = mcp_message.context.get("documents", []) if isinstance(mcp_message.context, dict) else []
            context_fields = mcp_message.context.get("fields", []) if isinstance(mcp_message.context, dict) else []
            logger.info(f"  - Context documents: {len(context_docs)}")
            logger.info(f"  - Context fields: {len(context_fields)}")
            
            if not context_docs:
                logger.error("  ❌ WARNING: No documents in MCP message context!")
            if not context_fields:
                logger.error("  ❌ WARNING: No fields in MCP message context!")
        
        # Check metadata
        if hasattr(mcp_message, 'metadata') and mcp_message.metadata:
            logger.info(f"  - Metadata record_id: {mcp_message.metadata.record_id if hasattr(mcp_message.metadata, 'record_id') else 'N/A'}")
        
        # Save output
        if hasattr(mcp_message, 'model_dump'):
            data_dict = mcp_message.model_dump()
        else:
            data_dict = {
                "message_id": getattr(mcp_message, 'message_id', None),
                "prompt": getattr(mcp_message, 'prompt', None),
                "context": mcp_message.context if hasattr(mcp_message, 'context') else {},
                "metadata": mcp_message.metadata.__dict__ if hasattr(mcp_message, 'metadata') and hasattr(mcp_message.metadata, '__dict__') else {}
            }
        
        output_file = project_root / "debug-scripts" / "step6_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"\n✅ Output saved to: {output_file}")
        
        return mcp_message
        
    except Exception as e:
        logger.error(f"❌ ERROR in MCP formatting: {type(e).__name__}: {str(e)}", exc_info=True)
        return None


async def test_document_serialization():
    """Test document serialization for MCP"""
    logger.info("\n" + "=" * 80)
    logger.info("TESTING: Document Serialization")
    logger.info("=" * 80)
    
    try:
        from app.services.mcp.mcp_message_formatter import MCPMessageFormatter
        
        # Load step 3 output
        step3_data = load_step3_output()
        if not step3_data:
            logger.error("❌ Step 3 output not found")
            return None
        
        documents = extract_documents_from_preprocessed_data(step3_data)
        logger.info(f"Serializing {len(documents)} documents...")
        
        formatter = MCPMessageFormatter()
        serialized = formatter.serialize_documents_for_mcp(documents)
        
        logger.info(f"✅ Serialized {len(serialized)} documents")
        for i, doc in enumerate(serialized, 1):
            logger.info(f"  Document {i}:")
            if isinstance(doc, dict):
                logger.info(f"    - ID: {doc.get('document_id', doc.get('id', 'N/A'))}")
                logger.info(f"    - Name: {doc.get('name', 'N/A')}")
                logger.info(f"    - URL: {doc.get('url', 'N/A')}")
                logger.info(f"    - Keys: {list(doc.keys())}")
            else:
                logger.info(f"    - Type: {type(doc).__name__}")
        
        return serialized
        
    except Exception as e:
        logger.error(f"❌ ERROR in document serialization: {type(e).__name__}: {str(e)}", exc_info=True)
        return None


async def main():
    """Main test function"""
    logger.info("=" * 80)
    logger.info("STEP 6: MCP FORMATTING TEST")
    logger.info("=" * 80)
    logger.info(f"Test Record ID: {TEST_RECORD_ID}")
    logger.info("")
    
    # Step 6.1: Test document serialization
    serialized_docs = await test_document_serialization()
    
    # Step 6.2: Test MCP message formatting
    mcp_message = await test_mcp_message_formatter()
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("STEP 6 SUMMARY")
    logger.info("=" * 80)
    
    if serialized_docs:
        logger.info(f"✅ Document serialization: PASSED ({len(serialized_docs)} documents)")
    else:
        logger.error("❌ Document serialization: FAILED")
    
    if mcp_message:
        logger.info("✅ MCP message formatting: PASSED")
        # Check if context has data
        if hasattr(mcp_message, 'context') and mcp_message.context:
            context_docs = mcp_message.context.get("documents", []) if isinstance(mcp_message.context, dict) else []
            context_fields = mcp_message.context.get("fields", []) if isinstance(mcp_message.context, dict) else []
            if not context_docs:
                logger.error("   ⚠️  WARNING: No documents in MCP message!")
            if not context_fields:
                logger.error("   ⚠️  WARNING: No fields in MCP message!")
                logger.error("   This will cause the graph to receive null data!")
    else:
        logger.error("❌ MCP message formatting: FAILED")
    
    logger.info("\n" + "=" * 80)
    logger.info("STEP 6 COMPLETE - Check step6_output.log and step6_output.json for details")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

