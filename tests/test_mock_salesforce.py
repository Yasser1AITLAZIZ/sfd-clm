"""Tests for mock Salesforce service"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path
import os
import importlib.util

project_root = Path(__file__).parent.parent
mock_path = project_root / "mock-salesforce"
mock_main_path = mock_path / "app" / "main.py"

# Clear cached modules
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith("app.") or mod_name in ["app", "app.main"]:
        del sys.modules[mod_name]

# Import app
original_cwd = os.getcwd()
try:
    os.chdir(mock_path)
    sys.path.insert(0, str(mock_path))
    
    spec = importlib.util.spec_from_file_location("mock_app", mock_main_path)
    mock_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mock_module)
    app = mock_module.app
finally:
    os.chdir(original_cwd)
    if str(mock_path) in sys.path:
        sys.path.remove(str(mock_path))

# Create test client
client = TestClient(app)


def test_get_record_data_success():
    """Test successful retrieval of record data (new format with 'fields')."""
    response = client.post(
        "/mock/salesforce/get-record-data",
        json={"record_id": "001XX000001"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert data["data"]["record_id"] == "001XX000001"
    assert "documents" in data["data"]
    assert "fields" in data["data"]
    assert isinstance(data["data"]["fields"], list)


def test_get_record_data_not_found():
    """Test record not found"""
    response = client.post(
        "/mock/salesforce/get-record-data",
        json={"record_id": "001XX999999"}
    )
    
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["error"]["code"] == "RECORD_NOT_FOUND"


def test_get_record_data_invalid_request():
    """Test invalid request (empty record_id)"""
    response = client.post(
        "/mock/salesforce/get-record-data",
        json={"record_id": ""}
    )
    
    assert response.status_code == 422  # Validation error


def test_get_record_data_missing_field():
    """Test missing record_id field"""
    response = client.post(
        "/mock/salesforce/get-record-data",
        json={}
    )
    
    assert response.status_code == 422  # Validation error


def test_get_record_data_returns_form_group_when_present():
    """When fields JSON has formGroup, response fields include formGroup (e.g. 001XX000001_fields.json)."""
    response = client.post(
        "/mock/salesforce/get-record-data",
        json={"record_id": "001XX000001"}
    )
    assert response.status_code == 200
    data = response.json()
    if data.get("status") != "success" or not data.get("data", {}).get("fields"):
        pytest.skip("Record 001XX000001 or fields file not available")
    fields = data["data"]["fields"]
    with_form_group = [f for f in fields if f.get("formGroup")]
    assert len(with_form_group) > 0, "At least one field should have formGroup when source JSON has it"
    assert all(isinstance(f["formGroup"], str) and f["formGroup"].strip() for f in with_form_group[:1])


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "mock-salesforce"

