// Workflow Progress Bar Component - Real-time step-by-step progress
import { useWorkflowStatus } from '../../hooks/useWorkflowStatus';
import type { WorkflowStep } from '../../types/workflow';

interface WorkflowProgressBarProps {
  workflowId: string | null;
}

const stepNames: Record<string, string> = {
  'routing': 'Routing',
  'preprocessing': 'Preprocessing',
  'prompt_building': 'Prompt Building',
  'prompt_optimization': 'Prompt Optimization',
  'mcp_sending': 'MCP Sending',
  'response_handling': 'Response Handling',
  'validation': 'Validation',
};

export function WorkflowProgressBar({ workflowId }: WorkflowProgressBarProps) {
  const { data: workflowStatus, isLoading } = useWorkflowStatus(workflowId, !!workflowId);

  // CRITICAL: Show loading state instead of returning null
  if (!workflowId) {
    return null;
  }

  // Show loading state while fetching initial status
  if (isLoading && !workflowStatus) {
    return (
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-bold text-gray-900">Workflow Progress</h3>
            <p className="text-sm text-gray-600 mt-1">Initializing workflow progress...</p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              0%
            </div>
            <div className="text-xs text-gray-500 mt-1">Loading...</div>
          </div>
        </div>
        <div className="flex items-center justify-center py-8">
          <div className="text-center">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto"></div>
            </div>
            <p className="mt-4 text-gray-600 font-medium">Fetching workflow status...</p>
          </div>
        </div>
      </div>
    );
  }

  // If still no status after loading, show waiting state
  if (!workflowStatus) {
    return (
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-bold text-gray-900">Workflow Progress</h3>
            <p className="text-sm text-gray-600 mt-1">Waiting for workflow to start...</p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold bg-gradient-to-r from-gray-600 to-gray-800 bg-clip-text text-transparent">
              0%
            </div>
            <div className="text-xs text-gray-500 mt-1">Pending</div>
          </div>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden shadow-inner mb-4">
          <div className="h-full rounded-full bg-gray-300" style={{ width: '0%' }} />
        </div>
        <div className="text-center py-4 text-gray-500">
          <p>Workflow ID: <span className="font-mono text-sm">{workflowId}</span></p>
          <p className="mt-2 text-sm">The workflow will appear here once it starts executing.</p>
        </div>
      </div>
    );
  }

  const steps = workflowStatus.steps || [];
  const sortedSteps = [...steps].sort((a, b) => a.step_order - b.step_order);
  const currentStepIndex = sortedSteps.findIndex(s => s.status === 'in_progress');
  const completedSteps = sortedSteps.filter(s => s.status === 'completed').length;
  const progressPercentage = steps.length > 0 ? (completedSteps / steps.length) * 100 : 0;

  const getStepStatus = (step: WorkflowStep, index: number) => {
    if (step.status === 'completed') return 'completed';
    if (step.status === 'in_progress') return 'active';
    if (step.status === 'failed') return 'failed';
    if (currentStepIndex !== -1 && index < currentStepIndex) return 'completed';
    return 'pending';
  };

  const getStepColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-gradient-to-r from-green-500 to-emerald-500';
      case 'active':
        return 'bg-gradient-to-r from-blue-500 to-indigo-500 animate-pulse';
      case 'failed':
        return 'bg-gradient-to-r from-red-500 to-red-600';
      default:
        return 'bg-gray-300';
    }
  };

  const getStepIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        );
      case 'active':
        return (
          <svg className="w-5 h-5 text-white animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        );
      case 'failed':
        return (
          <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5 text-gray-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V7z" clipRule="evenodd" />
          </svg>
        );
    }
  };

  return (
    <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-xl font-bold text-gray-900">Workflow Progress</h3>
          <p className="text-sm text-gray-600 mt-1">Real-time step-by-step execution</p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            {Math.round(progressPercentage)}%
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {completedSteps} / {steps.length} steps
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-8">
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden shadow-inner">
          <div
            className={`h-full rounded-full transition-all duration-500 ease-out ${getStepColor(
              workflowStatus.status === 'completed' ? 'completed' : 
              workflowStatus.status === 'in_progress' ? 'active' : 
              workflowStatus.status === 'failed' ? 'failed' : 'pending'
            )}`}
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Steps */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {sortedSteps.map((step, index) => {
          const stepStatus = getStepStatus(step, index);
          const displayName = stepNames[step.step_name] || step.step_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          
          return (
            <div
              key={step.step_name}
              className={`relative p-4 rounded-xl border-2 transition-all duration-300 ${
                stepStatus === 'completed'
                  ? 'bg-gradient-to-br from-green-50 to-emerald-50 border-green-300 shadow-md'
                  : stepStatus === 'active'
                  ? 'bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-400 shadow-lg ring-2 ring-blue-300 scale-105'
                  : stepStatus === 'failed'
                  ? 'bg-gradient-to-br from-red-50 to-red-100 border-red-300 shadow-md'
                  : 'bg-gray-50 border-gray-200'
              }`}
            >
              <div className="flex items-center space-x-3">
                <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${getStepColor(stepStatus)} shadow-lg`}>
                  {getStepIcon(stepStatus)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-gray-900 truncate">{displayName}</div>
                  <div className={`text-xs mt-0.5 ${
                    stepStatus === 'completed' ? 'text-green-700' :
                    stepStatus === 'active' ? 'text-blue-700 font-semibold' :
                    stepStatus === 'failed' ? 'text-red-700' :
                    'text-gray-500'
                  }`}>
                    {stepStatus === 'active' ? 'Processing...' :
                     stepStatus === 'completed' ? 'Completed' :
                     stepStatus === 'failed' ? 'Failed' :
                     'Pending'}
                  </div>
                </div>
              </div>
              {step.processing_time !== undefined && stepStatus === 'completed' && (
                <div className="mt-2 text-xs text-gray-600 font-mono">
                  {step.processing_time.toFixed(2)}s
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Status Message */}
      {workflowStatus.status === 'in_progress' && currentStepIndex !== -1 && (
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-xl">
          <div className="flex items-center space-x-2">
            <svg className="w-5 h-5 text-blue-600 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V7z" clipRule="evenodd" />
            </svg>
            <span className="text-sm font-semibold text-blue-800">
              Currently executing: {stepNames[sortedSteps[currentStepIndex]?.step_name] || sortedSteps[currentStepIndex]?.step_name}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

