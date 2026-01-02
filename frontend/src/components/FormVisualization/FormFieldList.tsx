// List of form fields component
import { FormField } from './FormField';
import type { MatchedField } from '../../types/form';

interface FormFieldListProps {
  fields: MatchedField[];
  rootConfidenceScores?: Record<string, number>;
  hasExecutedPipeline?: boolean;
}

export function FormFieldList({ fields, rootConfidenceScores, hasExecutedPipeline = false }: FormFieldListProps) {
  return (
    <div className="space-y-6">
      {fields.map((field) => (
        <FormField
          key={field.label}
          field={field}
          rootConfidenceScores={rootConfidenceScores}
          hasExecutedPipeline={hasExecutedPipeline}
        />
      ))}
    </div>
  );
}

