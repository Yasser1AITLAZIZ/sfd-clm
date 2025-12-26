# Quick Start Guide for Pipeline Testing

## Prerequisites

1. **Python 3.11+** installed (SQLite is included)
2. **All dependencies** installed:
   ```bash
   pip install -r requirements-dev.txt
   ```

## Quick Test (Simplest)

Run the simplified test script:

```bash
python tests/test_pipeline_simple.py
```

This will:
- Check if services are running
- Test main endpoints
- Show results immediately

## Full E2E Test

### Step 1: Start Services

**Option A: Manual (recommended for debugging)**
```bash
# Terminal 1: Mock Salesforce
cd mock-salesforce
uvicorn app.main:app --port 8001 --reload

# Terminal 2: Backend MCP
cd backend-mcp
uvicorn app.main:app --port 8000 --reload

# Terminal 3: (Optional) Monitor SQLite
# The backend-mcp/data/ directory will be created automatically on first start
```

**Option B: Using script (Unix/Linux/Mac)**
```bash
chmod +x tests/start_services.sh
./tests/start_services.sh
```

### Step 2: Run Tests

```bash
# Quick test
python tests/test_pipeline_simple.py

# Full E2E test
python tests/test_pipeline_e2e.py

# Component tests (no services needed)
python tests/test_workflow_components.py
```

## Test Files

1. **test_pipeline_simple.py** - Quick validation (recommended first)
2. **test_pipeline_e2e.py** - Complete E2E test with detailed results
3. **test_workflow_components.py** - Test individual components
4. **test_data_generator.py** - Generate fake test data

## Expected Output

### Successful Test
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

✨ Quick test completed!
```

## Troubleshooting

### Services not running
```bash
# Check if ports are in use
lsof -i :8000
lsof -i :8001

# Kill processes if needed
kill -9 <PID>
```

### SQLite database error
```bash
# Check that the data directory exists
ls backend-mcp/data/

# The directory will be created automatically on first service start
# If errors persist, check SESSION_DB_PATH in configuration
```

### Import errors
Make sure you're running from the project root:
```bash
cd /path/to/sfd-clm
python tests/test_pipeline_simple.py
```

## Test Data

The tests use fake data from:
- `mock-salesforce/app/data/mock_records.py` - Mock Salesforce records
- `mock-salesforce/app/data/mock_user_requests.py` - Mock user requests
- `tests/test_data_generator.py` - Dynamic test data generation

## Next Steps

After successful tests:
1. Check `test_results.json` for detailed results
2. Review service logs for any warnings
3. Test with different record_ids and user requests
4. Integrate with actual Langgraph backend (step 8)

