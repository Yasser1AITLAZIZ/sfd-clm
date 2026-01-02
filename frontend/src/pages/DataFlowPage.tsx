// Data Transformation Viewer Page - Salesforce Lightning Theme
import { useState, useEffect } from 'react';
import { useWorkflowStatus } from '../hooks/useWorkflowStatus';
import { usePipelineExecution } from '../hooks/usePipelineExecution';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface StepData {
  step: string;
  data: any;
  timestamp?: string;
  status?: 'completed' | 'pending' | 'processing';
}

export function DataFlowPage() {
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());
  const { workflowId } = usePipelineExecution();
  const { data: workflowStatus, isLoading, error } = useWorkflowStatus(workflowId, !!workflowId);

  // Debug logging
  useEffect(() => {
    if (workflowId) {
      console.log('[DataFlowPage] WorkflowId:', workflowId);
    }
    if (workflowStatus) {
      console.log('[DataFlowPage] WorkflowStatus:', {
        status: workflowStatus.status,
        stepsCount: workflowStatus.steps?.length || 0,
        steps: workflowStatus.steps?.map(s => ({
          name: s.step_name,
          status: s.status,
          hasOutput: !!s.output_data,
          hasInput: !!s.input_data,
        })),
      });
    }
    if (error) {
      console.error('[DataFlowPage] Error fetching workflow status:', error);
    }
  }, [workflowId, workflowStatus, error]);

  const toggleStep = (step: string) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(step)) {
      newExpanded.delete(step);
    } else {
      newExpanded.add(step);
    }
    setExpandedSteps(newExpanded);
  };

  // Only show data if workflow has been executed AND has actual step data
  const hasWorkflowData = !!workflowStatus && 
                         workflowStatus.status !== 'pending' && 
                         workflowStatus.steps && 
                         workflowStatus.steps.length > 0 &&
                         workflowStatus.steps.some(step => step.status === 'completed' || step.status === 'in_progress');
  
  // Build steps from workflow data if available, otherwise empty
  const steps: StepData[] = hasWorkflowData && workflowStatus?.steps ? 
    workflowStatus.steps.map((step) => {
      // Combine input and output data for better visibility
      const stepData: any = {};
      
      // Add input data if available
      if (step.input_data) {
        stepData.input = step.input_data;
      }
      
      // Add output data if available
      if (step.output_data) {
        stepData.output = step.output_data;
      }
      
      // If no data at all, show empty object
      const displayData = Object.keys(stepData).length > 0 ? stepData : {};
      
      return {
        step: step.step_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        data: displayData,
        timestamp: step.started_at,
        status: step.status === 'completed' ? 'completed' as const : 
                step.status === 'in_progress' ? 'processing' as const : 
                'pending' as const,
      };
    }) : [];

  const completedSteps = steps.filter(s => s.status === 'completed').length;
  const progressPercentage = steps.length > 0 ? (completedSteps / steps.length) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-8 border border-gray-200/50">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent mb-2">
              Data Transformation Viewer
            </h1>
            <p className="text-gray-600 text-lg">View data transformations at each workflow step</p>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <div className="text-2xl font-bold text-blue-600">{completedSteps}/{steps.length}</div>
              <div className="text-sm text-gray-600">Steps Completed</div>
            </div>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Pipeline Progress</span>
            <span className="text-sm font-semibold text-blue-600">{Math.round(progressPercentage)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
        </div>
      </div>

      {/* Pipeline Flow */}
      {isLoading ? (
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-12 border border-gray-200/50">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Loading Workflow Data...</h3>
            <p className="text-gray-600">Fetching workflow status...</p>
          </div>
        </div>
      ) : error ? (
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-12 border border-red-200/50">
          <div className="text-center">
            <svg className="w-16 h-16 mx-auto text-red-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="text-xl font-semibold text-red-900 mb-2">Error Loading Workflow Data</h3>
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
            <h3 className="text-xl font-semibold text-gray-900 mb-2">No Workflow Data</h3>
            <p className="text-gray-600">Execute a workflow from the Form Visualization page to see data transformations here.</p>
            {workflowId && (
              <p className="text-sm text-gray-500 mt-2">Workflow ID: {workflowId} (No data found)</p>
            )}
          </div>
        </div>
      ) : (
        <div className="relative">
          {/* Connection Lines */}
          <div className="absolute left-16 top-0 bottom-0 w-0.5 bg-gradient-to-b from-blue-300 via-indigo-300 to-purple-300 hidden lg:block" 
               style={{ marginTop: '2rem', marginBottom: '2rem' }} />
          
          {/* Step Cards */}
          <div className="space-y-6">
            {steps.map((stepData, index) => {
            const isExpanded = expandedSteps.has(stepData.step);
            const dataSize = JSON.stringify(stepData.data).length;
            // Count fields from various possible locations - prioritize explicit counts
            const fieldCount = 
              stepData.data.input?.fields_count ||  // Use explicit count from input_data
              stepData.data.output?.fields_count ||  // Use explicit count from output_data
              stepData.data.output?.form_json?.length ||  // Count from form_json in output
              stepData.data.output?.filled_form_json?.length ||  // Count from filled_form_json
              stepData.data.input?.form_json?.length ||  // Count from form_json in input
              stepData.data.output?.fields?.length ||
              stepData.data.input?.fields?.length ||
              stepData.data.filled_form_json?.length ||
              stepData.data.fields?.length || 0;
            const isCompleted = stepData.status === 'completed';
            const hasData = dataSize > 2; // More than just "{}"

            return (
              <div key={index} className="relative">
                {/* Step Card */}
                <div className={`bg-white/70 backdrop-blur-sm rounded-2xl shadow-lg border-2 transition-all duration-300 hover:shadow-xl ${
                  isCompleted 
                    ? 'border-blue-200 hover:border-blue-300' 
                    : 'border-gray-200 hover:border-gray-300'
                }`}>
                  <button
                    onClick={() => toggleStep(stepData.step)}
                    className="w-full px-6 py-5 flex items-center justify-between hover:bg-gradient-to-r hover:from-blue-50/50 hover:to-indigo-50/50 transition-all duration-200 rounded-t-2xl"
                  >
                    <div className="flex items-center space-x-4 flex-1">
                      {/* Step Number Badge */}
                      <div className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center font-bold text-lg shadow-md ${
                        isCompleted
                          ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white'
                          : 'bg-gray-300 text-gray-600'
                      }`}>
                        {index + 1}
                      </div>
                      
                      {/* Step Info */}
                      <div className="flex-1 text-left">
                        <div className="flex items-center space-x-2 mb-1">
                          <h3 className="text-lg font-bold text-gray-900">{stepData.step}</h3>
                          {isCompleted && (
                            <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                          )}
                        </div>
                        <div className="flex items-center space-x-3 text-sm">
                          {fieldCount > 0 && (
                            <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full font-medium">
                              {fieldCount} fields
                            </span>
                          )}
                          {hasData ? (
                            <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full font-medium">
                              {dataSize} bytes
                            </span>
                          ) : (
                            <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded-full font-medium">
                              No data
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    {/* Expand Icon */}
                    <svg
                      className={`w-6 h-6 text-gray-400 transform transition-transform duration-200 flex-shrink-0 ml-4 ${
                        isExpanded ? 'rotate-180' : ''
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  
                  {/* Expanded Content */}
                  {isExpanded && (
                    <div className="px-6 pb-6 border-t border-gray-200 pt-4 animate-in slide-in-from-top-2 duration-200">
                      <div className="bg-gray-900 rounded-xl p-4 overflow-x-auto">
                        <SyntaxHighlighter
                          language="json"
                          style={vscDarkPlus}
                          customStyle={{ 
                            borderRadius: '0.5rem', 
                            fontSize: '0.875rem',
                            margin: 0,
                            padding: '1rem',
                          }}
                        >
                          {JSON.stringify(stepData.data, null, 2)}
                        </SyntaxHighlighter>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          </div>
        </div>
      )}
    </div>
  );
}
