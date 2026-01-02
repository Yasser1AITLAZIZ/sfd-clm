"""
Script de diagnostic pour identifier l'erreur dans le service LangGraph
"""
import sys
import json
import logging
import asyncio
import httpx
from pathlib import Path
from datetime import datetime

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
        logger.info(f"\n📥 INPUT DATA STRUCTURE (Sent to LangGraph):")
        logger.info(f"   - Record ID: {langgraph_format.get('record_id', 'N/A')}")
        logger.info(f"   - Session ID: {langgraph_format.get('session_id', 'N/A')}")
        logger.info(f"   - User Request length: {len(langgraph_format.get('user_request', ''))} chars")
        logger.info(f"   - Documents: {len(langgraph_format.get('documents', []))}")
        logger.info(f"   - Form JSON fields: {len(langgraph_format.get('form_json', []))}")
        logger.info(f"   - Fields Dictionary: {len(langgraph_format.get('fields_dictionary', {}))}")
        
        # Check document structure (INPUT)
        documents = langgraph_format.get('documents', [])
        if documents:
            doc = documents[0]
            logger.info(f"\n   📄 Document Structure (INPUT):")
            logger.info(f"      - Document ID: {doc.get('id', 'N/A')}")
            logger.info(f"      - Document type: {doc.get('type', 'N/A')}")
            logger.info(f"      - Pages count: {len(doc.get('pages', []))}")
            
            if doc.get('pages'):
                logger.info(f"      - Page-by-Page Structure:")
                for i, page in enumerate(doc.get('pages', []), 1):
                    logger.info(f"        Page {i}:")
                    logger.info(f"          - page_number: {page.get('page_number', 'N/A')}")
                    logger.info(f"          - Has image_b64: {'image_b64' in page}")
                    if 'image_b64' in page:
                        img_len = len(page['image_b64'])
                        logger.info(f"          - Image base64 length: {img_len:,} chars")
                    logger.info(f"          - image_mime: {page.get('image_mime', 'N/A')}")
        
        # Check form_json structure (INPUT)
        form_json = langgraph_format.get('form_json', [])
        if form_json:
            logger.info(f"\n   📋 Form JSON Structure (INPUT):")
            logger.info(f"      - Total fields: {len(form_json)}")
            logger.info(f"      - Sample fields (first 3):")
            for i, field in enumerate(form_json[:3], 1):
                logger.info(f"        [{i}] {field.get('label', 'N/A')}:")
                logger.info(f"            - type: {field.get('type', 'N/A')}")
                logger.info(f"            - required: {field.get('required', 'N/A')}")
                logger.info(f"            - possibleValues count: {len(field.get('possibleValues', []))}")
                logger.info(f"            - dataValue_target_AI (initial): {field.get('dataValue_target_AI', 'N/A')}")
        
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
                        logger.info(f"\n📤 OUTPUT DATA STRUCTURE (Received from LangGraph):")
                        logger.info(f"   - Status: {response_data.get('status', 'N/A')}")
                        
                        if 'data' in response_data:
                            data = response_data['data']
                            
                            # Check filled_form_json (NEW - Page-based implementation)
                            filled_form_json = data.get('filled_form_json', [])
                            logger.info(f"\n   📋 Filled Form JSON (Page-Based Implementation - OUTPUT):")
                            logger.info(f"      - Total fields: {len(filled_form_json) if filled_form_json else 0}")
                            
                            if filled_form_json:
                                fields_with_quality = [f for f in filled_form_json if f.get("quality_score") is not None]
                                fields_without_quality = [f for f in filled_form_json if f.get("quality_score") is None]
                                
                                logger.info(f"      - Fields with quality_score: {len(fields_with_quality)}/{len(filled_form_json)}")
                                if fields_without_quality:
                                    logger.warning(f"      ⚠️  Fields missing quality_score: {len(fields_without_quality)}")
                                
                                # Show sample fields with before/after comparison
                                logger.info(f"\n      - Sample Fields (Before → After):")
                                for i, field in enumerate(filled_form_json[:5], 1):
                                    label = field.get('label', 'N/A')
                                    initial_value = "null"  # Would need to compare with input
                                    final_value = field.get('dataValue_target_AI', 'N/A')
                                    confidence = field.get('confidence', 'N/A')
                                    quality_score = field.get('quality_score', 'N/A')
                                    
                                    logger.info(f"        [{i}] {label}:")
                                    logger.info(f"            - dataValue_target_AI: {initial_value} → {str(final_value)[:60]}")
                                    logger.info(f"            - confidence: {confidence}")
                                    logger.info(f"            - quality_score: {quality_score}")  # NEW: Per-field quality
                                
                                # Verify quality_score calculation
                                if fields_with_quality:
                                    avg_quality = sum(f.get("quality_score", 0.0) for f in fields_with_quality) / len(fields_with_quality)
                                    logger.info(f"\n      - Average per-field quality_score: {avg_quality:.4f}")
                            
                            # Overall quality score
                            overall_quality_score = data.get('quality_score')
                            logger.info(f"\n   📊 Overall Quality Score (OUTPUT):")
                            logger.info(f"      - Overall quality_score: {overall_quality_score}")
                            if overall_quality_score is not None and filled_form_json:
                                field_quality_scores = [f.get("quality_score", 0.0) for f in filled_form_json if f.get("quality_score") is not None]
                                if field_quality_scores:
                                    expected_avg = sum(field_quality_scores) / len(field_quality_scores)
                                    logger.info(f"      - Expected (avg of per-field): {expected_avg:.4f}")
                                    if abs(expected_avg - overall_quality_score) < 0.01:
                                        logger.info(f"      ✅ Overall quality_score matches average of per-field quality_scores")
                                    else:
                                        logger.warning(f"      ⚠️  Overall quality_score differs (diff: {abs(expected_avg - overall_quality_score):.4f})")
                            
                            # Legacy fields (backward compatibility)
                            logger.info(f"\n   📦 Legacy Fields (Backward Compatibility - OUTPUT):")
                            logger.info(f"      - Extracted data count: {len(data.get('extracted_data', {}))}")
                            logger.info(f"      - Confidence scores count: {len(data.get('confidence_scores', {}))}")
                            
                            # Save detailed output for analysis
                            output_file = project_root / "debug-scripts" / f"langgraph_detailed_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                            with open(output_file, 'w', encoding='utf-8') as f:
                                json.dump({
                                    "input": {
                                        "documents_count": len(langgraph_format.get('documents', [])),
                                        "form_json_count": len(langgraph_format.get('form_json', [])),
                                        "sample_document": documents[0] if documents else None,
                                        "sample_form_fields": form_json[:3] if form_json else []
                                    },
                                    "output": {
                                        "filled_form_json": filled_form_json,
                                        "extracted_data": data.get('extracted_data', {}),
                                        "confidence_scores": data.get('confidence_scores', {}),
                                        "quality_score": overall_quality_score,
                                        "processing_time": data.get('processing_time')
                                    }
                                }, f, indent=2, ensure_ascii=False, default=str)
                            logger.info(f"\n   💾 Detailed input/output saved to: {output_file.name}")
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

