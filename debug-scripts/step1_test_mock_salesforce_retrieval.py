"""
Step 1: Test Mock Salesforce Data Retrieval
Tests the ability to retrieve documents and fields from test-data directory
"""

import sys
import json
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "mock-salesforce"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [STEP1] - %(message)s',
    handlers=[
        logging.FileHandler(project_root / "debug-scripts" / "step1_output.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TEST_RECORD_ID = "001XX000001"


def test_file_loader():
    """Test file loader functions"""
    logger.info("=" * 80)
    logger.info("TESTING: File Loader Functions")
    logger.info("=" * 80)
    
    try:
        from app.data.file_loader import (
            load_documents_for_record,
            load_fields_for_record,
            get_test_data_base_path
        )
        
        base_path = get_test_data_base_path()
        logger.info(f"Test data base path: {base_path}")
        
        # Test documents loading
        logger.info("\n--- Testing Documents Loading ---")
        documents = load_documents_for_record(TEST_RECORD_ID, base_path=base_path)
        logger.info(f"Documents loaded: {len(documents)}")
        for i, doc in enumerate(documents, 1):
            logger.info(f"  Document {i}:")
            logger.info(f"    - ID: {doc.document_id}")
            logger.info(f"    - Name: {doc.name}")
            logger.info(f"    - URL: {doc.url}")
            logger.info(f"    - Type: {doc.type}")
        
        # Test fields loading
        logger.info("\n--- Testing Fields Loading ---")
        fields = load_fields_for_record(TEST_RECORD_ID, base_path=base_path)
        logger.info(f"Fields loaded: {len(fields)}")
        
        # Check fields file
        fields_dir = base_path / "fields"
        fields_file = fields_dir / f"{TEST_RECORD_ID}_fields.json"
        if not fields_file.exists():
            fields_file = fields_dir / f"{TEST_RECORD_ID}.json"
        
        logger.info(f"Fields file: {fields_file}")
        if fields_file.exists():
            logger.info(f"✅ Fields file exists")
            try:
                with open(fields_file, 'r', encoding='utf-8') as f:
                    fields_data = json.load(f)
                    fields_count = len(fields_data.get("fields", []))
                    logger.info(f"   - Contains {fields_count} fields")
                    logger.info(f"   - File size: {fields_file.stat().st_size} bytes")
            except Exception as e:
                logger.error(f"❌ Error reading fields file: {e}")
        else:
            logger.error(f"❌ Fields file NOT FOUND. Tried: {fields_file}")
        
        return documents, fields
        
    except Exception as e:
        logger.error(f"❌ ERROR in file loader test: {type(e).__name__}: {str(e)}", exc_info=True)
        return [], []


def test_mock_record():
    """Test get_mock_record function"""
    logger.info("\n" + "=" * 80)
    logger.info("TESTING: get_mock_record Function")
    logger.info("=" * 80)
    
    try:
        from app.data.mock_records import get_mock_record
        
        mock_data = get_mock_record(TEST_RECORD_ID)
        
        logger.info(f"✅ Mock record retrieved")
        logger.info(f"  - Record ID: {mock_data.record_id}")
        logger.info(f"  - Record Type: {mock_data.record_type}")
        logger.info(f"  - Documents: {len(mock_data.documents)}")
        logger.info(f"  - Fields: {len(mock_data.fields)}")
        logger.info(f"  - Fields to Fill: {len(mock_data.fields_to_fill)}")
        
        return mock_data
        
    except Exception as e:
        logger.error(f"❌ ERROR in mock record test: {type(e).__name__}: {str(e)}", exc_info=True)
        return None


def main():
    """Main test function"""
    logger.info("=" * 80)
    logger.info("STEP 1: MOCK SALESFORCE DATA RETRIEVAL TEST")
    logger.info("=" * 80)
    logger.info(f"Test Record ID: {TEST_RECORD_ID}")
    logger.info("")
    
    # Test 1: File loader
    documents, fields = test_file_loader()
    
    # Test 2: Mock record
    mock_data = test_mock_record()
    
    # Save output
    output_data = {
        "record_id": TEST_RECORD_ID,
        "record_type": mock_data.record_type if mock_data else "Unknown",
        "documents": [
            {
                "document_id": doc.document_id,
                "name": doc.name,
                "url": doc.url,
                "type": doc.type,
                "indexed": doc.indexed
            }
            for doc in (mock_data.documents if mock_data else documents)
        ],
        "fields_to_fill": [],
        "fields": [
            {
                "label": field.label,
                "apiName": field.apiName,
                "type": field.type,
                "required": field.required,
                "possibleValues": field.possibleValues,
                "defaultValue": field.defaultValue
            }
            for field in (mock_data.fields if mock_data else fields)
        ]
    }
    
    output_file = project_root / "debug-scripts" / "step1_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, default=str, ensure_ascii=False)
    
    logger.info("\n" + "=" * 80)
    logger.info("STEP 1 SUMMARY")
    logger.info("=" * 80)
    logger.info(f"✅ Documents loaded: {len(output_data['documents'])}")
    logger.info(f"✅ Fields loaded: {len(output_data['fields'])}")
    logger.info(f"\n✅ Output saved to: {output_file}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

