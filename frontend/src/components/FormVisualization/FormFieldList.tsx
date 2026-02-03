// List of form fields component with horizontal layout support
import { FormField } from './FormField';
import type { MatchedField } from '../../types/form';

interface FormFieldListProps {
  fields: MatchedField[];
  rootConfidenceScores?: Record<string, number>;
  hasExecutedPipeline?: boolean;
  layout?: 'vertical' | 'horizontal';
}

export function FormFieldList({ 
  fields, 
  rootConfidenceScores, 
  hasExecutedPipeline = false,
  layout = 'vertical'
}: FormFieldListProps) {
  if (layout === 'horizontal') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {fields.map((field) => (
          <FormField
            key={field.apiName ?? `${field.formGroup ?? 'default'}-${field.label}`}
            field={field}
            rootConfidenceScores={rootConfidenceScores}
            hasExecutedPipeline={hasExecutedPipeline}
            compact={true}
          />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {fields.map((field) => (
        <FormField
          key={field.apiName ?? `${field.formGroup ?? 'default'}-${field.label}`}
          field={field}
          rootConfidenceScores={rootConfidenceScores}
          hasExecutedPipeline={hasExecutedPipeline}
        />
      ))}
    </div>
  );
}

