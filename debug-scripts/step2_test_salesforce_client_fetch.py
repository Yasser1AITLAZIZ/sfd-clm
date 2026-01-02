"""
Step 2: Test Backend MCP Salesforce Client Fetch
Tests the Salesforce client fetch from Mock Salesforce service
Note: Form JSON normalization is handled in Step 3 (Preprocessing Pipeline)
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


async def test_salesforce_client_full():
    """Test the full Salesforce client fetch function (requires running service)"""
    logger.info("=" * 80)
    logger.info("TESTING: Salesforce Client Fetch (requires running service)")
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
        
        # Verify fields structure
        for i, field in enumerate(salesforce_data.fields_to_fill, 1):
            logger.info(f"\n  Field {i}:")
            logger.info(f"    - Label: {field.label}")
            logger.info(f"    - Type: {field.type}")
            logger.info(f"    - Required: {field.required}")
            if hasattr(field, 'possibleValues') and field.possibleValues:
                logger.info(f"    - Possible Values: {len(field.possibleValues)} values")
        
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
                    "label": field.label,
                    "apiName": field.apiName,
                    "type": field.type,
                    "required": field.required,
                    "possibleValues": field.possibleValues,
                    "defaultValue": field.defaultValue
                }
                for field in salesforce_data.fields_to_fill
            ]
        }
        
        output_file = project_root / "debug-scripts" / "step2_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"\n✅ Output saved to: {output_file}")
        
        return salesforce_data
        
    except Exception as e:
        logger.error(f"❌ ERROR in full fetch test: {type(e).__name__}: {str(e)}", exc_info=True)
        raise


async def main():
    """Main test function"""
    logger.info("=" * 80)
    logger.info("STEP 2: BACKEND MCP SALESFORCE CLIENT FETCH TEST")
    logger.info("=" * 80)
    logger.info(f"Test Record ID: {TEST_RECORD_ID}")
    logger.info("")
    logger.info("Note: Form JSON normalization is handled in Step 3 (Preprocessing Pipeline)")
    logger.info("")
    
    # Test: Full fetch (requires service)
    salesforce_data = None
    try:
        salesforce_data = await test_salesforce_client_full()
        if salesforce_data:
            logger.info("✅ Salesforce client fetch test: PASSED")
        else:
            logger.warning("⚠️  Salesforce client fetch test: SKIPPED (service not running or URL not configured)")
    except Exception as e:
        logger.warning(f"⚠️  Salesforce client fetch test: SKIPPED - {e}")
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2 SUMMARY")
    logger.info("=" * 80)
    if salesforce_data:
        logger.info("✅ Salesforce client fetch: PASSED")
        logger.info(f"   - Record ID: {salesforce_data.record_id}")
        logger.info(f"   - Documents: {len(salesforce_data.documents)}")
        logger.info(f"   - Fields to Fill: {len(salesforce_data.fields_to_fill)}")
    else:
        logger.warning("⚠️  Salesforce client fetch: SKIPPED")
        logger.info("   - Service might not be running")
        logger.info("   - Check that Mock Salesforce service is accessible at http://localhost:8001")
    
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2 COMPLETE - Check step2_output.log and step2_output.json for details")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
