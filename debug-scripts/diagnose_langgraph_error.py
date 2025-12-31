"""
Script de diagnostic pour identifier l'erreur dans le service LangGraph
"""
import sys
import json
import logging
import asyncio
import httpx
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend-mcp"))

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def diagnose_langgraph_error():
    """Diagnostiquer l'erreur dans le service LangGraph"""
    logger.info("=" * 80)
    logger.info("DIAGNOSTIC: Erreur LangGraph Service")
    logger.info("=" * 80)
    
    # Try to load step7_conversion_output.json (already in LangGraph format)
    conversion_output = project_root / "debug-scripts" / "step7_conversion_output.json"
    step6_output = project_root / "debug-scripts" / "step6_output.json"
    
    langgraph_format = None
    
    # Prefer step7_conversion_output.json as it's already in LangGraph format
    if conversion_output.exists():
        logger.info(f"Loading step7_conversion_output.json (already in LangGraph format)...")
        with open(conversion_output, 'r', encoding='utf-8') as f:
            langgraph_format = json.load(f)
        logger.info("✅ Step 7 conversion data loaded (already in LangGraph format)")
    elif step6_output.exists():
        logger.info("Loading step6_output.json and converting to LangGraph format...")
        with open(step6_output, 'r', encoding='utf-8') as f:
            step6_data = json.load(f)
        
        logger.info("✅ Step 6 data loaded")
        
        # Convert to LangGraph format (simulate what mcp_sender does)
        from app.services.mcp.mcp_sender import MCPSender
        from app.models.schemas import MCPMessageSchema
        
        logger.info("\n1. Creating MCPMessageSchema...")
        mcp_message = MCPMessageSchema(**step6_data)
        logger.info("✅ MCPMessageSchema created")
        
        logger.info("\n2. Converting to LangGraph format...")
        sender = MCPSender()
        langgraph_format = await sender._convert_mcp_message_to_langgraph_format(mcp_message)
        logger.info("✅ Converted to LangGraph format")
    else:
        logger.error(f"❌ Neither step6_output.json nor step7_conversion_output.json found")
        logger.info("   Please run step6_test_mcp_formatting.py or step7_test_mcp_sending.py first")
        return
    
    if langgraph_format:
        logger.info(f"   - Documents: {len(langgraph_format.get('documents', []))}")
        logger.info(f"   - Fields Dictionary: {len(langgraph_format.get('fields_dictionary', {}))}")
        
        # Check document structure
        documents = langgraph_format.get('documents', [])
        if documents:
            doc = documents[0]
            logger.info(f"\n3. Analyzing document structure...")
            logger.info(f"   - Document ID: {doc.get('id', 'N/A')}")
            logger.info(f"   - Document type: {doc.get('type', 'N/A')}")
            logger.info(f"   - Pages count: {len(doc.get('pages', []))}")
            
            if doc.get('pages'):
                page = doc['pages'][0]
                logger.info(f"   - First page keys: {list(page.keys())}")
                logger.info(f"   - Has image_b64: {'image_b64' in page}")
                if 'image_b64' in page:
                    img_len = len(page['image_b64'])
                    logger.info(f"   - Image base64 length: {img_len} chars")
        
        # Test JSON serialization
        logger.info(f"\n4. Testing JSON serialization...")
        try:
            test_json = json.dumps(langgraph_format, default=str, ensure_ascii=False)
            logger.info(f"✅ JSON serialization successful ({len(test_json)} chars)")
        except Exception as e:
            logger.error(f"❌ JSON serialization failed: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return
        
        # Send request to LangGraph
        logger.info(f"\n5. Sending request to LangGraph...")
        langgraph_url = "http://localhost:8002"
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                logger.info(f"   Sending POST to {langgraph_url}/api/langgraph/process-mcp-request")
                response = await client.post(
                    f"{langgraph_url}/api/langgraph/process-mcp-request",
                    json=langgraph_format,
                    headers={"Content-Type": "application/json"}
                )
                
                logger.info(f"   Response status: {response.status_code}")
                
                if response.status_code == 200:
                    logger.info("✅ Request successful")
                    try:
                        response_data = response.json()
                        logger.info(f"   - Status: {response_data.get('status', 'N/A')}")
                        if 'data' in response_data:
                            data = response_data['data']
                            logger.info(f"   - Extracted data count: {len(data.get('extracted_data', {}))}")
                            logger.info(f"   - Confidence scores count: {len(data.get('confidence_scores', {}))}")
                            logger.info(f"   - Quality score: {data.get('quality_score', 'N/A')}")
                    except Exception as e:
                        logger.error(f"❌ Error parsing response JSON: {e}")
                        logger.error(f"   Response text (first 500 chars): {response.text[:500]}")
                else:
                    logger.error(f"❌ Request failed with status {response.status_code}")
                    try:
                        error_data = response.json()
                        logger.error(f"   Error response: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                    except:
                        logger.error(f"   Response text (first 1000 chars): {response.text[:1000]}")
                        
        except httpx.TimeoutException:
            logger.error("❌ Request timeout (120s)")
        except Exception as e:
            logger.error(f"❌ Request error: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    else:
        logger.warning("⚠️  No LangGraph format data available")
    
    logger.info("\n" + "=" * 80)
    logger.info("DIAGNOSTIC COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(diagnose_langgraph_error())

