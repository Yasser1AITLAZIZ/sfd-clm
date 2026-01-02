# OptiClaims Frontend Dashboard

React + TypeScript frontend application for visualizing and monitoring the OptiClaims pipeline end-to-end.

## Features

### Phase 1: Core Features

1. **Form Visualization Page** (`/`)
   - Display form fields from mock Salesforce
   - Show all 13 fields with their properties (label, type, required, possibleValues, defaultValue)
   - Document upload with drag & drop
   - Pre-fill form fields with `dataValue_target_AI` values after pipeline execution
   - Visual indicators for filled vs unfilled fields
   - Confidence and quality score badges
   - Field comparison view (before/after)

2. **Real-time Workflow Orchestration Page** (`/workflow`)
   - Visual timeline of all 8 workflow steps
   - Real-time status updates via polling
   - Progress percentage calculation
   - Error highlighting with details
   - Step timing information

### Phase 2: Enhanced Visualization

3. **Data Transformation Viewer** (`/dataflow`)
   - Step-by-step data viewer showing transformations
   - Collapsible sections for each step
   - JSON viewer with syntax highlighting
   - Data size indicators

4. **Document Processing View** (`/documents`)
   - Document list with metadata
   - OCR text extraction display
   - Field-to-OCR mapping visualization

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend services running:
  - Backend MCP (Port 8000)
  - Mock Salesforce (Port 8001)
  - Backend LangGraph (Port 8002)

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

The application will be available at `http://localhost:5173` (Vite default port).

### Build

```bash
npm run build
```

## Environment Variables

Create a `.env` file in the `frontend/` directory:

```
VITE_API_BASE_URL=http://localhost:8000
VITE_MOCK_SALESFORCE_URL=http://localhost:8001
VITE_LANGGRAPH_URL=http://localhost:8002
```

## Field Matching

The frontend uses exact label matching (case-sensitive) to match input form fields with output filled form fields. The matching algorithm:

1. Matches fields by exact `label` string
2. Maps `dataValue_target_AI` from output to input fields
3. Displays confidence and quality scores per field
4. Handles "non disponible" values with warning indicators
5. Validates all 13 input fields are accounted for

## API Endpoints Used

- `POST /mock/salesforce/get-record-data` - Get form structure
- `POST /api/mcp/receive-request` - Execute pipeline
- `GET /api/workflow/status/{workflow_id}` - Get workflow status (real-time polling)
- `GET /api/workflow/{workflow_id}/steps` - Get detailed step information

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── FormVisualization/
│   │   ├── WorkflowOrchestration/
│   │   ├── DataFlow/
│   │   ├── DocumentProcessing/
│   │   └── common/
│   ├── pages/               # Page components
│   ├── services/            # API services
│   ├── types/               # TypeScript types
│   ├── hooks/               # React hooks
│   └── utils/               # Utility functions
├── package.json
└── vite.config.ts
```

## Key Features

### Field Matching Utility

The `fieldMatcher.ts` utility ensures:
- Exact label matching (case-sensitive)
- Proper mapping of `dataValue_target_AI` values
- Confidence and quality score display
- Error handling for unmatched fields

### Real-time Updates

Workflow status is polled:
- Every 1 second during active workflow
- Every 5 seconds for completed workflows

## Troubleshooting

### Field Not Found Errors

If you see "Field not found in output" warnings:
1. Check that the pipeline executed successfully
2. Verify the output contains `filled_form_json` array
3. Ensure field labels match exactly (case-sensitive)

### API Connection Issues

If API calls fail:
1. Verify backend services are running
2. Check environment variables in `.env`
3. Verify CORS is enabled on backend services
