# Quick Start Guide

## Prerequisites

1. Backend services must be running:
   - Backend MCP on port 8000
   - Mock Salesforce on port 8001
   - Backend LangGraph on port 8002

## Starting the Frontend

```bash
cd frontend
npm install  # If not already done
npm run dev
```

The application will be available at `http://localhost:5173`

## Usage

### Form Visualization Page (`/`)

1. Enter a Record ID (default: `001XX000001`)
2. Click "Load Form Data" to fetch form structure from mock Salesforce
3. Optionally upload a document using drag & drop
4. Click "Execute Pipeline" to run the workflow
5. View pre-filled form fields with:
   - `dataValue_target_AI` values
   - Confidence scores (color-coded)
   - Quality scores
   - Visual indicators for filled/unfilled fields

### Workflow Orchestration Page (`/workflow`)

1. Enter Record ID and User Message
2. Click "Execute Workflow"
3. Monitor real-time progress:
   - Visual timeline of all 8 steps
   - Status updates (pending → in_progress → completed)
   - Progress percentage
   - Step timing information
   - Error highlighting

### Data Transformation Viewer (`/dataflow`)

View data transformations at each workflow step with collapsible JSON viewers.

### Document Processing View (`/documents`)

View document metadata, OCR text, and field-to-OCR mappings.

## Field Matching

The frontend uses **exact label matching** (case-sensitive) to match fields:
- All 13 fields from input are matched with output by exact `label`
- `dataValue_target_AI` values are correctly mapped
- Confidence and quality scores are displayed per field
- "non disponible" values are shown with warning indicators

## Troubleshooting

### Fields Not Showing

- Verify the pipeline executed successfully
- Check browser console for field matching warnings
- Ensure backend services are running

### API Connection Errors

- Verify backend services are running on correct ports
- Check CORS settings on backend
- Verify environment variables in `.env` file

