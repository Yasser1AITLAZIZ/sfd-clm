// Real-time Workflow Orchestration Page - Salesforce Lightning Theme
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { usePipelineExecution } from '../hooks/usePipelineExecution';
import { useWorkflowStatus } from '../hooks/useWorkflowStatus';
import { DocumentUpload } from '../components/FormVisualization/DocumentUpload';
import { WorkflowStatus as WorkflowStatusComponent } from '../components/WorkflowOrchestration/WorkflowStatus';
import { WorkflowTimeline } from '../components/WorkflowOrchestration/WorkflowTimeline';
import { ErrorHighlight } from '../components/WorkflowOrchestration/ErrorHighlight';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorDisplay } from '../components/common/ErrorDisplay';

const DEFAULT_RECORD_ID = '001XX000001';
const RECORD_ID_STORAGE_KEY = 'sfd-clm-record-id';

export function WorkflowPage() {
  const [recordId, setRecordId] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(RECORD_ID_STORAGE_KEY) || DEFAULT_RECORD_ID;
    }
    return DEFAULT_RECORD_ID;
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedDocument, setUploadedDocument] = useState<{ document_id: string; url: string } | null>(null);
  
  const queryClient = useQueryClient();
  const { workflowId, clearWorkflow } = usePipelineExecution();
  const [localWorkflowId, setLocalWorkflowId] = useState<string | null>(null);

  // Sync recordId to localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(RECORD_ID_STORAGE_KEY, recordId);
    }
  }, [recordId]);

  useEffect(() => {
    const storedId = typeof window !== 'undefined' ? localStorage.getItem('sfd-clm-workflow-id') : null;
    setLocalWorkflowId(storedId);
  }, [workflowId]);

  const activeWorkflowId = workflowId || localWorkflowId;

  const { data: workflowStatus, isLoading: isLoadingStatus, error: statusError } = useWorkflowStatus(
    activeWorkflowId,
    !!activeWorkflowId
  );

  const handleRestartPipeline = () => {
    clearWorkflow();
    queryClient.invalidateQueries({ queryKey: ['formData', recordId] });
    queryClient.invalidateQueries({ queryKey: ['workflowStatus'] });
    console.log('[WorkflowPage] Pipeline restarted');
  };

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-8 border border-gray-200/50">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent mb-2">
              Workflow Orchestration
            </h1>
            <p className="text-gray-600 text-lg">Monitor pipeline execution in real-time</p>
          </div>
          {workflowStatus && (
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <div className="text-2xl font-bold text-blue-600">{workflowStatus.progress_percentage}%</div>
                <div className="text-sm text-gray-600">Progress</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Record ID Input */}
      <div className="bg-gradient-to-br from-white via-blue-50/30 to-indigo-50/30 backdrop-blur-sm rounded-2xl shadow-xl p-6 border-2 border-blue-200/50">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center mr-3 shadow-lg">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </div>
          Workflow Configuration
        </h2>
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Record ID
          </label>
          <input
            type="text"
            value={recordId}
            onChange={(e) => setRecordId(e.target.value)}
            className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 text-gray-900 placeholder-gray-400 bg-white shadow-sm"
            placeholder="Enter record ID"
          />
          <p className="mt-2 text-xs text-gray-500">
            This record ID is shared with Form Visualization page
          </p>
        </div>
      </div>

      {/* Document Upload */}
      <div className="bg-gradient-to-br from-white via-green-50/30 to-emerald-50/30 backdrop-blur-sm rounded-2xl shadow-xl p-6 border-2 border-green-200/50">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
          <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-emerald-600 rounded-lg flex items-center justify-center mr-3 shadow-lg">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          Document Upload
        </h2>
        <DocumentUpload
          onFileSelect={setSelectedFile}
          onUploadComplete={(documentId, url) => {
            setUploadedDocument({ document_id: documentId, url });
            console.log('[WorkflowPage] Document uploaded successfully:', { documentId, url });
          }}
          recordId={recordId}
          disabled={false}
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
          <div className="mt-4 p-4 bg-gradient-to-r from-green-50 to-blue-50 border-2 border-green-300 rounded-xl shadow-md">
            <div className="flex items-center justify-between">
              <div className="flex items-center text-sm text-green-800">
                <svg className="w-6 h-6 mr-3 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <div>
                  <span className="font-bold text-base">Document uploaded successfully!</span>
                  <p className="text-xs text-gray-600 mt-1">Document ID: {uploadedDocument.document_id}</p>
                </div>
              </div>
              <Link
                to="/documents"
                className="ml-4 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200 flex items-center space-x-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>View in Document Processing</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* Restart Pipeline Button - If workflow is active */}
      {activeWorkflowId && (
        <div className="bg-gradient-to-r from-orange-50 via-red-50 to-orange-50 backdrop-blur-sm rounded-2xl shadow-xl p-6 border-2 border-orange-400">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-red-600 rounded-xl flex items-center justify-center shadow-lg">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </div>
              <div>
                <h3 className="text-xl font-bold text-gray-900">⚠️ Active Workflow Detected</h3>
                <p className="text-sm text-gray-700 mt-1">Clear workflow data to start fresh</p>
                <p className="text-xs text-gray-600 mt-2 font-mono bg-white/70 px-3 py-1 rounded border border-orange-200 inline-block">
                  ID: {activeWorkflowId}
                </p>
              </div>
            </div>
            <button
              onClick={handleRestartPipeline}
              className="px-8 py-3 bg-gradient-to-r from-red-600 to-orange-600 text-white font-bold rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 flex items-center justify-center space-x-2"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>Restart Pipeline</span>
            </button>
          </div>
        </div>
      )}

      {/* Workflow Status */}
      {isLoadingStatus ? (
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-12 border border-gray-200/50">
          <div className="flex flex-col items-center justify-center">
            <LoadingSpinner size="lg" />
            <p className="mt-4 text-gray-600 font-medium">Loading workflow status...</p>
          </div>
        </div>
      ) : statusError ? (
        <div className="bg-red-50 border-2 border-red-200 rounded-2xl p-6">
          <ErrorDisplay error={statusError} />
        </div>
      ) : workflowStatus ? (
        <div className="space-y-6">
          <WorkflowStatusComponent status={workflowStatus} />
          
          {workflowStatus.steps.some(s => s.status === 'failed') && (
            <ErrorHighlight
              errors={workflowStatus.steps
                .filter(s => s.status === 'failed' && s.error)
                .map(s => ({
                  step: s.step_name,
                  error: s.error || 'Unknown error',
                  error_type: 'WorkflowError',
                }))}
            />
          )}

          <div className="bg-gradient-to-br from-white via-indigo-50/30 to-purple-50/30 backdrop-blur-sm rounded-2xl shadow-xl p-6 border-2 border-indigo-200/50">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
              <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center mr-3 shadow-lg">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              Workflow Timeline
            </h2>
            <WorkflowTimeline
              steps={workflowStatus.steps}
              currentStep={workflowStatus.current_step || undefined}
            />
          </div>
        </div>
      ) : activeWorkflowId ? (
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-12 border border-gray-200/50">
          <div className="text-center">
            <LoadingSpinner size="lg" />
            <p className="mt-4 text-gray-600 font-medium">Waiting for workflow to start...</p>
          </div>
        </div>
      ) : (
        <div className="bg-gradient-to-br from-gray-50 to-blue-50/30 backdrop-blur-sm rounded-2xl shadow-xl p-12 border-2 border-gray-200/50">
          <div className="text-center">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-400 to-indigo-500 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
              <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">No Active Workflow</h3>
            <p className="text-gray-600 font-medium">Go to Form Visualization page to execute a workflow</p>
            <Link
              to="/"
              className="mt-4 inline-block px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200"
            >
              Go to Form Visualization
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

