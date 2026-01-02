// Workflow types

export type WorkflowStatus = "pending" | "in_progress" | "completed" | "failed";
export type StepStatus = "pending" | "in_progress" | "completed" | "failed" | "skipped";

export interface WorkflowStep {
  step_name: string;
  step_order: number;
  status: StepStatus;
  started_at?: string;
  completed_at?: string;
  processing_time?: number;
  error?: string;
  error_details?: Record<string, any>;
  input_data?: Record<string, any>;
  output_data?: Record<string, any>;
}

export interface WorkflowResponse {
  status: WorkflowStatus;
  workflow_id: string;
  current_step?: string | null;
  steps_completed: string[];
  data: Record<string, any>;
  errors: Array<{
    step: string;
    error: string;
    error_type: string;
  }>;
  started_at: string;
  completed_at?: string | null;
  filled_form_json?: any[];  // Optional, may be at root level
  confidence_scores?: Record<string, number>;  // Optional, may be at root level
}

export interface WorkflowStatusResponse {
  workflow_id: string;
  status: WorkflowStatus;
  current_step?: string | null;
  steps: WorkflowStep[];
  progress_percentage: number;
  started_at: string;
  completed_at?: string | null;
}

