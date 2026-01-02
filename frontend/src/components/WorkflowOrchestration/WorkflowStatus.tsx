// Overall workflow status component
import type { WorkflowStatusResponse } from '../../types/workflow';
import { formatDate, formatDuration } from '../../utils/formatters';

interface WorkflowStatusProps {
  status: WorkflowStatusResponse;
}

export function WorkflowStatus({ status }: WorkflowStatusProps) {
  const statusColors = {
    pending: 'bg-gray-100 text-gray-700',
    in_progress: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
  };

  const totalDuration = status.completed_at && status.started_at
    ? (new Date(status.completed_at).getTime() - new Date(status.started_at).getTime()) / 1000
    : undefined;

  return (
    <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Workflow Status</h2>
          <p className="text-sm text-gray-500 font-mono">ID: {status.workflow_id}</p>
        </div>
        <div className={`px-4 py-2 rounded-xl font-bold shadow-md ${statusColors[status.status]}`}>
          {status.status.toUpperCase()}
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <div className="text-sm text-gray-500">Progress</div>
          <div className="text-2xl font-bold">{status.progress_percentage}%</div>
          <div className="w-full bg-gray-200 rounded-full h-3 mt-2 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${status.progress_percentage}%` }}
            />
          </div>
        </div>
        <div>
          <div className="text-sm text-gray-500">Steps Completed</div>
          <div className="text-2xl font-bold">
            {status.steps.length} / {status.steps.length}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <div className="text-gray-500">Started</div>
          <div className="font-medium">{formatDate(status.started_at)}</div>
        </div>
        {status.completed_at && (
          <div>
            <div className="text-gray-500">Completed</div>
            <div className="font-medium">{formatDate(status.completed_at)}</div>
          </div>
        )}
        {totalDuration && (
          <div>
            <div className="text-gray-500">Duration</div>
            <div className="font-medium">{formatDuration(totalDuration)}</div>
          </div>
        )}
      </div>
    </div>
  );
}

