// Before/After field comparison component
import type { MatchedField } from '../../types/form';

interface FieldComparisonProps {
  field: MatchedField;
  showComparison?: boolean;
}

export function FieldComparison({ field, showComparison = true }: FieldComparisonProps) {
  if (!showComparison) return null;

  const hasChanged = field.defaultValue !== field.dataValue_target_AI;

  return (
    <div className="mt-2 p-2 bg-gray-50 rounded border border-gray-200">
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <div className="font-medium text-gray-700 mb-1">Original (defaultValue)</div>
          <div className="text-gray-600">
            {field.defaultValue || <span className="text-gray-400">null</span>}
          </div>
        </div>
        <div>
          <div className="font-medium text-gray-700 mb-1">Extracted (dataValue_target_AI)</div>
          <div className={hasChanged ? 'text-green-600 font-medium' : 'text-gray-600'}>
            {field.dataValue_target_AI || <span className="text-gray-400">null</span>}
          </div>
        </div>
      </div>
      {hasChanged && (
        <div className="mt-2 text-xs text-green-600 flex items-center">
          <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          Value changed
        </div>
      )}
    </div>
  );
}

