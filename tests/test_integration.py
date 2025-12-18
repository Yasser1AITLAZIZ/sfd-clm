"""Integration tests"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path
import os
import importlib.util

project_root = Path(__file__).parent.parent
mock_path = project_root / "mock-salesforce"
mcp_path = project_root / "backend-mcp"
mock_main_path = mock_path / "app" / "main.py"
mcp_main_path = mcp_path / "app" / "main.py"

# Clear any cached modules - be more aggressive
for module_name in list(sys.modules.keys()):
    if module_name.startswith("app.") or module_name == "app":
        del sys.modules[module_name]

# Import mock app FIRST
original_cwd = os.getcwd()
try:
    os.chdir(mock_path)
    sys.path.insert(0, str(mock_path))
    # Clear any cached modules again before import
    for module_name in list(sys.modules.keys()):
        if module_name.startswith("app.") or module_name == "app":
            del sys.modules[module_name]
    spec = importlib.util.spec_from_file_location("mock_app_main", mock_main_path)
    mock_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mock_module)
    mock_app = mock_module.app
finally:
    os.chdir(original_cwd)
    if str(mock_path) in sys.path:
        sys.path.remove(str(mock_path))

# Clear cached modules again before importing MCP app
for module_name in list(sys.modules.keys()):
    if module_name.startswith("app.") or module_name == "app":
        del sys.modules[module_name]

# Import MCP app
try:
    os.chdir(mcp_path)
    sys.path.insert(0, str(mcp_path))
    # Clear any cached modules again before import
    for module_name in list(sys.modules.keys()):
        if module_name.startswith("app.") or module_name == "app":
            del sys.modules[module_name]
    spec = importlib.util.spec_from_file_location("mcp_app_main", mcp_main_path)
    mcp_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mcp_module)
    mcp_app = mcp_module.app
finally:
    os.chdir(original_cwd)
    if str(mcp_path) in sys.path:
        sys.path.remove(str(mcp_path))


def test_integration_flow():
    """Test full integration flow: mock -> mcp"""
    # #region agent log
    with open(r"c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log", "a") as f:
        import json
        from datetime import datetime
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"test_integration.py:51","message":"Before mock request","data":{"routes":[r.path for r in mock_app.routes]},"timestamp":int(datetime.now().timestamp()*1000)}) + "\n")
    # #endregion
    # First, test mock service
    mock_test_client = TestClient(mock_app)
    # #region agent log
    with open(r"c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log", "a") as f:
        import json
        from datetime import datetime
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"test_integration.py:54","message":"About to make request","data":{"url":"/mock/salesforce/get-record-data","record_id":"001XX000001"},"timestamp":int(datetime.now().timestamp()*1000)}) + "\n")
    # #endregion
    mock_response = mock_test_client.post(
        "/mock/salesforce/get-record-data",
        json={"record_id": "001XX000001"}
    )
    # #region agent log
    with open(r"c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log", "a") as f:
        import json
        from datetime import datetime
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"test_integration.py:60","message":"After mock request","data":{"status_code":mock_response.status_code,"response_text":mock_response.text[:200] if hasattr(mock_response, 'text') else str(mock_response)},"timestamp":int(datetime.now().timestamp()*1000)}) + "\n")
    # #endregion
    
    assert mock_response.status_code == 200
    mock_data = mock_response.json()
    assert mock_data["status"] == "success"
    
    # Import MCP modules for creating mock data and mocking
    original_cwd = os.getcwd()
    try:
        os.chdir(mcp_path)
        sys.path.insert(0, str(mcp_path))
        
        from app.models.schemas import SalesforceDataResponseSchema, DocumentResponseSchema, FieldToFillResponseSchema
        import app.services.session_router as session_router_module
        
        # Create mock Salesforce data for MCP service
        mock_salesforce_data = SalesforceDataResponseSchema(
            record_id="001XX000001",
            record_type="Claim",
            documents=[
                DocumentResponseSchema(
                    document_id="doc_1",
                    name="test.pdf",
                    url="https://example.com/test.pdf",
                    type="application/pdf",
                    indexed=True
                )
            ],
            fields_to_fill=[
                FieldToFillResponseSchema(
                    field_name="montant_total",
                    field_type="currency",
                    value=None,
                    required=True,
                    label="Montant total"
                )
            ]
        )
        
        # Mock fetch_salesforce_data to use the mock data
        original_fetch = session_router_module.fetch_salesforce_data
        async def mock_fetch(record_id):
            return mock_salesforce_data
        
        session_router_module.fetch_salesforce_data = mock_fetch
        
        try:
            # Then test MCP service with mocked data
            mcp_test_client = TestClient(mcp_app)
            mcp_response = mcp_test_client.post(
                "/api/mcp/receive-request",
                json={
                    "record_id": "001XX000001",
                    "session_id": None,
                    "user_message": "Remplis tous les champs"
                }
            )
            
            # Should return 200 with mocked data
            assert mcp_response.status_code == 200
            mcp_data = mcp_response.json()
            assert "status" in mcp_data
            assert mcp_data["status"] == "success"
        finally:
            # Restore original function
            session_router_module.fetch_salesforce_data = original_fetch
    finally:
        os.chdir(original_cwd)
        if str(mcp_path) in sys.path:
            sys.path.remove(str(mcp_path))

