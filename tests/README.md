# Pipeline E2E Tests

This directory contains end-to-end tests for the OptiClaims pipeline.

## Test Files

- `test_pipeline_e2e.py`: Main E2E test script that tests the complete pipeline
- `test_data_generator.py`: Utility for generating fake test data
- `run_pipeline_tests.sh`: Shell script to run tests (Unix/Linux/Mac)

## Prerequisites

1. **Start Mock Salesforce service:**
   ```bash
   cd mock-salesforce
   uvicorn app.main:app --port 8001 --reload
   ```

2. **Start Backend MCP service:**
   ```bash
   cd backend-mcp
   uvicorn app.main:app --port 8000 --reload
   ```

3. **SQLite session storage** : Le répertoire `backend-mcp/data/` sera créé automatiquement au premier démarrage

## Running Tests

### Option 1: Direct Python execution
```bash
python tests/test_pipeline_e2e.py
```

### Option 2: Using pytest
```bash
pytest tests/test_pipeline_e2e.py -v
```

### Option 3: Using shell script (Unix/Linux/Mac)
```bash
chmod +x tests/run_pipeline_tests.sh
./tests/run_pipeline_tests.sh
```

## Test Coverage

The E2E test covers:

1. ✅ Health check endpoints (both services)
2. ✅ Mock Salesforce - Get Record Data
3. ✅ Mock Apex - Send User Request
4. ✅ MCP - Request Salesforce Data (internal endpoint)
5. ✅ MCP - Receive Request (new session flow)
6. ✅ MCP - Receive Request (continuation flow)
7. ✅ Task Status endpoint

## Test Flow

```
1. Health Checks
   ↓
2. Mock Salesforce - Get Record Data
   ↓
3. Mock Apex - Send User Request
   ↓
4. MCP - Request Salesforce Data
   ↓
5. MCP - Receive Request (New Session)
   ↓
6. MCP - Receive Request (Continuation)
   ↓
7. Task Status Check
```

## Expected Results

All tests should pass if:
- Both services are running
- SQLite database directory is accessible (backend-mcp/data/)
- Mock data is properly configured

## Test Results

Test results are saved to `test_results.json` with detailed information about each test.

## Troubleshooting

### Service not running
- Check if services are listening on correct ports (8000, 8001)
- Verify no firewall blocking the ports

### SQLite database errors
- Ensure the `backend-mcp/data/` directory exists and is writable
- Check `SESSION_DB_PATH` in configuration

### Test failures
- Check service logs for detailed error messages
- Verify mock data exists in `mock-salesforce/app/data/mock_records.py`
- Ensure all dependencies are installed

