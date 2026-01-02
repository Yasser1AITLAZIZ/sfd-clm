// Timeline visualization component
import { WorkflowStep } from './WorkflowStep';
import type { WorkflowStep as WorkflowStepType } from '../../types/workflow';

interface WorkflowTimelineProps {
  steps: WorkflowStepType[];
  currentStep?: string | null;
}

export function WorkflowTimeline({ steps, currentStep }: WorkflowTimelineProps) {
  // Sort steps by order
  const sortedSteps = [...steps].sort((a, b) => a.step_order - b.step_order);

  return (
    <div className="space-y-4">
      {sortedSteps.map((step, index) => (
        <div key={step.step_name} className="relative">
          {index < sortedSteps.length - 1 && (
            <div className="absolute left-8 top-20 w-0.5 h-10 bg-gradient-to-b from-blue-300 to-indigo-300" />
          )}
          <WorkflowStep
            step={step}
            isActive={step.step_name === currentStep}
          />
        </div>
      ))}
    </div>
  );
}

