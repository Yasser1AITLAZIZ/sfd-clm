# Test Pipeline Summary

## Overview

This test suite validates the complete OptiClaims pipeline from steps 3 to 7, including:
- Mock Salesforce endpoints
- MCP endpoints
- Workflow orchestrator
- Preprocessing pipeline
- Prompt building
- MCP communication

## Test Files

### 1. `test_pipeline_simple.py` ⭐ **START HERE**
**Purpose:** Quick validation of main endpoints
**Requirements:** Both services running
**Time:** ~10 seconds
**Best for:** Quick sanity check

**Tests:**
- Health checks
- Mock Salesforce - Get Record Data
- Mock Apex - Send User Request
- MCP - Receive Request (New Session)
- MCP - Receive Request (Continuation)

### 2. `test_pipeline_e2e.py`
**Purpose:** Complete end-to-end test with detailed results
**Requirements:** Both services running, SQLite database accessible
**Time:** ~30 seconds
**Best for:** Full validation before deployment

**Tests:**
- All endpoints from simple test
- Task status endpoint
- Detailed logging and error reporting
- Generates `test_results.json`

### 3. `test_workflow_components.py`
**Purpose:** Test individual workflow components
**Requirements:** No services needed (unit tests)
**Time:** ~5 seconds
**Best for:** Debugging specific components

**Tests:**
- Document Preprocessor
- Fields Preprocessor
- Preprocessing Pipeline
- Prompt Builder
- Prompt Optimizer
- MCP Message Formatter

### 4. `test_data_generator.py`
**Purpose:** Utility for generating fake test data
**Usage:** Import and use in other tests or scripts

## Test Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Test Pipeline                        │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  1. Health Checks                 │
        │     - Mock Salesforce (8001)      │
        │     - Backend MCP (8000)          │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  2. Mock Salesforce               │
        │     - Get Record Data             │
        │     - Send User Request           │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  3. MCP Endpoints                 │
        │     - Request Salesforce Data     │
        │     - Receive Request (New)       │
        │     - Receive Request (Continue)  │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  4. Workflow Orchestrator         │
        │     - Validation & Routing        │
        │     - Preprocessing               │
        │     - Prompt Building             │
        │     - MCP Sending                 │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  5. Task Status                   │
        │     - Check async task status     │
        └───────────────────────────────────┘
```

## Running Tests

### Quick Start (Recommended)

```bash
# 1. Start services
./tests/start_services.sh    # Unix/Linux/Mac
# OR
tests\start_services.bat     # Windows

# 2. Run quick test
python tests/test_pipeline_simple.py
```

### Full Test Suite

```bash
# Run all tests
python tests/test_pipeline_e2e.py

# Run component tests (no services needed)
python tests/test_workflow_components.py
```

## Expected Results

### Successful Test Output

```
🚀 Quick Pipeline Test

1. Testing health endpoints...
   ✅ Both services are healthy

2. Testing Mock Salesforce - Get Record Data...
   ✅ Success: 3 documents, 5 fields

3. Testing Mock Apex - Send User Request...
   ✅ Success: Request ID = abc-123-def

4. Testing MCP - Receive Request (New Session)...
   ✅ Success: Workflow ID = xyz-789, Status = completed

5. Testing MCP - Receive Request (Continuation)...
   ✅ Success: Continuation workflow completed

✨ Quick test completed!
```

## Test Data

The tests use fake data from:
- **Mock Records:** `mock-salesforce/app/data/mock_records.py`
- **User Requests:** `mock-salesforce/app/data/mock_user_requests.py`
- **Dynamic Generator:** `tests/test_data_generator.py`

### Sample Test Data

**Record IDs:**
- `001XXXX`
- `001YYYY`
- `001ZZZZ`

**User Requests:**
- "Remplis tous les champs manquants"
- "Quel est le montant sur la facture ?"
- "Corrige la date, elle semble incorrecte"
- "Extraire les informations du bénéficiaire"

## Troubleshooting

### Common Issues

1. **Services not running**
   - Check ports 8000 and 8001
   - Verify services started correctly
   - Check service logs

2. **SQLite database errors**
   - Ensure the `backend-mcp/data/` directory exists and is writable
   - Check `SESSION_DB_PATH` in configuration
   - Verify SQLite is accessible (included in Python)

3. **Import errors**
   - Run from project root directory
   - Check Python path includes project root
   - Verify all dependencies installed

4. **Timeout errors**
   - Increase timeout values in test files
   - Check network connectivity
   - Verify services are responding

## Test Coverage

| Component | Test Coverage | Status |
|-----------|--------------|--------|
| Mock Salesforce Endpoints | ✅ Full | Complete |
| Mock Apex Endpoints | ✅ Full | Complete |
| MCP Receive Request | ✅ Full | Complete |
| MCP Request Data | ✅ Full | Complete |
| Workflow Orchestrator | ✅ Full | Complete |
| Document Preprocessor | ✅ Full | Complete |
| Fields Preprocessor | ✅ Full | Complete |
| Preprocessing Pipeline | ✅ Full | Complete |
| Prompt Builder | ✅ Full | Complete |
| Prompt Optimizer | ✅ Full | Complete |
| MCP Client | ✅ Full | Complete |
| MCP Formatter | ✅ Full | Complete |
| MCP Sender | ✅ Partial | Needs Langgraph backend |
| Task Queue | ✅ Full | Complete |

## Next Steps

After successful tests:
1. ✅ Review test results in `test_results.json`
2. ✅ Check service logs for warnings
3. ✅ Test with different record_ids
4. ⏭️ Integrate with Langgraph backend (Step 8)
5. ⏭️ Add performance tests
6. ⏭️ Add load tests

## Notes

- Tests use fake/mock data - no real Salesforce connection needed
- SQLite is used for session storage (included in Python)
- Langgraph backend integration tests will be added in Step 8
- All tests include defensive error handling and logging

