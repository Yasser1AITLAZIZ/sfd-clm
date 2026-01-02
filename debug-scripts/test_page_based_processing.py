"""
Test script to verify page-based OCR mapping with quality-weighted merging
Tests the new page-by-page processing implementation with real test data
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [PAGE-TEST] - %(message)s',
    handlers=[
        logging.FileHandler(project_root / "debug-scripts" / "test_page_based_processing.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TEST_RECORD_ID = "001XX000001"
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


def load_langgraph_input():
    """Load LangGraph format input data"""
    conversion_output = project_root / "debug-scripts" / "step7_conversion_output.json"
    
    if not conversion_output.exists():
        logger.error(f"❌ {conversion_output.name} not found")
        logger.info("   Please run step7_test_mcp_sending.py first")
        return None
    
    logger.info(f"Loading {conversion_output.name}...")
    with open(conversion_output, 'r', encoding='utf-8') as f:
        return json.load(f)


async def test_page_based_processing():
    """Test page-by-page processing with quality-weighted merging"""
    logger.info("=" * 80)
    logger.info("TEST: Page-Based OCR Mapping with Quality-Weighted Merging")
    logger.info("=" * 80)
    
    # Load input data
    langgraph_format = load_langgraph_input()
    if not langgraph_format:
        return
    
    # Analyze input structure
    logger.info("\n📥 INPUT ANALYSIS:")
    documents = langgraph_format.get('documents', [])
    form_json = langgraph_format.get('form_json', [])
    
    logger.info(f"   - Documents: {len(documents)}")
    logger.info(f"   - Form JSON fields: {len(form_json)}")
    
    total_pages = 0
    for doc in documents:
        pages = doc.get('pages', [])
        total_pages += len(pages)
        logger.info(f"   - Document '{doc.get('id', 'N/A')}': {len(pages)} pages")
        for i, page in enumerate(pages, 1):
            logger.info(f"     Page {i}: {len(page.get('image_b64', '')):,} chars base64")
    
    logger.info(f"   - Total pages to process: {total_pages}")
    
    # Send request to LangGraph
    logger.info(f"\n🚀 Sending request to LangGraph service...")
    langgraph_url = "http://localhost:8002"
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:  # Longer timeout for processing
            logger.info(f"   POST {langgraph_url}/api/langgraph/process-mcp-request")
            logger.info(f"   - Request size: {len(json.dumps(langgraph_format, default=str)):,} chars")
            
            response = await client.post(
                f"{langgraph_url}/api/langgraph/process-mcp-request",
                json=langgraph_format,
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"   Response status: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("✅ Request successful")
                response_data = response.json()
                
                # Save full response
                response_file = project_root / "debug-scripts" / f"page_based_response_{timestamp}.json"
                with open(response_file, 'w', encoding='utf-8') as f:
                    json.dump(response_data, f, indent=2, ensure_ascii=False, default=str)
                logger.info(f"   💾 Full response saved to: {response_file.name}")
                
                # Analyze output structure
                if response_data.get("status") == "success" and "data" in response_data:
                    data = response_data["data"]
                    
                    logger.info(f"\n📤 OUTPUT ANALYSIS:")
                    
                    # Verify filled_form_json with per-field quality_score
                    filled_form_json = data.get('filled_form_json', [])
                    logger.info(f"\n   ✅ Filled Form JSON (Page-Based Processing Result):")
                    logger.info(f"      - Total fields: {len(filled_form_json)}")
                    
                    if filled_form_json:
                        # Verify per-field quality_score
                        fields_with_quality = [f for f in filled_form_json if f.get("quality_score") is not None]
                        fields_without_quality = [f for f in filled_form_json if f.get("quality_score") is None]
                        
                        logger.info(f"      - Fields with quality_score: {len(fields_with_quality)}/{len(filled_form_json)}")
                        
                        if fields_without_quality:
                            logger.error(f"      ❌ Fields missing quality_score: {len(fields_without_quality)}")
                            for field in fields_without_quality[:5]:
                                logger.error(f"         - {field.get('label', 'N/A')}")
                        else:
                            logger.info(f"      ✅ All fields have quality_score")
                        
                        # Analyze quality scores
                        quality_scores = [f.get("quality_score", 0.0) for f in fields_with_quality]
                        if quality_scores:
                            min_qs = min(quality_scores)
                            max_qs = max(quality_scores)
                            avg_qs = sum(quality_scores) / len(quality_scores)
                            
                            logger.info(f"\n      📊 Quality Score Statistics:")
                            logger.info(f"         - Min: {min_qs:.4f}")
                            logger.info(f"         - Max: {max_qs:.4f}")
                            logger.info(f"         - Average: {avg_qs:.4f}")
                        
                        # Show detailed field-by-field analysis
                        logger.info(f"\n      📋 Field-by-Field Analysis:")
                        fields_filled = 0
                        fields_not_available = 0
                        
                        for i, field in enumerate(filled_form_json, 1):
                            label = field.get('label', 'N/A')
                            data_value = field.get('dataValue_target_AI', 'N/A')
                            confidence = field.get('confidence', 0.0)
                            quality_score = field.get('quality_score', 0.0)
                            
                            if data_value != "non disponible" and data_value is not None:
                                fields_filled += 1
                            else:
                                fields_not_available += 1
                            
                            # Show first 10 fields in detail
                            if i <= 10:
                                logger.info(f"         [{i}] {label}:")
                                logger.info(f"             - dataValue_target_AI: {str(data_value)[:60]}")
                                logger.info(f"             - confidence: {confidence:.4f}")
                                logger.info(f"             - quality_score: {quality_score:.4f}")
                                
                                # Verify quality_score <= confidence (since it's weighted by page quality <= 1.0)
                                if quality_score > confidence + 0.01:
                                    logger.warning(f"             ⚠️  quality_score > confidence (unexpected)")
                        
                        logger.info(f"\n      📈 Extraction Summary:")
                        logger.info(f"         - Fields filled: {fields_filled}/{len(filled_form_json)}")
                        logger.info(f"         - Fields not available: {fields_not_available}/{len(filled_form_json)}")
                        logger.info(f"         - Fill rate: {(fields_filled/len(filled_form_json)*100):.1f}%")
                    
                    # Verify overall quality_score
                    overall_quality_score = data.get('quality_score')
                    logger.info(f"\n   📊 Overall Quality Score:")
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
                    
                    # Processing metrics
                    processing_time = data.get('processing_time')
                    logger.info(f"\n   ⏱️  Processing Metrics:")
                    logger.info(f"      - Processing time: {processing_time:.2f}s" if processing_time else "      - Processing time: N/A")
                    logger.info(f"      - Pages processed: {total_pages}")
                    if processing_time and total_pages:
                        logger.info(f"      - Average time per page: {processing_time/total_pages:.2f}s")
                    
                    # Create detailed analysis report
                    analysis_report = {
                        "timestamp": timestamp,
                        "input": {
                            "documents_count": len(documents),
                            "total_pages": total_pages,
                            "form_json_fields_count": len(form_json),
                            "pages_per_document": [len(doc.get('pages', [])) for doc in documents]
                        },
                        "output": {
                            "filled_form_json_count": len(filled_form_json),
                            "fields_with_quality_score": len(fields_with_quality),
                            "fields_filled": fields_filled,
                            "fields_not_available": fields_not_available,
                            "fill_rate_percent": (fields_filled/len(filled_form_json)*100) if filled_form_json else 0,
                            "quality_score_stats": {
                                "min": min_qs if quality_scores else None,
                                "max": max_qs if quality_scores else None,
                                "average": avg_qs if quality_scores else None
                            },
                            "overall_quality_score": overall_quality_score,
                            "processing_time": processing_time
                        },
                        "verification": {
                            "all_fields_have_quality_score": len(fields_without_quality) == 0,
                            "overall_quality_matches_avg": abs(expected_avg - overall_quality_score) < 0.01 if overall_quality_score and quality_scores else None
                        }
                    }
                    
                    report_file = project_root / "debug-scripts" / f"page_based_analysis_{timestamp}.json"
                    with open(report_file, 'w', encoding='utf-8') as f:
                        json.dump(analysis_report, f, indent=2, ensure_ascii=False, default=str)
                    logger.info(f"\n   💾 Analysis report saved to: {report_file.name}")
                    
                    # Summary
                    logger.info(f"\n" + "=" * 80)
                    logger.info("TEST SUMMARY")
                    logger.info("=" * 80)
                    logger.info(f"✅ Page-based processing: {'PASSED' if len(fields_without_quality) == 0 else 'FAILED'}")
                    logger.info(f"✅ Per-field quality_score: {'PASSED' if len(fields_with_quality) == len(filled_form_json) else 'FAILED'}")
                    logger.info(f"✅ Overall quality_score: {'PASSED' if overall_quality_score is not None else 'FAILED'}")
                    logger.info(f"✅ Fields extraction: {fields_filled}/{len(filled_form_json)} fields filled")
                    logger.info("=" * 80)
                    
                else:
                    logger.error("❌ Response structure doesn't match expected format")
                    logger.error(f"   Status: {response_data.get('status')}")
                    logger.error(f"   Has 'data' key: {'data' in response_data}")
                    
            else:
                logger.error(f"❌ Request failed with status {response.status_code}")
                try:
                    error_data = response.json()
                    error_file = project_root / "debug-scripts" / f"page_based_error_{timestamp}.json"
                    with open(error_file, 'w', encoding='utf-8') as f:
                        json.dump(error_data, f, indent=2, ensure_ascii=False, default=str)
                    logger.error(f"   Error response saved to: {error_file.name}")
                except:
                    logger.error(f"   Response text (first 1000 chars): {response.text[:1000]}")
                    
    except httpx.TimeoutException:
        logger.error("❌ Request timeout (300s)")
    except Exception as e:
        logger.error(f"❌ Request error: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(test_page_based_processing())

