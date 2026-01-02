// Individual workflow step component
import type { WorkflowStep as WorkflowStepType } from '../../types/workflow';
import { formatDuration, formatDate } from '../../utils/formatters';

interface WorkflowStepProps {
  step: WorkflowStepType;
  isActive: boolean;
}

const stepNames: Record<string, string> = {
  validation_routing: 'Validation & Routing',
  fetch_salesforce_data: 'Fetch Salesforce Data',
  preprocessing: 'Preprocessing',
  prompt_building: 'Prompt Building',
  prompt_optimization: 'Prompt Optimization',
  mcp_formatting: 'MCP Formatting',
  mcp_sending: 'MCP Sending',
  response_handling: 'Response Handling',
};

export function WorkflowStep({ step, isActive }: WorkflowStepProps) {
  const displayName = stepNames[step.step_name] || step.step_name;
  
  const statusColors = {
    pending: 'bg-gray-100 border-gray-300 text-gray-600',
    in_progress: 'bg-blue-100 border-blue-400 text-blue-700',
    completed: 'bg-green-100 border-green-400 text-green-700',
    failed: 'bg-red-100 border-red-400 text-red-700',
    skipped: 'bg-yellow-100 border-yellow-400 text-yellow-700',
  };

  const statusIconsSVG = {
    pending: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
      </svg>
    ),
    in_progress: (
      <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
      </svg>
    ),
    completed: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
      </svg>
    ),
    failed: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
      </svg>
    ),
    skipped: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM7 9a1 1 0 000 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
      </svg>
    ),
  };

  return (
    <div
      className={`p-5 border-2 rounded-xl shadow-md transition-all duration-200 ${
        statusColors[step.status]
      } ${isActive ? 'ring-4 ring-blue-400 shadow-lg scale-[1.02]' : 'hover:shadow-lg'}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg shadow-md ${
            step.status === 'completed'
              ? 'bg-gradient-to-br from-green-500 to-emerald-600 text-white'
              : step.status === 'in_progress'
              ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white'
              : step.status === 'failed'
              ? 'bg-gradient-to-br from-red-500 to-red-600 text-white'
              : 'bg-gray-300 text-gray-600'
          }`}>
            {step.step_order}
          </div>
          <div>
            <h3 className="font-bold text-gray-900">{displayName}</h3>
            <div className="flex items-center space-x-2 mt-1">
              {statusIconsSVG[step.status]}
              <p className="text-sm font-medium opacity-75 capitalize">
                {step.status.replace('_', ' ')}
              </p>
            </div>
          </div>
        </div>
        <div className="text-right text-sm">
          {step.processing_time !== undefined && (
            <div className="font-bold text-gray-900">{formatDuration(step.processing_time)}</div>
          )}
          {step.started_at && (
            <div className="text-xs opacity-75 mt-1">{formatDate(step.started_at)}</div>
          )}
        </div>
      </div>
      {step.error && (
        <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          <strong>Error:</strong> {step.error}
        </div>
      )}
      {step.error_details && Object.keys(step.error_details).length > 0 && (
        <details className="mt-2">
          <summary className="text-sm cursor-pointer text-red-600">Error Details</summary>
          <pre className="mt-2 p-2 bg-red-50 rounded text-xs overflow-auto">
            {JSON.stringify(step.error_details, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}

