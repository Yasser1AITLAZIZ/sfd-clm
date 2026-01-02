// Workflow status polling hook
import { useQuery } from '@tanstack/react-query';
import { getWorkflowStatus } from '../services/workflow';
import type { WorkflowStatusResponse } from '../types/workflow';

export function useWorkflowStatus(workflowId: string | null, enabled: boolean = true) {
  return useQuery<WorkflowStatusResponse, Error>({
    queryKey: ['workflowStatus', workflowId],
    queryFn: async () => {
      const result = await getWorkflowStatus(workflowId!);
      console.log('[useWorkflowStatus] Fetched workflow status:', {
        workflowId,
        status: result.status,
        stepsCount: result.steps?.length || 0,
        steps: result.steps?.map(s => s.step_name),
      });
      return result;
    },
    enabled: enabled && !!workflowId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 1000; // Poll every 1 second if no data
      
      // Poll every 1 second during active workflow
      if (data.status === 'pending' || data.status === 'in_progress') {
        return 1000;
      }
      
      // Poll every 5 seconds for completed workflows
      return 5000;
    },
    retry: 2,
    retryDelay: 1000,
  });
}

