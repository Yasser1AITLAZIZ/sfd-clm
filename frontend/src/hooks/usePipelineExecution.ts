// Pipeline execution hook
import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { executeWorkflow } from '../services/workflow';
import type { WorkflowResponse } from '../types/workflow';

const WORKFLOW_ID_STORAGE_KEY = 'sfd-clm-workflow-id';

export function usePipelineExecution() {
  const queryClient = useQueryClient();
  // Load workflowId from localStorage on mount
  const [workflowId, setWorkflowIdState] = useState<string | null>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(WORKFLOW_ID_STORAGE_KEY);
    }
    return null;
  });

  // Sync workflowId to localStorage whenever it changes
  useEffect(() => {
    if (workflowId) {
      localStorage.setItem(WORKFLOW_ID_STORAGE_KEY, workflowId);
    } else {
      localStorage.removeItem(WORKFLOW_ID_STORAGE_KEY);
    }
  }, [workflowId]);

  const setWorkflowId = (id: string | null) => {
    setWorkflowIdState(id);
  };

  const mutation = useMutation<WorkflowResponse, Error, {
    recordId: string;
    sessionId: string | null;
    userMessage: string;
  }>({
    mutationFn: ({ recordId, sessionId, userMessage }) =>
      executeWorkflow(recordId, sessionId, userMessage),
    onSuccess: (data) => {
      console.log('[usePipelineExecution] Workflow executed successfully, workflowId:', data.workflow_id);
      setWorkflowId(data.workflow_id);
      // Invalidate and refetch workflow status for all pages
      queryClient.invalidateQueries({ queryKey: ['workflowStatus'] });
      // Also refetch immediately
      queryClient.refetchQueries({ queryKey: ['workflowStatus', data.workflow_id] });
    },
  });

  const clearWorkflow = () => {
    console.log('[usePipelineExecution] Clearing workflow and resetting state');
    setWorkflowId(null);
    // Clear all workflow-related queries
    queryClient.removeQueries({ queryKey: ['workflowStatus'] });
    // Also invalidate form data queries to ensure fresh data on restart
    queryClient.invalidateQueries({ queryKey: ['formData'] });
    // Clear localStorage
    if (typeof window !== 'undefined') {
      localStorage.removeItem(WORKFLOW_ID_STORAGE_KEY);
    }
  };

  return {
    ...mutation,
    workflowId,
    isLoading: mutation.isPending, // Alias for compatibility
    execute: mutation.mutate,
    executeAsync: mutation.mutateAsync,
    clearWorkflow,
  };
}

