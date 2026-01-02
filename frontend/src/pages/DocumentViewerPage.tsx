// Document Processing View Page - Salesforce Lightning Theme
import { useState, useEffect } from 'react';
import { useWorkflowStatus } from '../hooks/useWorkflowStatus';
import { usePipelineExecution } from '../hooks/usePipelineExecution';
import { useFormData } from '../hooks/useFormData';

export function DocumentViewerPage() {
  const [selectedField, setSelectedField] = useState<string | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null);
  const { workflowId } = usePipelineExecution();
  const { data: workflowStatus, isLoading, error } = useWorkflowStatus(workflowId, !!workflowId);
  const { data: formData } = useFormData('001XX000001');

  // Debug logging
  useEffect(() => {
    if (workflowId) {
      console.log('[DocumentViewerPage] WorkflowId:', workflowId);
    }
    if (workflowStatus) {
      console.log('[DocumentViewerPage] WorkflowStatus:', {
        status: workflowStatus.status,
        stepsCount: workflowStatus.steps?.length || 0,
        preprocessingStep: workflowStatus.steps?.find(s => s.step_name === 'preprocessing'),
      });
    }
    if (error) {
      console.error('[DocumentViewerPage] Error fetching workflow status:', error);
    }
  }, [workflowId, workflowStatus, error]);

  // Extract data from workflow steps if available - only show if workflow has actually been executed
  const hasWorkflowData = !!workflowStatus && 
                         workflowStatus.status !== 'pending' && 
                         workflowStatus.steps && 
                         workflowStatus.steps.length > 0 &&
                         workflowStatus.steps.some(step => step.status === 'completed' || step.status === 'in_progress');
  
  // Extract documents from preprocessing step or form data
  const preprocessingStep = workflowStatus?.steps?.find(s => s.step_name === 'preprocessing');
  // Try multiple paths to find documents - check preprocessed_data structure
  const documentsData = 
    preprocessingStep?.output_data?.documents ||  // From output_data directly
    preprocessingStep?.output_data?.preprocessed_data?.processed_documents ||  // From preprocessed_data.processed_documents
    preprocessingStep?.output_data?.preprocessed_data?.documents ||  // From preprocessed_data.documents (fallback)
    preprocessingStep?.input_data?.salesforce_data?.documents ||  // From input salesforce_data
    preprocessingStep?.input_data?.documents ||  // From input_data directly
    formData?.documents || [];  // Fallback to formData
  
  // Extract OCR text from preprocessing step
  const ocrTextData = preprocessingStep?.output_data?.ocr_text || 
                     preprocessingStep?.input_data?.ocr_text || '';
  
  // Extract field mappings from response_handling or mcp_sending step
  const responseStep = workflowStatus?.steps?.find(s => s.step_name === 'response_handling');
  const mcpStep = workflowStatus?.steps?.find(s => s.step_name === 'mcp_sending');
  const fieldMappingsData = responseStep?.output_data?.field_mappings || 
                           mcpStep?.output_data?.mcp_response?.field_mappings ||
                           responseStep?.input_data?.field_mappings ||
                           mcpStep?.input_data?.mcp_response?.field_mappings || [];

  // Convert documents to display format
  const documents = documentsData.map((doc: any, index: number) => ({
    id: doc.document_id || `doc_${index + 1}`,
    name: doc.name || 'Unknown document',
    url: doc.url || '',
    pages: doc.pages || 1,
    type: doc.type || 'application/pdf',
  }));

  const ocrText = ocrTextData || '';

  const fieldMappings = fieldMappingsData.length > 0 ? fieldMappingsData : [];

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800 border-green-300';
    if (confidence >= 0.5) return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    return 'bg-red-100 text-red-800 border-red-300';
  };

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-8 border border-gray-200/50">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent mb-2">
              Document Processing View
            </h1>
            <p className="text-gray-600 text-lg">View OCR text and field mappings</p>
          </div>
          {hasWorkflowData && (
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <div className="text-2xl font-bold text-blue-600">{documents.length}</div>
                <div className="text-sm text-gray-600">Document{documents.length > 1 ? 's' : ''}</div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-indigo-600">{fieldMappings.length}</div>
                <div className="text-sm text-gray-600">Field Mapping{fieldMappings.length > 1 ? 's' : ''}</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Three-Column Layout */}
      {isLoading ? (
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-12 border border-gray-200/50">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Loading Document Data...</h3>
            <p className="text-gray-600">Fetching workflow status...</p>
          </div>
        </div>
      ) : error ? (
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-12 border border-red-200/50">
          <div className="text-center">
            <svg className="w-16 h-16 mx-auto text-red-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="text-xl font-semibold text-red-900 mb-2">Error Loading Document Data</h3>
            <p className="text-gray-600 mb-2">{error.message}</p>
            {workflowId && (
              <p className="text-sm text-gray-500">Workflow ID: {workflowId}</p>
            )}
          </div>
        </div>
      ) : !hasWorkflowData ? (
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-12 border border-gray-200/50">
          <div className="text-center">
            <svg className="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">No Document Processing Data</h3>
            <p className="text-gray-600">Execute a workflow from the Form Visualization page to see document processing results here.</p>
            {workflowId && (
              <p className="text-sm text-gray-500 mt-2">Workflow ID: {workflowId} (No data found)</p>
            )}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Column 1: Document List */}
          <div className="lg:col-span-3">
            <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50 sticky top-24">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <svg className="w-6 h-6 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Documents
              </h2>
              <div className="space-y-3">
                {documents.length > 0 ? documents.map((doc: { id: string; name: string; url: string; pages: number; type: string }) => (
                  <div
                    key={doc.id}
                    className={`border-2 rounded-xl p-4 cursor-pointer transition-all duration-200 ${
                      selectedDocument === doc.id
                        ? 'border-blue-500 bg-blue-50 shadow-md'
                        : 'border-gray-200 hover:border-blue-300 hover:shadow-md'
                    }`}
                    onClick={() => setSelectedDocument(doc.id)}
                  >
                    <div className="flex items-start space-x-3">
                      <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                        </svg>
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-sm text-gray-900 truncate">{doc.name}</h3>
                        <div className="flex items-center space-x-2 mt-1">
                          <span className="text-xs text-gray-500">{doc.pages} page{doc.pages > 1 ? 's' : ''}</span>
                          <span className="text-xs text-gray-400">•</span>
                          <span className="text-xs text-gray-500">{doc.type.split('/')[1]?.toUpperCase()}</span>
                        </div>
                        <a
                          href={doc.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-2 inline-flex items-center text-xs font-medium text-blue-600 hover:text-blue-800"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                          View Document
                        </a>
                      </div>
                    </div>
                  </div>
                )) : (
                  <div className="text-center py-8 text-gray-500">
                    <p>No documents available</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Column 2: OCR Text Viewer */}
          <div className="lg:col-span-5">
            <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <svg className="w-6 h-6 mr-2 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                OCR Text
              </h2>
              {ocrText ? (
                <>
                  <div className="bg-gray-900 rounded-xl p-4 max-h-[600px] overflow-y-auto">
                    <pre className="text-sm whitespace-pre-wrap font-mono text-gray-100 leading-relaxed">
                      {ocrText}
                    </pre>
                  </div>
                  <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
                    <span>Page 1 of 1</span>
                    <span>{ocrText.length} characters</span>
                  </div>
                </>
              ) : (
                <div className="bg-gray-50 rounded-xl p-8 text-center text-gray-500">
                  <p>No OCR text available</p>
                </div>
              )}
            </div>
          </div>

          {/* Column 3: Field Mappings */}
          <div className="lg:col-span-4">
            <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <svg className="w-6 h-6 mr-2 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
                Field Mappings
              </h2>
              <div className="space-y-4 max-h-[600px] overflow-y-auto">
                {fieldMappings.length > 0 ? fieldMappings.map((mapping: any, index: number) => {
                  const isSelected = selectedField === mapping.field_label;
                  return (
                    <div
                      key={index}
                      className={`border-2 rounded-xl p-4 cursor-pointer transition-all duration-200 ${
                        isSelected
                          ? 'border-blue-500 bg-blue-50 shadow-md'
                          : 'border-gray-200 hover:border-blue-300 hover:shadow-md'
                      }`}
                      onClick={() => setSelectedField(mapping.field_label)}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="font-bold text-gray-900">{mapping.field_label}</h3>
                        <div className="flex items-center space-x-2">
                          {mapping.source_page && (
                            <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium">
                              Page {mapping.source_page}
                            </span>
                          )}
                          <span className={`px-3 py-1 rounded-lg text-xs font-bold border-2 ${getConfidenceColor(mapping.confidence || 0)}`}>
                            {((mapping.confidence || 0) * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 border border-gray-200">
                        {mapping.ocr_text}
                      </div>
                      {isSelected && (
                        <div className="mt-3 pt-3 border-t border-blue-200">
                          <div className="flex items-center text-xs text-blue-700">
                            <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                            </svg>
                            <span>Selected - Highlighted in OCR text</span>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                }) : (
                  <div className="text-center py-8 text-gray-500">
                    <p>No field mappings available</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
