// Real-time Workflow Orchestration Page - Salesforce Lightning Theme
import { useState } from 'react';
import { usePipelineExecution } from '../hooks/usePipelineExecution';
import { useWorkflowStatus } from '../hooks/useWorkflowStatus';
import { WorkflowStatus as WorkflowStatusComponent } from '../components/WorkflowOrchestration/WorkflowStatus';
import { WorkflowTimeline } from '../components/WorkflowOrchestration/WorkflowTimeline';
import { ErrorHighlight } from '../components/WorkflowOrchestration/ErrorHighlight';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorDisplay } from '../components/common/ErrorDisplay';

const DEFAULT_RECORD_ID = '001XX000001';

export function WorkflowPage() {
  const [recordId, setRecordId] = useState(DEFAULT_RECORD_ID);
  const [userMessage, setUserMessage] = useState('Remplis tous les champs manquants');
  const { executeAsync, workflowId, isLoading: isExecuting, error: executionError } = usePipelineExecution();
  const { data: workflowStatus, isLoading: isLoadingStatus, error: statusError } = useWorkflowStatus(
    workflowId,
    !!workflowId
  );

  const handleExecute = async () => {
    try {
      await executeAsync({
        recordId,
        sessionId: null,
        userMessage,
      });
    } catch (error) {
      console.error('Execution error:', error);
    }
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

      {/* Input Section */}
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
          <svg className="w-6 h-6 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
          Workflow Configuration
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
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
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              User Message
            </label>
            <textarea
              value={userMessage}
              onChange={(e) => setUserMessage(e.target.value)}
              className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 text-gray-900 placeholder-gray-400 resize-y"
              rows={3}
              placeholder="Enter user message"
            />
          </div>
          <button
            onClick={handleExecute}
            disabled={isExecuting || !recordId || !userMessage}
            className="w-full px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center justify-center space-x-2"
          >
            {isExecuting ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Executing Workflow...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span>Execute Workflow</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Execution Error */}
      {executionError && (
        <div className="bg-red-50 border-2 border-red-200 rounded-2xl p-6">
          <ErrorDisplay error={executionError} />
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

          <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
              <svg className="w-6 h-6 mr-2 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Workflow Timeline
            </h2>
            <WorkflowTimeline
              steps={workflowStatus.steps}
              currentStep={workflowStatus.current_step || undefined}
            />
          </div>
        </div>
      ) : workflowId ? (
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-12 border border-gray-200/50">
          <div className="text-center">
            <LoadingSpinner size="lg" />
            <p className="mt-4 text-gray-600 font-medium">Waiting for workflow to start...</p>
          </div>
        </div>
      ) : (
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-12 border border-gray-200/50">
          <div className="text-center">
            <svg className="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p className="text-gray-600 font-medium">Enter record ID and user message, then click "Execute Workflow" to start</p>
          </div>
        </div>
      )}
    </div>
  );
}

