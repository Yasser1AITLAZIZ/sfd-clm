#!/usr/bin/env python3
"""Test script for end-to-end pipeline testing"""
import os
import sys
import json
import time
import requests
import threading
import http.server
import socketserver
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configuration
DOCUMENTS_DIR = Path(__file__).parent / "documents"
FIELDS_FILE = Path(__file__).parent / "fields" / "fields.json"
RESULTS_DIR = Path(__file__).parent / "results"
LOGS_DIR = RESULTS_DIR / "logs"

# Service URLs
MOCK_SALESFORCE_URL = "http://localhost:8001"
BACKEND_MCP_URL = "http://localhost:8000"
BACKEND_LANGGRAPH_URL = "http://localhost:8002"
FILE_SERVER_URL = "http://localhost:8003"
FILE_SERVER_PORT = 8003

# File server
_file_server: Optional[socketserver.TCPServer] = None
_file_server_thread: Optional[threading.Thread] = None


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler to serve files from documents directory"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCUMENTS_DIR), **kwargs)
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def start_file_server():
    """Start HTTP file server for documents"""
    global _file_server, _file_server_thread
    
    try:
        handler = CustomHTTPRequestHandler
        _file_server = socketserver.TCPServer(("", FILE_SERVER_PORT), handler)
        _file_server.allow_reuse_address = True
        
        def serve():
            _file_server.serve_forever()
        
        _file_server_thread = threading.Thread(target=serve, daemon=True)
        _file_server_thread.start()
        print(f"✅ File server started on {FILE_SERVER_URL}")
        time.sleep(1)  # Give server time to start
        return True
    except Exception as e:
        print(f"❌ Failed to start file server: {e}")
        return False


def stop_file_server():
    """Stop HTTP file server"""
    global _file_server
    if _file_server:
        _file_server.shutdown()
        _file_server.server_close()
        print("✅ File server stopped")


def wait_for_service(url: str, service_name: str, max_retries: int = 30, retry_delay: float = 1.0) -> bool:
    """Wait for a service to be ready"""
    for i in range(max_retries):
        try:
            response = requests.get(f"{url}/health", timeout=2.0)
            if response.status_code == 200:
                print(f"✅ {service_name} is ready")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if i < max_retries - 1:
            time.sleep(retry_delay)
    
    print(f"❌ {service_name} is not ready after {max_retries * retry_delay}s")
    return False


def read_documents() -> List[Dict[str, Any]]:
    """Read all PDF files from documents directory"""
    documents = []
    
    if not DOCUMENTS_DIR.exists():
        print(f"❌ Documents directory not found: {DOCUMENTS_DIR}")
        print(f"   Please create the directory and add PDF files for testing.")
        return documents
    
    pdf_files = list(DOCUMENTS_DIR.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files found in {DOCUMENTS_DIR}")
        print(f"   Please add at least one PDF file to test the pipeline.")
        print(f"   Supported formats: .pdf")
        return documents
    
    # Validate PDF files
    valid_pdfs = []
    for pdf_file in pdf_files:
        if pdf_file.stat().st_size == 0:
            print(f"⚠️  Skipping empty file: {pdf_file.name}")
            continue
        if pdf_file.stat().st_size > 100 * 1024 * 1024:  # 100MB limit
            print(f"⚠️  Skipping large file (>100MB): {pdf_file.name}")
            continue
        valid_pdfs.append(pdf_file)
    
    if not valid_pdfs:
        print(f"❌ No valid PDF files found after validation")
        return documents
    
    for i, pdf_file in enumerate(valid_pdfs, 1):
        filename = pdf_file.name
        url = f"{FILE_SERVER_URL}/documents/{filename}"
        
        documents.append({
            "document_id": f"doc_{i}",
            "name": filename,
            "url": url,
            "type": "application/pdf",
            "indexed": True
        })
    
    print(f"✅ Found {len(documents)} valid document(s)")
    return documents


def read_fields() -> List[Dict[str, Any]]:
    """Read fields from JSON file"""
    if not FIELDS_FILE.exists():
        print(f"❌ Fields file not found: {FIELDS_FILE}")
        print(f"   Please create the file with the following structure:")
        print(f"   {{")
        print(f"     \"fields\": [")
        print(f"       {{")
        print(f"         \"label\": \"Field Name\",")
        print(f"         \"apiName\": null,")
        print(f"         \"type\": \"text|picklist|radio|number|textarea\",")
        print(f"         \"required\": true,")
        print(f"         \"possibleValues\": [],")
        print(f"         \"defaultValue\": null")
        print(f"       }}")
        print(f"     ]")
        print(f"   }}")
        return []
    
    try:
        with open(FIELDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate structure
        if not isinstance(data, dict):
            print(f"❌ Invalid structure: root must be an object")
            return []
        
        if "fields" not in data:
            print(f"❌ Invalid structure: missing 'fields' key")
            return []
        
        fields = data.get("fields", [])
        if not isinstance(fields, list):
            print(f"❌ Invalid structure: 'fields' must be an array")
            return []
        
        if len(fields) == 0:
            print(f"⚠️  Warning: No fields defined in {FIELDS_FILE}")
        
        # Validate each field
        valid_fields = []
        for i, field in enumerate(fields):
            if not isinstance(field, dict):
                print(f"⚠️  Skipping invalid field at index {i}: not an object")
                continue
            if "label" not in field:
                print(f"⚠️  Skipping invalid field at index {i}: missing 'label'")
                continue
            valid_fields.append(field)
        
        print(f"✅ Loaded {len(valid_fields)} valid field(s) from {FIELDS_FILE}")
        if len(valid_fields) < len(fields):
            print(f"⚠️  {len(fields) - len(valid_fields)} field(s) were skipped due to validation errors")
        
        return valid_fields
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {FIELDS_FILE}: {e}")
        print(f"   Please check the JSON syntax and try again.")
        return []
    except Exception as e:
        print(f"❌ Error reading {FIELDS_FILE}: {e}")
        return []


def setup_test_data(record_id: str, documents: List[Dict], fields: List[Dict]) -> bool:
    """Setup test data in mock-salesforce"""
    try:
        url = f"{MOCK_SALESFORCE_URL}/api/test/setup-test-data"
        payload = {
            "record_id": record_id,
            "documents": documents,
            "fields": fields
        }
        
        print(f"📤 Setting up test data for record_id: {record_id}")
        response = requests.post(url, json=payload, timeout=10.0)
        response.raise_for_status()
        
        result = response.json()
        if result.get("status") == "success":
            print(f"✅ Test data setup successful")
            return True
        else:
            print(f"❌ Test data setup failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up test data: {e}")
        return False


def run_pipeline_test(record_id: str, user_message: str = "Extract data from documents") -> Optional[Dict[str, Any]]:
    """Run the complete pipeline test"""
    try:
        url = f"{BACKEND_MCP_URL}/api/mcp/receive-request"
        payload = {
            "record_id": record_id,
            "session_id": None,
            "user_message": user_message
        }
        
        print(f"📤 Sending request to backend-mcp...")
        print(f"   Record ID: {record_id}")
        print(f"   User message: {user_message}")
        
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=300.0)  # 5 min timeout
        elapsed_time = time.time() - start_time
        
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ Pipeline completed in {elapsed_time:.2f}s")
        return result
        
    except requests.exceptions.Timeout:
        print(f"❌ Request timeout after 300s")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Error running pipeline test: {e}")
        return None


def save_results(record_id: str, result: Dict[str, Any], documents: List[Dict], fields: List[Dict]):
    """Save test results to file"""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = RESULTS_DIR / f"test_results_{timestamp}.json"
    
    results_data = {
        "timestamp": datetime.now().isoformat(),
        "record_id": record_id,
        "documents": documents,
        "fields": fields,
        "pipeline_result": result,
        "summary": {
            "status": result.get("status", "unknown") if result else "error",
            "documents_count": len(documents),
            "fields_count": len(fields)
        }
    }
    
    try:
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Results saved to {results_file}")
    except Exception as e:
        print(f"⚠️  Failed to save results: {e}")


def print_results(result: Dict[str, Any]):
    """Print test results in a readable format"""
    if not result:
        print("\n❌ No results to display")
        return
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    
    # Check response structure
    response_status = result.get("status", "unknown")
    print(f"Response Status: {response_status}")
    
    if response_status == "success":
        # The workflow_result is now directly in data
        workflow_data = result.get("data", {})
        
        # Extract workflow information
        workflow_status = workflow_data.get("status", "unknown")
        workflow_id = workflow_data.get("workflow_id", "unknown")
        steps_completed = workflow_data.get("steps_completed", [])
        
        print(f"Workflow Status: {workflow_status}")
        print(f"Workflow ID: {workflow_id}")
        print(f"Steps Completed: {len(steps_completed)}/{len(steps_completed)}")
        print(f"Steps: {', '.join(steps_completed)}")
        
        # Extract extracted data from response handling step
        workflow_steps_data = workflow_data.get("data", {})
        response_handling = workflow_steps_data.get("response_handling", {})
        extracted_data = response_handling.get("extracted_data", {})
        confidence_scores = response_handling.get("confidence_scores", {})
        
        # Fallback: try to get from mcp_sending step if response_handling is empty
        if not extracted_data:
            mcp_sending = workflow_steps_data.get("mcp_sending", {})
            mcp_response = mcp_sending.get("mcp_response", {})
            extracted_data = mcp_response.get("extracted_data", {})
            confidence_scores = mcp_response.get("confidence_scores", {})
        
        if extracted_data:
            print(f"\nExtracted Data ({len(extracted_data)} fields):")
            print("-" * 60)
            for field_name, value in extracted_data.items():
                confidence = confidence_scores.get(field_name, 0.0)
                print(f"  {field_name}: {value} (confidence: {confidence:.2%})")
            
            if confidence_scores:
                avg_confidence = sum(confidence_scores.values()) / len(confidence_scores)
                print(f"\nAverage Confidence: {avg_confidence:.2%}")
        else:
            print("\n⚠️  No extracted data found in response")
            print("Available workflow steps:")
            for step_name in workflow_data.keys():
                print(f"  - {step_name}")
            
            # Show a preview of the workflow data structure
            print("\nWorkflow data preview:")
            preview = json.dumps(workflow_data, indent=2, ensure_ascii=False)
            if len(preview) > 500:
                print(preview[:500] + "...")
            else:
                print(preview)
    else:
        error = result.get("error", {})
        if error:
            print(f"\nError:")
            print(f"  Code: {error.get('code', 'unknown')}")
            print(f"  Message: {error.get('message', 'Unknown error')}")
        else:
            errors = result.get("errors", [])
            if errors:
                print(f"\nErrors ({len(errors)}):")
                print("-" * 60)
                for error in errors:
                    print(f"  {error.get('step', 'unknown')}: {error.get('error', 'Unknown error')}")
    
    print("="*60)


def validate_prerequisites() -> bool:
    """Validate all prerequisites before running tests"""
    print("Validating prerequisites...")
    print("-" * 60)
    
    all_valid = True
    
    # Check documents directory
    if not DOCUMENTS_DIR.exists():
        print(f"❌ Documents directory not found: {DOCUMENTS_DIR}")
        print(f"   Please create the directory and add PDF files.")
        all_valid = False
    else:
        pdf_count = len(list(DOCUMENTS_DIR.glob("*.pdf")))
        if pdf_count == 0:
            print(f"⚠️  No PDF files found in {DOCUMENTS_DIR}")
            all_valid = False
        else:
            print(f"✅ Documents directory exists with {pdf_count} PDF file(s)")
    
    # Check fields file
    if not FIELDS_FILE.exists():
        print(f"❌ Fields file not found: {FIELDS_FILE}")
        all_valid = False
    else:
        try:
            with open(FIELDS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            fields_count = len(data.get("fields", []))
            if fields_count == 0:
                print(f"⚠️  Fields file exists but contains no fields")
                all_valid = False
            else:
                print(f"✅ Fields file exists with {fields_count} field(s)")
        except Exception as e:
            print(f"❌ Fields file exists but is invalid: {e}")
            all_valid = False
    
    # Check results directory
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✅ Results directory ready: {RESULTS_DIR}")
    
    print("-" * 60)
    return all_valid


def main():
    """Main test function"""
    print("="*60)
    print("PIPELINE END-TO-END TEST")
    print("="*60)
    print()
    
    # Validate prerequisites
    if not validate_prerequisites():
        print("\n❌ Prerequisites validation failed. Please fix the issues above and try again.")
        return 1
    
    # Start file server
    print("Starting file server...")
    if not start_file_server():
        return 1
    
    try:
        # Wait for services to be ready
        print("\nWaiting for services to be ready...")
        services_ready = True
        services_ready &= wait_for_service(MOCK_SALESFORCE_URL, "Mock Salesforce")
        services_ready &= wait_for_service(BACKEND_MCP_URL, "Backend MCP")
        services_ready &= wait_for_service(BACKEND_LANGGRAPH_URL, "Backend LangGraph")
        
        if not services_ready:
            print("\n❌ Some services are not ready. Please start them first.")
            return 1
        
        # Read test data
        print("\nReading test data...")
        documents = read_documents()
        fields = read_fields()
        
        if not documents:
            print("❌ No documents found. Please add PDF files to test-data/documents/")
            return 1
        
        if not fields:
            print("❌ No fields found. Please check test-data/fields/fields.json")
            return 1
        
        # Generate record_id
        record_id = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Setup test data in mock-salesforce
        print(f"\nSetting up test data...")
        if not setup_test_data(record_id, documents, fields):
            print("❌ Failed to setup test data")
            return 1
        
        # Run pipeline test
        print(f"\nRunning pipeline test...")
        result = run_pipeline_test(record_id)
        
        # Print and save results
        print_results(result)
        save_results(record_id, result, documents, fields)
        
        if result and result.get("status") == "success":
            print("\n✅ Test completed successfully!")
            return 0
        else:
            print("\n❌ Test completed with errors")
            return 1
            
    finally:
        # Stop file server
        stop_file_server()


if __name__ == "__main__":
    sys.exit(main())

