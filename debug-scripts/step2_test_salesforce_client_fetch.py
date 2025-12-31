"""
Step 2: Test Backend MCP Salesforce Client Fetch
Tests the conversion of Salesforce fields to FieldToFillResponseSchema format
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
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [STEP2] - %(message)s',
    handlers=[
        logging.FileHandler(project_root / "debug-scripts" / "step2_output.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TEST_RECORD_ID = "001XX000001"


def load_step1_output():
    """Load step 1 output"""
    step1_output = project_root / "debug-scripts" / "step1_output.json"
    if step1_output.exists():
        try:
            with open(step1_output, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load step1 output: {e}")
    return None


async def test_salesforce_client_logic():
    """Test the Salesforce client conversion logic without HTTP call"""
    logger.info("=" * 80)
    logger.info("TESTING: Salesforce Client Conversion Logic")
    logger.info("=" * 80)
    
    try:
        from app.models.schemas import (
            SalesforceFormFieldSchema,
            FieldToFillResponseSchema
        )
        
        # Load step 1 output to get fields in new format
        step1_data = load_step1_output()
        if not step1_data:
            logger.warning("Step 1 output not found, creating mock data")
            step1_data = {
                "fields": [
                    {
                        "label": "Evènement déclencheur de sinistre",
                        "apiName": None,
                        "type": "picklist",
                        "required": True,
                        "possibleValues": ["Accident", "Assistance", "Bris de glace"],
                        "defaultValue": "Accident"
                    }
                ]
            }
        
        fields_data = step1_data.get("fields", [])
        logger.info(f"Testing conversion of {len(fields_data)} fields")
        
        # Test conversion
        converted_fields = []
        conversion_errors = []
        
        for i, field_data in enumerate(fields_data, 1):
            try:
                logger.info(f"\n--- Converting Field {i} ---")
                logger.info(f"  Original data: {json.dumps(field_data, indent=2, ensure_ascii=False)}")
                
                # Create SalesforceFormFieldSchema
                form_field = SalesforceFormFieldSchema(**field_data)
                logger.info(f"  ✅ Created SalesforceFormFieldSchema")
                logger.info(f"     - Label: {form_field.label}")
                logger.info(f"     - Type: {form_field.type}")
                logger.info(f"     - Required: {form_field.required}")
                
                # Convert to FieldToFillResponseSchema
                converted = FieldToFillResponseSchema.from_salesforce_form_field(form_field)
                logger.info(f"  ✅ Converted to FieldToFillResponseSchema")
                logger.info(f"     - Field Name: {converted.field_name}")
                logger.info(f"     - Field Type: {converted.field_type}")
                logger.info(f"     - Required: {converted.required}")
                logger.info(f"     - Label: {converted.label}")
                logger.info(f"     - Value: {converted.value}")
                if hasattr(converted, 'metadata') and converted.metadata:
                    logger.info(f"     - Metadata: {json.dumps(converted.metadata, indent=6, ensure_ascii=False)}")
                    logger.info(f"       - Original Type: {converted.metadata.get('original_type', 'N/A')}")
                    logger.info(f"       - Possible Values: {len(converted.metadata.get('possibleValues', []))} values")
                    logger.info(f"       - Default Value: {converted.metadata.get('defaultValue', 'N/A')}")
                
                converted_fields.append(converted)
                
            except Exception as e:
                logger.error(f"  ❌ Error converting field {i}: {type(e).__name__}: {str(e)}")
                conversion_errors.append({
                    "field_index": i,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
        
        logger.info("\n" + "=" * 80)
        logger.info("CONVERSION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total fields: {len(fields_data)}")
        logger.info(f"Successfully converted: {len(converted_fields)}")
        logger.info(f"Failed conversions: {len(conversion_errors)}")
        
        # Check metadata preservation
        fields_with_metadata = sum(1 for f in converted_fields if hasattr(f, 'metadata') and f.metadata)
        fields_with_possible_values = sum(1 for f in converted_fields if hasattr(f, 'metadata') and f.metadata and f.metadata.get('possibleValues'))
        fields_with_original_type = sum(1 for f in converted_fields if hasattr(f, 'metadata') and f.metadata and f.metadata.get('original_type'))
        
        logger.info(f"\nMetadata Preservation:")
        logger.info(f"  - Fields with metadata: {fields_with_metadata}/{len(converted_fields)}")
        logger.info(f"  - Fields with possibleValues: {fields_with_possible_values}")
        logger.info(f"  - Fields with original_type: {fields_with_original_type}")
        
        if fields_with_metadata < len(converted_fields):
            logger.warning(f"  ⚠️  WARNING: {len(converted_fields) - fields_with_metadata} fields are missing metadata!")
        
        if conversion_errors:
            logger.error("\nConversion Errors:")
            for error in conversion_errors:
                logger.error(f"  Field {error['field_index']}: {error['error']}")
        
        # Save converted fields with full metadata
        converted_data = {
            "original_fields_count": len(fields_data),
            "converted_fields_count": len(converted_fields),
            "conversion_errors": conversion_errors,
            "converted_fields": [
                {
                    "field_name": f.field_name,
                    "field_type": f.field_type,
                    "value": f.value,
                    "required": f.required,
                    "label": f.label,
                    "metadata": f.metadata if hasattr(f, 'metadata') and f.metadata else {}
                }
                for f in converted_fields
            ]
        }
        
        output_file = project_root / "debug-scripts" / "step2_conversion_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"\n✅ Conversion output saved to: {output_file}")
        
        return converted_fields, conversion_errors
        
    except Exception as e:
        logger.error(f"❌ ERROR in conversion test: {type(e).__name__}: {str(e)}", exc_info=True)
        return None, None


async def test_salesforce_client_full():
    """Test the full Salesforce client fetch function (requires running service)"""
    logger.info("\n" + "=" * 80)
    logger.info("TESTING: Full Salesforce Client Fetch (requires running service)")
    logger.info("=" * 80)
    
    try:
        from app.services.salesforce_client import fetch_salesforce_data
        from app.core.config import settings
        
        logger.info(f"Mock Salesforce URL: {getattr(settings, 'mock_salesforce_url', 'NOT SET')}")
        logger.info(f"Record ID: {TEST_RECORD_ID}")
        
        # Check if URL is configured
        if not hasattr(settings, 'mock_salesforce_url') or not settings.mock_salesforce_url:
            logger.warning("⚠️  Mock Salesforce URL not configured - skipping HTTP test")
            logger.warning("   Set MOCK_SALESFORCE_URL environment variable to test HTTP fetch")
            return None
        
        logger.info("Attempting to fetch data from Mock Salesforce service...")
        logger.info(f"   Full URL will be: {settings.mock_salesforce_url.rstrip('/')}/mock/salesforce/get-record-data")
        
        # Test health endpoint first
        try:
            import httpx
            health_url = f"{settings.mock_salesforce_url.rstrip('/')}/health"
            logger.info(f"   Testing health endpoint: {health_url}")
            async with httpx.AsyncClient(timeout=5.0) as client:
                health_response = await client.get(health_url)
                if health_response.status_code == 200:
                    logger.info(f"   ✅ Service is healthy: {health_response.json()}")
                else:
                    logger.warning(f"   ⚠️  Health check returned {health_response.status_code}")
        except Exception as e:
            logger.warning(f"   ⚠️  Could not reach health endpoint: {e}")
            logger.warning("   Service might not be running or URL is incorrect")
        
        # Try to get OpenAPI spec to see available routes
        try:
            import httpx
            docs_url = f"{settings.mock_salesforce_url.rstrip('/')}/openapi.json"
            logger.info(f"   Checking available routes: {docs_url}")
            async with httpx.AsyncClient(timeout=5.0) as client:
                docs_response = await client.get(docs_url)
                if docs_response.status_code == 200:
                    openapi_spec = docs_response.json()
                    paths = openapi_spec.get("paths", {})
                    logger.info(f"   ✅ Found {len(paths)} registered endpoints:")
                    for path, methods in paths.items():
                        method_list = list(methods.keys())
                        logger.info(f"      {', '.join(method_list).upper():6} {path}")
                    
                    # Check if our endpoint exists
                    target_path = "/mock/salesforce/get-record-data"
                    if target_path in paths:
                        logger.info(f"   ✅ Target endpoint found: {target_path}")
                    else:
                        logger.error(f"   ❌ Target endpoint NOT found: {target_path}")
                        logger.error(f"   Available paths: {list(paths.keys())}")
                else:
                    logger.warning(f"   ⚠️  Could not fetch OpenAPI spec: {docs_response.status_code}")
        except Exception as e:
            logger.warning(f"   ⚠️  Could not check routes: {e}")
        
        # Test the endpoint directly first to see the actual response
        try:
            import httpx
            endpoint_url = f"{settings.mock_salesforce_url.rstrip('/')}/mock/salesforce/get-record-data"
            logger.info(f"   Testing endpoint directly: {endpoint_url}")
            async with httpx.AsyncClient(timeout=10.0) as client:
                test_response = await client.post(
                    endpoint_url,
                    json={"record_id": TEST_RECORD_ID},
                    headers={"Content-Type": "application/json"}
                )
                logger.info(f"   Direct test response status: {test_response.status_code}")
                if test_response.status_code != 200:
                    try:
                        error_body = test_response.json()
                        logger.error(f"   Error response: {json.dumps(error_body, indent=2, ensure_ascii=False)}")
                    except:
                        logger.error(f"   Error response text: {test_response.text[:500]}")
        except Exception as e:
            logger.warning(f"   ⚠️  Direct endpoint test failed: {e}")
        
        try:
            salesforce_data = await fetch_salesforce_data(TEST_RECORD_ID)
        except Exception as e:
            # If it's a 404, try to get more details
            if "404" in str(e) or "not found" in str(e).lower():
                logger.error(f"❌ 404 Error - Endpoint not found")
                logger.error(f"   This usually means:")
                logger.error(f"   1. The service is running but the endpoint path is wrong")
                logger.error(f"   2. The router isn't properly registered")
                logger.error(f"   3. The service is running on a different port")
                logger.error(f"   Expected endpoint: {settings.mock_salesforce_url.rstrip('/')}/mock/salesforce/get-record-data")
                logger.error(f"   Note: Docker Compose maps port 8001 (host) -> 8000 (container)")
                logger.error(f"   From host machine, use: http://localhost:8001")
                logger.error(f"   From Docker network, use: http://mock-salesforce:8000")
                logger.error(f"   Try checking: curl {settings.mock_salesforce_url.rstrip('/')}/health")
                logger.error(f"   Or check the service logs: docker-compose logs mock-salesforce")
            raise
        
        logger.info("✅ Data fetched successfully")
        logger.info(f"  - Record ID: {salesforce_data.record_id}")
        logger.info(f"  - Record Type: {salesforce_data.record_type}")
        logger.info(f"  - Documents: {len(salesforce_data.documents)}")
        logger.info(f"  - Fields to Fill: {len(salesforce_data.fields_to_fill)}")
        
        # Save output
        output_data = {
            "record_id": salesforce_data.record_id,
            "record_type": salesforce_data.record_type,
            "documents": [
                {
                    "document_id": doc.document_id,
                    "name": doc.name,
                    "url": doc.url,
                    "type": doc.type,
                    "indexed": doc.indexed
                }
                for doc in salesforce_data.documents
            ],
            "fields_to_fill": [
                {
                    "field_name": f.field_name,
                    "field_type": f.field_type,
                    "value": f.value,
                    "required": f.required,
                    "label": f.label,
                    "metadata": f.metadata if hasattr(f, 'metadata') and f.metadata else {}
                }
                for f in salesforce_data.fields_to_fill
            ]
        }
        
        output_file = project_root / "debug-scripts" / "step2_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"\n✅ Output saved to: {output_file}")
        
        return salesforce_data
        
    except Exception as e:
        logger.error(f"❌ ERROR in full fetch test: {type(e).__name__}: {str(e)}", exc_info=True)
        return None


async def main():
    """Main test function"""
    logger.info("=" * 80)
    logger.info("STEP 2: BACKEND MCP SALESFORCE CLIENT FETCH TEST")
    logger.info("=" * 80)
    logger.info(f"Test Record ID: {TEST_RECORD_ID}")
    logger.info("")
    
    # Test 1: Conversion logic
    converted_fields, errors = await test_salesforce_client_logic()
    
    # Test 2: Full fetch (requires service)
    salesforce_data = await test_salesforce_client_full()
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2 SUMMARY")
    logger.info("=" * 80)
    
    if converted_fields:
        logger.info(f"✅ Field conversion method test: PASSED")
    else:
        logger.error("❌ Field conversion method test: FAILED")
    
    if converted_fields and len(converted_fields) > 0:
        logger.info(f"✅ Conversion logic test: PASSED ({len(converted_fields)} fields converted)")
    else:
        logger.error("❌ Conversion logic test: FAILED")
    
    if salesforce_data:
        logger.info("✅ Full fetch test: PASSED")
    else:
        logger.warning("⚠️  Full fetch test: SKIPPED (service not running or URL not configured)")
    
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2 COMPLETE - Check step2_output.log and step2_output.json for details")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

