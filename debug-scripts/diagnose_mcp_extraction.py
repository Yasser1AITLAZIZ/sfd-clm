"""
Script de diagnostic pour identifier pourquoi le MCP ne reçoit pas les données extraites
Enregistre la réponse LangGraph et ce que le MCP en extrait
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

async def diagnose_mcp_extraction():
    """Diagnostiquer pourquoi le MCP ne reçoit pas les données extraites"""
    logger.info("=" * 80)
    logger.info("DIAGNOSTIC: MCP Data Extraction Problem")
    logger.info("=" * 80)
    
    # Load LangGraph format data
    conversion_output = project_root / "debug-scripts" / "step7_conversion_output.json"
    
    if not conversion_output.exists():
        logger.error(f"❌ {conversion_output.name} not found")
        logger.info("   Please run step7_test_mcp_sending.py first")
        return
    
    logger.info(f"Loading {conversion_output.name}...")
    with open(conversion_output, 'r', encoding='utf-8') as f:
        langgraph_format = json.load(f)
    logger.info("✅ Data loaded")
    
    # Send request to LangGraph
    logger.info(f"\n1. Sending request to LangGraph...")
    langgraph_url = "http://localhost:8002"
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{langgraph_url}/api/langgraph/process-mcp-request",
                json=langgraph_format,
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"   Response status: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("✅ Request successful")
                
                # Parse response
                response_data = response.json()
                
                # Save full LangGraph response
                langgraph_response_file = project_root / "debug-scripts" / f"langgraph_response_{timestamp}.json"
                with open(langgraph_response_file, 'w', encoding='utf-8') as f:
                    json.dump(response_data, f, indent=2, ensure_ascii=False, default=str)
                logger.info(f"   ✅ Full LangGraph response saved to: {langgraph_response_file}")
                
                # Analyze response structure
                logger.info(f"\n2. Analyzing LangGraph response structure...")
                logger.info(f"   - Top level keys: {list(response_data.keys())}")
                logger.info(f"   - Status: {response_data.get('status', 'N/A')}")
                
                if 'data' in response_data:
                    data = response_data['data']
                    logger.info(f"   - Data section keys: {list(data.keys())}")
                    
                    # Check extracted_data
                    extracted_data = data.get('extracted_data', {})
                    logger.info(f"\n3. LangGraph Extracted Data Analysis:")
                    logger.info(f"   - Type: {type(extracted_data).__name__}")
                    logger.info(f"   - Is None: {extracted_data is None}")
                    logger.info(f"   - Is Empty: {not extracted_data or len(extracted_data) == 0}")
                    logger.info(f"   - Count: {len(extracted_data) if extracted_data else 0}")
                    
                    if extracted_data and isinstance(extracted_data, dict):
                        logger.info(f"   - Keys: {list(extracted_data.keys())}")
                        logger.info(f"   - Sample (first 3 items):")
                        for i, (key, value) in enumerate(list(extracted_data.items())[:3]):
                            logger.info(f"     [{i+1}] {key}: {str(value)[:100]}")
                    
                    # Check confidence_scores
                    confidence_scores = data.get('confidence_scores', {})
                    logger.info(f"\n4. LangGraph Confidence Scores Analysis:")
                    logger.info(f"   - Type: {type(confidence_scores).__name__}")
                    logger.info(f"   - Count: {len(confidence_scores) if confidence_scores else 0}")
                    if confidence_scores and isinstance(confidence_scores, dict):
                        logger.info(f"   - Keys: {list(confidence_scores.keys())}")
                    
                    # Check field_mappings
                    field_mappings = data.get('field_mappings', {})
                    logger.info(f"\n5. LangGraph Field Mappings Analysis:")
                    logger.info(f"   - Type: {type(field_mappings).__name__}")
                    logger.info(f"   - Count: {len(field_mappings) if field_mappings else 0}")
                    if field_mappings and isinstance(field_mappings, dict):
                        logger.info(f"   - Keys: {list(field_mappings.keys())}")
                        logger.info(f"   - Sample (first 2 items):")
                        for i, (key, value) in enumerate(list(field_mappings.items())[:2]):
                            logger.info(f"     [{i+1}] {key}: {str(value)[:200]}")
                    
                    # Check filled_form_json with per-field quality_score (NEW - Page-based implementation)
                    filled_form_json = data.get('filled_form_json', [])
                    logger.info(f"\n5.5. LangGraph Filled Form JSON Analysis (Page-Based Implementation):")
                    logger.info(f"   - Type: {type(filled_form_json).__name__}")
                    logger.info(f"   - Count: {len(filled_form_json) if filled_form_json else 0}")
                    
                    if filled_form_json and isinstance(filled_form_json, list):
                        # Check if fields have quality_score (per-field quality from page-based processing)
                        fields_with_quality = [f for f in filled_form_json if f.get("quality_score") is not None]
                        fields_without_quality = [f for f in filled_form_json if f.get("quality_score") is None]
                        
                        logger.info(f"   - Fields with quality_score: {len(fields_with_quality)}/{len(filled_form_json)}")
                        if fields_without_quality:
                            logger.warning(f"   ⚠️  Fields missing quality_score: {len(fields_without_quality)}")
                            logger.warning(f"      Missing fields: {[f.get('label', 'N/A') for f in fields_without_quality[:5]]}")
                        
                        # Sample fields with quality scores
                        logger.info(f"   - Sample fields (first 5 with quality_score):")
                        sample_count = 0
                        for field in filled_form_json:
                            if sample_count >= 5:
                                break
                            label = field.get('label', 'N/A')
                            data_value = field.get('dataValue_target_AI', 'N/A')
                            confidence = field.get('confidence', 'N/A')
                            quality_score = field.get('quality_score', 'N/A')
                            logger.info(f"     [{sample_count+1}] {label}:")
                            logger.info(f"         - dataValue_target_AI: {str(data_value)[:80]}")
                            logger.info(f"         - confidence: {confidence}")
                            logger.info(f"         - quality_score: {quality_score}")  # NEW: Per-field quality
                            sample_count += 1
                        
                        # Verify quality_score calculation (should be confidence * page_quality)
                        logger.info(f"\n   - Quality Score Verification:")
                        quality_issues = []
                        for field in filled_form_json:
                            if field.get("quality_score") is not None:
                                conf = field.get("confidence", 0.0)
                                qs = field.get("quality_score", 0.0)
                                # Quality score should be <= confidence (since it's weighted by page quality <= 1.0)
                                if qs > conf + 0.01:  # Allow small floating point differences
                                    quality_issues.append({
                                        "label": field.get("label", "N/A"),
                                        "confidence": conf,
                                        "quality_score": qs,
                                        "issue": "quality_score > confidence (unexpected)"
                                    })
                        
                        if quality_issues:
                            logger.warning(f"   ⚠️  Found {len(quality_issues)} fields with unexpected quality_score:")
                            for issue in quality_issues[:3]:
                                logger.warning(f"      - {issue['label']}: conf={issue['confidence']:.3f}, qs={issue['quality_score']:.3f}")
                        else:
                            logger.info(f"   ✅ All quality_scores are valid (<= confidence)")
                    
                    # Check overall quality_score
                    overall_quality_score = data.get('quality_score')
                    logger.info(f"\n5.6. Overall Quality Score Analysis:")
                    logger.info(f"   - Overall quality_score: {overall_quality_score}")
                    if overall_quality_score is not None and filled_form_json:
                        # Verify overall quality_score is average of per-field quality_scores
                        field_quality_scores = [f.get("quality_score", 0.0) for f in filled_form_json if f.get("quality_score") is not None]
                        if field_quality_scores:
                            expected_avg = sum(field_quality_scores) / len(field_quality_scores)
                            logger.info(f"   - Expected (avg of per-field): {expected_avg:.4f}")
                            logger.info(f"   - Actual: {overall_quality_score}")
                            if abs(expected_avg - overall_quality_score) < 0.01:
                                logger.info(f"   ✅ Overall quality_score matches average of per-field quality_scores")
                            else:
                                logger.warning(f"   ⚠️  Overall quality_score differs from average (diff: {abs(expected_avg - overall_quality_score):.4f})")
                    
                    # Simulate MCP extraction (exact same logic as mcp_sender.py)
                    logger.info(f"\n6. Simulating MCP extraction (same logic as mcp_sender.py)...")
                    
                    # This is the exact extraction logic from mcp_sender.py
                    if response_data.get("status") == "success" and "data" in response_data:
                        mcp_data = response_data["data"]
                        mcp_filled_form_json = mcp_data.get("filled_form_json", [])  # NEW: Primary format
                        mcp_extracted_data = mcp_data.get("extracted_data", {})  # Deprecated: backward compatibility
                        mcp_confidence_scores = mcp_data.get("confidence_scores", {})
                        mcp_quality_score = mcp_data.get("quality_score")
                        
                        # MCP Filled Form JSON (NEW - Primary format)
                        logger.info(f"\n   - MCP filled_form_json type: {type(mcp_filled_form_json).__name__}")
                        logger.info(f"   - MCP filled_form_json count: {len(mcp_filled_form_json) if mcp_filled_form_json else 0}")
                        if mcp_filled_form_json:
                            fields_with_quality = [f for f in mcp_filled_form_json if f.get("quality_score") is not None]
                            logger.info(f"   - MCP fields with quality_score: {len(fields_with_quality)}/{len(mcp_filled_form_json)}")
                        
                        # MCP Extracted Data (Deprecated - backward compatibility)
                        logger.info(f"\n   - MCP extracted_data type: {type(mcp_extracted_data).__name__}")
                        logger.info(f"   - MCP extracted_data count: {len(mcp_extracted_data) if mcp_extracted_data else 0}")
                        logger.info(f"   - MCP extracted_data is None: {mcp_extracted_data is None}")
                        logger.info(f"   - MCP extracted_data is empty: {not mcp_extracted_data or len(mcp_extracted_data) == 0}")
                        logger.info(f"   - MCP confidence_scores count: {len(mcp_confidence_scores) if mcp_confidence_scores else 0}")
                        logger.info(f"   - MCP quality_score: {mcp_quality_score}")
                        
                        if mcp_extracted_data and isinstance(mcp_extracted_data, dict):
                            logger.info(f"   - MCP extracted_data keys: {list(mcp_extracted_data.keys())}")
                            logger.info(f"   - MCP extracted_data sample (first 3 items):")
                            for i, (key, value) in enumerate(list(mcp_extracted_data.items())[:3]):
                                logger.info(f"     [{i+1}] {key}: {str(value)[:100]}")
                        
                        # Build MCP response structure (same as mcp_sender.py)
                        mcp_response = {
                            "message_id": f"diagnostic-{timestamp}",
                            "filled_form_json": mcp_filled_form_json,  # NEW: Primary format
                            "extracted_data": mcp_extracted_data,  # Deprecated: backward compatibility
                            "confidence_scores": mcp_confidence_scores,
                            "status": "success",
                            "quality_score": mcp_quality_score
                        }
                        
                        # Save MCP extracted response
                        mcp_response_file = project_root / "debug-scripts" / f"mcp_extracted_response_{timestamp}.json"
                        with open(mcp_response_file, 'w', encoding='utf-8') as f:
                            json.dump(mcp_response, f, indent=2, ensure_ascii=False, default=str)
                        logger.info(f"   ✅ MCP extracted response saved to: {mcp_response_file}")
                        
                        # Compare LangGraph vs MCP
                        logger.info(f"\n7. Comparison: LangGraph vs MCP Extraction:")
                        logger.info(f"   - LangGraph extracted_data count: {len(extracted_data) if extracted_data else 0}")
                        logger.info(f"   - MCP extracted_data count: {len(mcp_extracted_data) if mcp_extracted_data else 0}")
                        logger.info(f"   - Match: {len(extracted_data) == len(mcp_extracted_data) if extracted_data and mcp_extracted_data else False}")
                        
                        if extracted_data and mcp_extracted_data:
                            langgraph_keys = set(extracted_data.keys())
                            mcp_keys = set(mcp_extracted_data.keys())
                            missing_in_mcp = langgraph_keys - mcp_keys
                            extra_in_mcp = mcp_keys - langgraph_keys
                            
                            if missing_in_mcp:
                                logger.warning(f"   ⚠️  Keys in LangGraph but NOT in MCP: {list(missing_in_mcp)}")
                            if extra_in_mcp:
                                logger.warning(f"   ⚠️  Keys in MCP but NOT in LangGraph: {list(extra_in_mcp)}")
                            if not missing_in_mcp and not extra_in_mcp:
                                logger.info(f"   ✅ All keys match between LangGraph and MCP")
                        
                        # Save comparison report
                        comparison = {
                            "timestamp": timestamp,
                            "langgraph_response": {
                                "filled_form_json_count": len(filled_form_json) if filled_form_json else 0,
                                "filled_form_json_fields_with_quality": len([f for f in filled_form_json if f.get("quality_score") is not None]) if filled_form_json else 0,
                                "extracted_data_count": len(extracted_data) if extracted_data else 0,
                                "extracted_data_keys": list(extracted_data.keys()) if extracted_data else [],
                                "confidence_scores_count": len(confidence_scores) if confidence_scores else 0,
                                "field_mappings_count": len(field_mappings) if field_mappings else 0,
                                "quality_score": data.get("quality_score")
                            },
                            "mcp_extraction": {
                                "filled_form_json_count": len(mcp_filled_form_json) if mcp_filled_form_json else 0,
                                "filled_form_json_fields_with_quality": len([f for f in mcp_filled_form_json if f.get("quality_score") is not None]) if mcp_filled_form_json else 0,
                                "extracted_data_count": len(mcp_extracted_data) if mcp_extracted_data else 0,
                                "extracted_data_keys": list(mcp_extracted_data.keys()) if mcp_extracted_data else [],
                                "confidence_scores_count": len(mcp_confidence_scores) if mcp_confidence_scores else 0,
                                "quality_score": mcp_quality_score
                            },
                            "comparison": {
                                "filled_form_json_match": len(filled_form_json) == len(mcp_filled_form_json) if filled_form_json and mcp_filled_form_json else False,
                                "data_match": len(extracted_data) == len(mcp_extracted_data) if extracted_data and mcp_extracted_data else False,
                                "missing_in_mcp": list(missing_in_mcp) if extracted_data and mcp_extracted_data else [],
                                "extra_in_mcp": list(extra_in_mcp) if extracted_data and mcp_extracted_data else []
                            }
                        }
                        
                        comparison_file = project_root / "debug-scripts" / f"comparison_report_{timestamp}.json"
                        with open(comparison_file, 'w', encoding='utf-8') as f:
                            json.dump(comparison, f, indent=2, ensure_ascii=False, default=str)
                        logger.info(f"   ✅ Comparison report saved to: {comparison_file}")
                        
                    else:
                        logger.warning("   ⚠️  Response structure doesn't match expected format")
                        logger.info(f"   Status: {response_data.get('status')}")
                        logger.info(f"   Has 'data' key: {'data' in response_data}")
                else:
                    logger.warning("   ⚠️  No 'data' section in response")
                    logger.info(f"   Response structure: {json.dumps(response_data, indent=2, default=str)[:500]}")
            else:
                logger.error(f"❌ Request failed with status {response.status_code}")
                try:
                    error_data = response.json()
                    error_file = project_root / "debug-scripts" / f"langgraph_error_{timestamp}.json"
                    with open(error_file, 'w', encoding='utf-8') as f:
                        json.dump(error_data, f, indent=2, ensure_ascii=False, default=str)
                    logger.error(f"   Error response saved to: {error_file}")
                    logger.error(f"   Error response: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                except:
                    error_text_file = project_root / "debug-scripts" / f"langgraph_error_{timestamp}.txt"
                    with open(error_text_file, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    logger.error(f"   Error response text saved to: {error_text_file}")
                    logger.error(f"   Response text (first 1000 chars): {response.text[:1000]}")
                    
    except httpx.TimeoutException:
        logger.error("❌ Request timeout (120s)")
    except Exception as e:
        logger.error(f"❌ Request error: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("\n" + "=" * 80)
    logger.info("DIAGNOSTIC COMPLETE")
    logger.info("=" * 80)
    logger.info(f"\n📁 Output files saved in: {project_root / 'debug-scripts'}")
    logger.info(f"   - LangGraph response: langgraph_response_{timestamp}.json")
    logger.info(f"   - MCP extracted response: mcp_extracted_response_{timestamp}.json")
    logger.info(f"   - Comparison report: comparison_report_{timestamp}.json")

if __name__ == "__main__":
    asyncio.run(diagnose_mcp_extraction())

