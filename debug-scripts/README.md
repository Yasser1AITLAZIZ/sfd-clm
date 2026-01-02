# Debug Scripts - Pipeline Step-by-Step Testing

This folder contains individual Python scripts to test each step of the data pipeline, allowing for detailed debugging and tracing of data flow.

## Overview

The pipeline processes data through 7 main steps:
1. **Mock Salesforce Retrieval** - Load documents and fields from test-data
2. **Salesforce Client Conversion** - Convert fields to internal format
3. **Preprocessing Pipeline** - Process documents and enrich fields
4. **Prompt Building** - Build prompt from processed data
5. **Prompt Optimization** - Optimize prompt for LLM
6. **MCP Formatting** - Format message for MCP protocol
7. **MCP Sending** - Send to LangGraph service

## Prerequisites

- Python 3.8+
- All project dependencies installed
- Test data files in `test-data/` directory:
  - `test-data/fields/001XX000001_fields.json`
  - `test-data/documents/001XX000001_*.pdf`
- Docker Compose services running (for HTTP tests in steps 2 and 7)

### Docker Compose Port Mapping

When services run in Docker Compose, ports are mapped as follows:
- **Mock Salesforce**: `localhost:8001` (host) → `8000` (container)
- **Backend MCP**: `localhost:8000` (host) → `8000` (container)  
- **Backend LangGraph**: `localhost:8002` (host) → `8002` (container)

**Important**: When running debug scripts from your host machine (outside Docker), use:
- Mock Salesforce: `http://localhost:8001`
- Backend LangGraph: `http://localhost:8002`

The scripts automatically use these ports, but if you get 404 errors, check:
1. Services are running: `docker-compose ps`
2. Ports are correctly mapped
3. Use the diagnostic script: `python debug-scripts/test_endpoint_connection.py`

## Scripts

### Diagnostic Scripts

#### `diagnose_mcp_extraction.py`
**Purpose**: Deep diagnostic to identify why MCP doesn't receive extracted data from LangGraph

**Usage**:
```bash
python debug-scripts/diagnose_mcp_extraction.py
```

**What it does**:
1. Sends request to LangGraph service
2. Captures and saves the full LangGraph response (`langgraph_response_*.json`)
3. **NEW**: Analyzes `filled_form_json` with per-field `quality_score` (page-based implementation)
4. **NEW**: Verifies quality-weighted merging and per-field quality scores
5. Simulates MCP extraction logic (same as `mcp_sender.py`)
6. Saves what MCP extracts (`mcp_extracted_response_*.json`)
7. Creates comparison report (`comparison_report_*.json`)

**Output files**:
- `langgraph_response_YYYYMMDD_HHMMSS.json` - Full LangGraph response
- `mcp_extracted_response_YYYYMMDD_HHMMSS.json` - What MCP extracts
- `comparison_report_YYYYMMDD_HHMMSS.json` - Comparison analysis

**Use this when**: You see that LangGraph returns data (e.g., "8 fields extracted") but MCP receives empty `extracted_data`.

**NEW Features**:
- Verifies `filled_form_json` structure with per-field `quality_score`
- Validates quality-weighted merging logic
- Checks overall `quality_score` calculation

#### `test_page_based_processing.py` ⭐ NEW
**Purpose**: Comprehensive test for page-based OCR mapping with quality-weighted merging

**Usage**:
```bash
python debug-scripts/test_page_based_processing.py
```

**What it does**:
1. Loads LangGraph format input data
2. Analyzes input structure (documents, pages, form_json)
3. Sends request to LangGraph service
4. **Verifies page-by-page processing**:
   - Checks that all fields have `quality_score`
   - Validates quality-weighted merging
   - Verifies overall `quality_score` calculation
5. Provides detailed field-by-field analysis
6. Generates comprehensive analysis report

**Output files**:
- `page_based_response_YYYYMMDD_HHMMSS.json` - Full LangGraph response
- `page_based_analysis_YYYYMMDD_HHMMSS.json` - Detailed analysis report
- `test_page_based_processing.log` - Detailed logs

**Use this when**: You want to verify the new page-based implementation is working correctly with real test data.

**Features**:
- ✅ Verifies per-field `quality_score` in `filled_form_json`
- ✅ Validates quality-weighted merging across pages
- ✅ Checks overall `quality_score` matches average of per-field scores
- ✅ Provides extraction statistics (fill rate, quality distribution)
- ✅ Shows before/after comparison for each field

### Step 1: Mock Salesforce Retrieval
```bash
python debug-scripts/step1_test_mock_salesforce_retrieval.py
```
- Tests loading documents and fields from test-data directory
- Output: `step1_output.json`, `step1_output.log`

### Step 2: Salesforce Client Fetch
```bash
python debug-scripts/step2_test_salesforce_client_fetch.py
```
- Tests HTTP fetch from Mock Salesforce service (requires service running)
- Fetches complete Salesforce data (documents + fields)
- Output: `step2_output.json`, `step2_output.log`
- **Note**: Form JSON normalization is handled in Step 3 (Preprocessing Pipeline)

### Step 3: Preprocessing Pipeline
```bash
python debug-scripts/step3_test_preprocessing_pipeline.py
```
- Tests document and field preprocessing
- Output: `step3_output.json`, `step3_output.log`

### Step 4: Prompt Building
```bash
python debug-scripts/step4_test_prompt_building.py
```
- Tests prompt construction from preprocessed data
- Output: `step4_output.json`, `step4_output.log`

### Step 5: MCP Formatting
```bash
python debug-scripts/step6_test_mcp_formatting.py
```
- Tests MCP message formatting
- Tests document serialization
- Uses prompt from Step 4 (no optimization step)
- Output: `step6_output.json`, `step6_output.log`

### Step 6: MCP Sending
```bash
python debug-scripts/step7_test_mcp_sending.py
```
- Tests conversion to LangGraph format
- Tests sending to LangGraph service (requires service running)
- **NEW**: Verifies `filled_form_json` with per-field `quality_score`
- **NEW**: Validates overall `quality_score` calculation
- Output: `step7_output.json`, `step7_conversion_output.json`, `step7_output.log`

## Running All Steps

To run all steps in sequence:

```bash
# Activate virtual environment first
# For backend-mcp scripts:
cd backend-mcp
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Then run each step
cd ..
python debug-scripts/step1_test_mock_salesforce_retrieval.py
python debug-scripts/step2_test_salesforce_client_fetch.py
python debug-scripts/step3_test_preprocessing_pipeline.py
python debug-scripts/step4_test_prompt_building.py
python debug-scripts/step6_test_mcp_formatting.py
python debug-scripts/step7_test_mcp_sending.py
```

## Output Files

Each script generates:
- `stepN_output.json` - Main output data
- `stepN_output.log` - Detailed logs
- Additional files for specific steps (e.g., `step2_conversion_output.json`)

## Troubleshooting

### Step 1: No fields loaded
- Check that `test-data/fields/001XX000001_fields.json` exists
- Verify file naming convention: `{record_id}_fields.json` or `{record_id}.json`

### Step 2: 404 Error from Mock Salesforce
- Ensure Docker services are running: `docker-compose ps`
- Check that test-data is mounted: `docker-compose.yml` should have volume mount for `./test-data:/app/test-data:ro`
- Verify endpoint: `http://localhost:8001/mock/salesforce/get-record-data`
- Use diagnostic script: `python debug-scripts/test_endpoint_connection.py`

### Step 6: Documents have empty URL
- This was a bug in `serialize_documents_for_mcp()` - should be fixed
- Check that documents from Step 3 have valid URLs
- Verify document serialization handles both dict and Pydantic models

### Step 7: No documents in LangGraph format
- Check Step 6 output: documents should have valid URLs
- Verify document validation in `mcp_sender.py`
- Check logs for validation errors

## Virtual Environment

The scripts use the `backend-mcp` virtual environment. Activate it before running:

```bash
cd backend-mcp
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows PowerShell
cd ..
```

## Data Flow

```
Step 1 (Mock Salesforce)
  └─> Documents + Fields from test-data
      └─> Step 2 (Client Conversion)
          └─> Fields converted to FieldToFillResponseSchema
              └─> Step 3 (Preprocessing)
                  └─> Documents processed, fields enriched
                      └─> Step 4 (Prompt Building)
                          └─> Prompt constructed
                              └─> Step 5 (Optimization)
                                  └─> Prompt optimized
                                      └─> Step 6 (MCP Formatting)
                                          └─> MCP message formatted
                                              └─> Step 7 (MCP Sending)
                                                  └─> Sent to LangGraph
```

## Notes

- Each step depends on the previous step's output
- Scripts can be run individually for debugging specific steps
- Logs are detailed to help identify where data is lost or transformed incorrectly
- All scripts use the same test record ID: `001XX000001`

## New Features (Page-Based Implementation)

The debug scripts have been updated to verify the new page-based OCR mapping implementation:

### What's New:
1. **Per-Field Quality Score Verification**: All scripts now check that each field in `filled_form_json` has a `quality_score` (weighted confidence)
2. **Quality-Weighted Merging Validation**: Scripts verify that quality scores are calculated correctly (confidence × page quality)
3. **Overall Quality Score Validation**: Scripts verify that the overall `quality_score` matches the average of per-field quality scores
4. **Input/Output Logging**: Enhanced logging shows the structure of data at each step (input → processing → output)
5. **Page-by-Page Processing Test**: New `test_page_based_processing.py` script provides comprehensive testing

### Updated Scripts:
- `diagnose_mcp_extraction.py` - Now analyzes `filled_form_json` with per-field quality scores
- `diagnose_langgraph_error.py` - Enhanced with input/output structure logging and quality score verification
- `step7_test_mcp_sending.py` - Verifies `filled_form_json` structure and quality scores

### New Script:
- `test_page_based_processing.py` - Comprehensive test for page-based processing with detailed analysis

