// Custom hook to extract workflow data (documents, OCR text, field mappings)
import { useMemo } from 'react';
import type { WorkflowStatusResponse } from '../types/workflow';
import type { FormDataResponse } from '../types/form';

interface ExtractedWorkflowData {
  documents: Array<{
    id: string;
    name: string;
    url: string;
    pages: number;
    type: string;
  }>;
  ocrText: string;
  fieldMappings: Array<{
    field_label: string;
    ocr_text: string;
    confidence: number;
    source_page?: number;
    apiName?: string;
  }>;
}

export function useWorkflowData(
  workflowStatus: WorkflowStatusResponse | undefined,
  formData?: FormDataResponse | null
): ExtractedWorkflowData {
  return useMemo(() => {
    // PRIORITY 1: If no workflow, use formData directly (uploaded documents from test-data/documents/)
    if (!workflowStatus && formData) {
      const documentsData = formData.documents || [];
      const documents = documentsData.map((doc: any, index: number) => ({
        id: doc.document_id || doc.id || `doc_${index + 1}`,
        name: doc.name || doc.filename || 'Unknown document',
        url: doc.url || '',
        pages: doc.pages || 1,
        type: doc.type || 'application/pdf',
      }));
      
      console.log('[useWorkflowData] No workflow - using formData documents from test-data/documents/:', documents.length);
      
      return {
        documents,
        ocrText: '',
        fieldMappings: [],
      };
    }

    // PRIORITY 2: If workflow exists, try to extract from workflow steps first
    if (!workflowStatus) {
      return { documents: [], ocrText: '', fieldMappings: [] };
    }

    // Extract preprocessing step
    const preprocessingStep = workflowStatus.steps?.find(s => s.step_name === 'preprocessing');
    const responseStep = workflowStatus.steps?.find(s => s.step_name === 'response_handling');
    const mcpStep = workflowStatus.steps?.find(s => s.step_name === 'mcp_sending');

    // ========== EXTRACT DOCUMENTS ==========
    let documentsData: any[] = [];

    // Try all possible paths for documents from workflow
    if (preprocessingStep?.output_data) {
      // Path 1: output_data.documents directly
      if (Array.isArray(preprocessingStep.output_data.documents)) {
        documentsData = preprocessingStep.output_data.documents;
      }
      // Path 2: output_data.preprocessed_data.processed_documents
      else if (preprocessingStep.output_data.preprocessed_data?.processed_documents) {
        documentsData = Array.isArray(preprocessingStep.output_data.preprocessed_data.processed_documents)
          ? preprocessingStep.output_data.preprocessed_data.processed_documents
          : [];
      }
      // Path 3: output_data.preprocessed_data.documents
      else if (preprocessingStep.output_data.preprocessed_data?.documents) {
        documentsData = Array.isArray(preprocessingStep.output_data.preprocessed_data.documents)
          ? preprocessingStep.output_data.preprocessed_data.documents
          : [];
      }
    }

    // Path 4: input_data.salesforce_data.documents
    if (documentsData.length === 0 && preprocessingStep?.input_data?.salesforce_data?.documents) {
      documentsData = Array.isArray(preprocessingStep.input_data.salesforce_data.documents)
        ? preprocessingStep.input_data.salesforce_data.documents
        : [];
    }

    // Path 5: input_data.documents
    if (documentsData.length === 0 && preprocessingStep?.input_data?.documents) {
      documentsData = Array.isArray(preprocessingStep.input_data.documents)
        ? preprocessingStep.input_data.documents
        : [];
    }
    
    // Path 6: formData.documents (FALLBACK: Use formData if workflow doesn't have documents)
    // This ensures uploaded documents from test-data/documents/ appear even if workflow hasn't processed them yet
    if (documentsData.length === 0 && formData?.documents && Array.isArray(formData.documents)) {
      documentsData = formData.documents;
      console.log('[useWorkflowData] Workflow has no documents - using formData from test-data/documents/:', documentsData.length);
    }

    // Convert documents to display format
    const documents = documentsData.map((doc: any, index: number) => ({
      id: doc.document_id || doc.id || `doc_${index + 1}`,
      name: doc.name || doc.filename || doc.metadata?.filename || 'Unknown document',
      url: doc.url || doc.metadata?.url || '',
      pages: doc.pages || doc.page_count || doc.metadata?.page_count || 1,
      type: doc.type || doc.metadata?.mime || doc.content_type || 'application/pdf',
    }));

    // ========== EXTRACT OCR TEXT ==========
    let ocrText = '';

    // Path 1: preprocessing output_data.ocr_text
    if (preprocessingStep?.output_data?.ocr_text) {
      ocrText = String(preprocessingStep.output_data.ocr_text);
    }
    // Path 2: preprocessing output_data.preprocessed_data.ocr_text
    else if (preprocessingStep?.output_data?.preprocessed_data?.ocr_text) {
      ocrText = String(preprocessingStep.output_data.preprocessed_data.ocr_text);
    }
    // Path 3: preprocessing input_data.ocr_text
    else if (preprocessingStep?.input_data?.ocr_text) {
      ocrText = String(preprocessingStep.input_data.ocr_text);
    }
    // Path 4: Extract from document pages
    else if (documentsData.length > 0) {
      // Try to extract OCR text from all pages of all documents
      const allPagesText: string[] = [];
      
      documentsData.forEach((doc: any) => {
        if (doc.pages && Array.isArray(doc.pages)) {
          doc.pages.forEach((page: any) => {
            if (page.ocr_text) {
              allPagesText.push(String(page.ocr_text));
            }
          });
        }
      });

      if (allPagesText.length > 0) {
        ocrText = allPagesText.join('\n\n--- Page Break ---\n\n');
      }
    }

    // ========== EXTRACT FIELD MAPPINGS ==========
    let fieldMappings: ExtractedWorkflowData['fieldMappings'] = [];

    // Path 1: response_handling.output_data.field_mappings
    if (responseStep?.output_data?.field_mappings) {
      const mappings = responseStep.output_data.field_mappings;
      if (Array.isArray(mappings)) {
        fieldMappings = mappings.map((m: any) => ({
          field_label: m.field_label || m.label || m.field_name || 'Unknown',
          ocr_text: m.ocr_text || m.value || m.dataValue_target_AI || '',
          confidence: m.confidence || m.quality_score || 0,
          source_page: m.source_page || m.page_number,
          apiName: m.apiName || m.api_name,
        }));
      } else if (typeof mappings === 'object') {
        // Convert object to array
        fieldMappings = Object.entries(mappings).map(([key, value]: [string, any]) => ({
          field_label: key,
          ocr_text: typeof value === 'string' ? value : value?.value || value?.ocr_text || '',
          confidence: typeof value === 'object' ? (value.confidence || value.quality_score || 0) : 0,
          source_page: typeof value === 'object' ? value.source_page : undefined,
          apiName: typeof value === 'object' ? value.apiName : undefined,
        }));
      }
    }
    // Path 2: Create from filled_form_json in response_handling
    else if (responseStep?.output_data?.filled_form_json && Array.isArray(responseStep.output_data.filled_form_json)) {
      fieldMappings = responseStep.output_data.filled_form_json
        .filter((f: any) => f.dataValue_target_AI && f.dataValue_target_AI !== 'non disponible')
        .map((f: any) => ({
          field_label: f.label || f.apiName || 'Unknown',
          ocr_text: f.dataValue_target_AI || '',
          confidence: f.confidence || f.quality_score || responseStep.output_data?.confidence_scores?.[f.apiName || f.label] || 0,
          source_page: f.source_page || f.page_number,
          apiName: f.apiName || f.api_name,
        }));
    }
    // Path 3: mcp_sending.output_data.mcp_response.field_mappings
    else if (mcpStep?.output_data?.mcp_response?.field_mappings) {
      const mappings = mcpStep.output_data.mcp_response.field_mappings;
      if (Array.isArray(mappings)) {
        fieldMappings = mappings.map((m: any) => ({
          field_label: m.field_label || m.label || m.field_name || 'Unknown',
          ocr_text: m.ocr_text || m.value || m.dataValue_target_AI || '',
          confidence: m.confidence || m.quality_score || 0,
          source_page: m.source_page || m.page_number,
          apiName: m.apiName || m.api_name,
        }));
      }
    }
    // Path 4: Create from filled_form_json in mcp_sending
    else if (mcpStep?.output_data?.mcp_response?.filled_form_json && Array.isArray(mcpStep.output_data.mcp_response.filled_form_json)) {
      fieldMappings = mcpStep.output_data.mcp_response.filled_form_json
        .filter((f: any) => f.dataValue_target_AI && f.dataValue_target_AI !== 'non disponible')
        .map((f: any) => ({
          field_label: f.label || f.apiName || 'Unknown',
          ocr_text: f.dataValue_target_AI || '',
          confidence: f.confidence || f.quality_score || mcpStep.output_data?.mcp_response?.confidence_scores?.[f.apiName || f.label] || 0,
          source_page: f.source_page || f.page_number,
          apiName: f.apiName || f.api_name,
        }));
    }

    return {
      documents,
      ocrText,
      fieldMappings,
    };
  }, [workflowStatus, formData]);
}

