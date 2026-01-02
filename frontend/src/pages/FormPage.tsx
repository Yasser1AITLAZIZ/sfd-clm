// Form Visualization Page
import { useState, useEffect } from 'react';
import { useFormData } from '../hooks/useFormData';
import { usePipelineExecution } from '../hooks/usePipelineExecution';
import { useServiceHealth } from '../hooks/useServiceHealth';
import { FormFieldList } from '../components/FormVisualization/FormFieldList';
import { DocumentUpload } from '../components/FormVisualization/DocumentUpload';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorDisplay } from '../components/common/ErrorDisplay';
import { ServiceHealthDashboard } from '../components/common/ServiceHealthDashboard';
import { matchFields } from '../utils/fieldMatcher';
import type { MatchedField } from '../types/form';

const DEFAULT_RECORD_ID = '001XX000001';

export function FormPage() {
  const [recordId, setRecordId] = useState(DEFAULT_RECORD_ID);
  const [userMessage, setUserMessage] = useState('Remplis tous les champs manquants');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedDocument, setUploadedDocument] = useState<{ document_id: string; url: string } | null>(null);
  const [showComparison, setShowComparison] = useState(false);
  const [showHealthStatus, setShowHealthStatus] = useState(true);
  const [matchedFields, setMatchedFields] = useState<MatchedField[]>([]);
  const [rootConfidenceScores, setRootConfidenceScores] = useState<Record<string, number>>({});
  const [hasExecutedPipeline, setHasExecutedPipeline] = useState(false);

  const { data: formData, isLoading: isLoadingForm, error: formError, refetch: refetchForm } = useFormData(recordId);
  const { executeAsync, workflowId, isLoading: isExecuting, error: executionError, clearWorkflow } = usePipelineExecution();
  const { data: servicesHealth } = useServiceHealth();
  
  const allServicesHealthy = servicesHealth?.every(s => s.status === 'healthy') ?? false;

  // Check localStorage directly as fallback
  const [localWorkflowId, setLocalWorkflowId] = useState<string | null>(null);
  
  useEffect(() => {
    // Check localStorage directly
    const storedId = typeof window !== 'undefined' ? localStorage.getItem('sfd-clm-workflow-id') : null;
    setLocalWorkflowId(storedId);
    console.log('[FormPage] Current workflowId from hook:', workflowId);
    console.log('[FormPage] Current workflowId from localStorage:', storedId);
    console.log('[FormPage] hasExecutedPipeline:', hasExecutedPipeline);
  }, [workflowId, hasExecutedPipeline]);
  
  // Use either workflowId from hook or from localStorage
  const activeWorkflowId = workflowId || localWorkflowId;

  const handleRestartPipeline = () => {
    // Clear workflow ID and all related state
    clearWorkflow();
    // Reset form state
    setMatchedFields([]);
    setRootConfidenceScores({});
    setHasExecutedPipeline(false);
    // Clear any form field local values by reloading form data
    refetchForm();
    console.log('[FormPage] Pipeline restarted - all state cleared');
  };

  const handleExecutePipeline = async () => {
    if (!formData) return;

    try {
      const response = await executeAsync({
        recordId,
        sessionId: null,
        userMessage: userMessage,
      });

      console.log('Pipeline response:', response);

      // Extract filled_form_json from response
      // Response is WorkflowResponse which has filled_form_json at root level
      // or nested in data.response_handling or data.mcp_sending.mcp_response
      let filledFormJson: any[] = [];
      let confidenceScores: Record<string, number> = {};

      // Try root level first (primary location)
      if (response.filled_form_json && Array.isArray(response.filled_form_json)) {
        filledFormJson = response.filled_form_json;
        confidenceScores = response.confidence_scores || {};
        console.log('Found filled_form_json at root level:', filledFormJson.length, 'fields');
      }
      // Try response_handling
      else if (response.data?.response_handling?.filled_form_json && Array.isArray(response.data.response_handling.filled_form_json)) {
        filledFormJson = response.data.response_handling.filled_form_json;
        confidenceScores = response.data.response_handling.confidence_scores || {};
        console.log('Found filled_form_json in response_handling:', filledFormJson.length, 'fields');
      }
      // Try mcp_sending.mcp_response
      else if (response.data?.mcp_sending?.mcp_response?.filled_form_json && Array.isArray(response.data.mcp_sending.mcp_response.filled_form_json)) {
        filledFormJson = response.data.mcp_sending.mcp_response.filled_form_json;
        confidenceScores = response.data.mcp_sending.mcp_response.confidence_scores || {};
        console.log('Found filled_form_json in mcp_sending.mcp_response:', filledFormJson.length, 'fields');
      }
      // Try data directly
      else if (response.data?.filled_form_json && Array.isArray(response.data.filled_form_json)) {
        filledFormJson = response.data.filled_form_json;
        confidenceScores = response.data.confidence_scores || {};
        console.log('Found filled_form_json in data:', filledFormJson.length, 'fields');
      }
      else {
        console.warn('No filled_form_json found in response. Response structure:', {
          hasRoot: !!response.filled_form_json,
          hasResponseHandling: !!response.data?.response_handling,
          hasMcpSending: !!response.data?.mcp_sending,
          dataKeys: response.data ? Object.keys(response.data) : [],
        });
      }

      // Log field labels for debugging
      if (filledFormJson.length > 0) {
        console.log('Output field labels:', filledFormJson.map(f => f.label));
        console.log('Input field labels:', formData.fields.map(f => f.label));
      }

      // Match fields
      const matched = matchFields(formData.fields, filledFormJson);
      setRootConfidenceScores(confidenceScores);
      setMatchedFields(matched);

      // Log matching results
      const matchedCount = matched.filter(m => m.isMatched).length;
      const unmatchedCount = matched.filter(m => !m.isMatched).length;
      console.log(`Field matching: ${matchedCount} matched, ${unmatchedCount} unmatched`);
      if (unmatchedCount > 0) {
        console.warn('Unmatched fields:', matched.filter(m => !m.isMatched).map(m => m.label));
      }
      
      // Mark that pipeline has been executed
      setHasExecutedPipeline(true);
      
      // Force refetch of workflow status for other pages
      console.log('[FormPage] Pipeline executed successfully, workflowId:', response.workflow_id);
    } catch (error) {
      console.error('Pipeline execution error:', error);
    }
  };

  const displayFields = matchedFields.length > 0 ? matchedFields : formData?.fields.map(f => ({
    ...f,
    isMatched: false,
  })) || [];

  return (
    <div className="space-y-6">
      {/* Service Health Dashboard Toggle */}
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-4 border border-gray-200/50">
        <button
          onClick={() => setShowHealthStatus(!showHealthStatus)}
          className="w-full flex items-center justify-between hover:bg-gray-50/50 rounded-lg p-2 transition-colors duration-200"
        >
          <div className="flex items-center space-x-3">
            <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-lg font-semibold text-gray-900">Service Health Status</span>
            {servicesHealth && (
              <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                allServicesHealthy
                  ? 'bg-green-100 text-green-800'
                  : 'bg-red-100 text-red-800'
              }`}>
                {allServicesHealthy ? 'All Healthy' : `${servicesHealth.filter(s => s.status === 'unhealthy').length} Service${servicesHealth.filter(s => s.status === 'unhealthy').length > 1 ? 's' : ''} Down`}
              </span>
            )}
          </div>
          <svg
            className={`w-5 h-5 text-gray-500 transform transition-transform duration-200 ${
              showHealthStatus ? 'rotate-180' : ''
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* Service Health Dashboard */}
      {showHealthStatus && (
        <div className="animate-in slide-in-from-top-2 duration-200">
          <ServiceHealthDashboard />
        </div>
      )}
      
      {/* Header Section */}
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-8 border border-gray-200/50">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-gray-900 via-blue-800 to-indigo-800 bg-clip-text text-transparent mb-2">
              Form Visualization
            </h1>
            <p className="text-gray-600 text-lg">View and interact with Salesforce form fields</p>
          </div>
        </div>
      </div>

      {/* Record ID Input */}
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
        <label className="block text-sm font-semibold text-gray-700 mb-3">
          Record ID
        </label>
        <input
          type="text"
          value={recordId}
          onChange={(e) => setRecordId(e.target.value)}
          className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 text-gray-900 placeholder-gray-400"
          placeholder="Enter record ID"
        />
      </div>

      {/* User Message Input */}
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
        <label className="block text-sm font-semibold text-gray-700 mb-3">
          User Message
        </label>
        <textarea
          value={userMessage}
          onChange={(e) => setUserMessage(e.target.value)}
          className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 text-gray-900 placeholder-gray-400 resize-y"
          rows={3}
          placeholder="Enter user message (e.g., 'Remplis tous les champs manquants')"
        />
        <p className="mt-2 text-xs text-gray-500">
          This message will be used to guide the AI in filling the form fields and will appear in the Data Transformation Viewer for each step.
        </p>
      </div>

      {/* Document Upload */}
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
          <svg className="w-6 h-6 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          Document Upload
        </h2>
        <DocumentUpload
          onFileSelect={setSelectedFile}
          onUploadComplete={(documentId, url) => {
            setUploadedDocument({ document_id: documentId, url });
            console.log('[FormPage] Document uploaded successfully:', { documentId, url });
          }}
          recordId={recordId}
          disabled={isExecuting}
        />
        {selectedFile && (
          <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center text-sm text-green-800">
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="font-medium">Selected:</span>
              <span className="ml-2">{selectedFile.name}</span>
              <span className="ml-2 text-green-600">({(selectedFile.size / 1024).toFixed(2)} KB)</span>
            </div>
          </div>
        )}
        {uploadedDocument && (
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center text-sm text-blue-800">
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="font-medium">Uploaded:</span>
              <span className="ml-2">Document ID: {uploadedDocument.document_id}</span>
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons Section */}
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
          {/* Load Form Data Button */}
          <button
            onClick={() => refetchForm()}
            disabled={isLoadingForm || !recordId}
            className="flex-1 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center justify-center space-x-2"
          >
            {isLoadingForm ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Loading...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>Load Form Data</span>
              </>
            )}
          </button>

          {/* Error Display - Inline */}
          {formError && (
            <div className="flex-1">
              <ErrorDisplay error={formError} onRetry={() => refetchForm()} />
            </div>
          )}
        </div>
      </div>

      {/* Debug Info - Always visible */}
      <div className="bg-yellow-50 border-2 border-yellow-300 rounded-xl p-4 mb-4">
        <p className="text-sm font-mono text-gray-800">
          <strong>Debug:</strong> workflowId from hook: {workflowId || 'null'} | 
          localStorage: {localWorkflowId || 'null'} | 
          activeWorkflowId: {activeWorkflowId || 'null'}
        </p>
      </div>

      {/* Restart Pipeline Button - Always visible if workflow exists */}
      {activeWorkflowId ? (
        <div className="bg-gradient-to-r from-orange-50 to-red-50 backdrop-blur-sm rounded-2xl shadow-xl p-6 border-2 border-orange-400 mb-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <svg className="w-8 h-8 text-orange-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <div>
                <h3 className="text-xl font-bold text-gray-900">⚠️ Active Workflow Detected</h3>
                <p className="text-sm text-gray-700 mt-1">Clear workflow data to start fresh</p>
                <p className="text-xs text-gray-600 mt-2 font-mono bg-white/70 px-3 py-1 rounded border border-orange-200">ID: {activeWorkflowId}</p>
              </div>
            </div>
            <button
              onClick={handleRestartPipeline}
              disabled={isExecuting}
              className="w-full sm:w-auto px-8 py-3 bg-gradient-to-r from-red-600 to-orange-600 text-white font-bold rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center justify-center space-x-2 text-lg"
              title="Clear workflow and reset pipeline state"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>Restart Pipeline</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-gray-100 border border-gray-300 rounded-xl p-4 mb-6">
          <p className="text-sm text-gray-600">No active workflow detected. Execute a pipeline to see the restart button.</p>
        </div>
      )}

      {/* Execute Pipeline Button */}
      {formData && (
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
          {!allServicesHealthy && (
            <div className="mb-4 p-4 bg-yellow-50 border-2 border-yellow-200 rounded-xl">
              <div className="flex items-center text-yellow-800">
                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <span className="font-semibold">Warning: Some services are unhealthy. Pipeline execution may fail.</span>
              </div>
            </div>
          )}
          <button
            onClick={handleExecutePipeline}
            disabled={isExecuting || !formData || !allServicesHealthy || !userMessage.trim()}
            className="w-full px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center justify-center space-x-2"
          >
            {isExecuting ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Executing Pipeline...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span>Execute Pipeline</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Execution Error */}
      {executionError && (
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-red-200/50">
          <ErrorDisplay error={executionError} />
        </div>
      )}

      {/* Form Fields */}
      {isLoadingForm ? (
        <div className="flex justify-center items-center py-20 bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200/50">
          <div className="text-center">
            <LoadingSpinner size="lg" />
            <p className="mt-4 text-gray-600 font-medium">Loading form data...</p>
          </div>
        </div>
      ) : formData ? (
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-8 border border-gray-200/50">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              Form Fields
              <span className="ml-3 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-semibold">
                {displayFields.length}
              </span>
            </h2>
            <label className="flex items-center cursor-pointer group">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={showComparison}
                  onChange={(e) => setShowComparison(e.target.checked)}
                  className="sr-only"
                />
                <div className={`block w-14 h-8 rounded-full transition-colors duration-200 ${
                  showComparison ? 'bg-blue-600' : 'bg-gray-300'
                }`}></div>
                <div className={`absolute left-1 top-1 bg-white w-6 h-6 rounded-full transition-transform duration-200 ${
                  showComparison ? 'transform translate-x-6' : ''
                }`}></div>
              </div>
              <span className="ml-3 text-sm font-medium text-gray-700 group-hover:text-gray-900">
                Show Comparison
              </span>
            </label>
          </div>
          <FormFieldList
            fields={displayFields}
            hasExecutedPipeline={hasExecutedPipeline}
            rootConfidenceScores={rootConfidenceScores}
          />
        </div>
      ) : null}
    </div>
  );
}

