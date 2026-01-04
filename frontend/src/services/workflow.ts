// Workflow API service
import { apiClient, handleApiError, extractApiData } from './api';
import type { WorkflowResponse, WorkflowStatusResponse, WorkflowStep } from '../types/workflow';
import type { ApiResponse } from '../types/api';

/**
 * Execute pipeline workflow
 * POST /api/mcp/receive-request
 */
export async function executeWorkflow(
  recordId: string,
  sessionId: string | null,
  userMessage: string
): Promise<WorkflowResponse> {
  try {
    const response = await apiClient.post<ApiResponse<WorkflowResponse>>(
      '/api/mcp/receive-request',
      {
        record_id: recordId,
        session_id: sessionId,
        user_message: userMessage,
      }
    );
    return extractApiData(response.data);
  } catch (error) {
    const apiError = handleApiError(error);
    throw new Error(apiError.message);
  }
}

/**
 * Get workflow status
 * GET /api/workflow/status/{workflow_id}
 */
export async function getWorkflowStatus(workflowId: string): Promise<WorkflowStatusResponse> {
  try {
    const response = await apiClient.get<ApiResponse<WorkflowStatusResponse>>(
      `/api/workflow/status/${workflowId}`
    );
    return extractApiData(response.data);
  } catch (error) {
    const apiError = handleApiError(error);
    throw new Error(apiError.message);
  }
}

/**
 * Get workflow steps
 * GET /api/workflow/{workflow_id}/steps
 */
export async function getWorkflowSteps(workflowId: string): Promise<WorkflowStep[]> {
  try {
    const response = await apiClient.get<ApiResponse<WorkflowStep[]>>(
      `/api/workflow/${workflowId}/steps`
    );
    return extractApiData(response.data);
  } catch (error) {
    const apiError = handleApiError(error);
    throw new Error(apiError.message);
  }
}

/**
 * Get list of recent workflows
 * GET /api/workflow/recent?limit={limit}
 */
export async function getRecentWorkflows(limit: number = 10): Promise<Array<{
  workflow_id: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  record_id: string;
}>> {
  try {
    const response = await apiClient.get<ApiResponse<Array<{
      workflow_id: string;
      status: string;
      started_at: string;
      completed_at: string | null;
      record_id: string;
    }>>>(`/api/workflow/recent?limit=${limit}`);
    
    return extractApiData(response.data);
  } catch (error) {
    const apiError = handleApiError(error);
    throw new Error(apiError.message);
  }
}

