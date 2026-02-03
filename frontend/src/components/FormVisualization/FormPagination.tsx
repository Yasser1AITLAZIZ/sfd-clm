// Form area with button-based pagination across form groups (pages)
import { useState, useMemo } from 'react';
import { FormFieldList } from './FormFieldList';
import { groupFieldsByFormGroup, DEFAULT_FORM_GROUP_ORDER, getOrderedGroupNames } from '../../utils/formGrouping';
import type { MatchedField } from '../../types/form';

export interface FormPaginationProps {
  fields: MatchedField[];
  formGroupOrder?: string[];
  rootConfidenceScores?: Record<string, number>;
  hasExecutedPipeline?: boolean;
  layout?: 'vertical' | 'horizontal';
}

export function FormPagination({
  fields,
  formGroupOrder = [...DEFAULT_FORM_GROUP_ORDER],
  rootConfidenceScores,
  hasExecutedPipeline = false,
  layout = 'horizontal',
}: FormPaginationProps) {
  const [currentPageIndex, setCurrentPageIndex] = useState(0);

  const groups = useMemo(
    () => groupFieldsByFormGroup(fields, formGroupOrder),
    [fields, formGroupOrder]
  );
  const groupNames = getOrderedGroupNames(formGroupOrder);
  const currentGroupName = groupNames[currentPageIndex] ?? groupNames[0];
  const currentFields = groups.get(currentGroupName) ?? [];
  const totalPages = groupNames.length;

  const goPrev = () => setCurrentPageIndex((i) => (i > 0 ? i - 1 : i));
  const goNext = () => setCurrentPageIndex((i) => (i < totalPages - 1 ? i + 1 : i));

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Pagination controls */}
      <div className="flex items-center justify-between gap-4 py-3 px-1 border-b border-gray-200/50 mb-4 flex-shrink-0">
        <button
          type="button"
          onClick={goPrev}
          disabled={currentPageIndex === 0}
          className="px-3 py-1.5 rounded-lg border-2 border-gray-300 text-gray-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors text-sm"
          aria-label="Page précédente"
        >
          Précédent
        </button>
        <div className="flex items-center gap-1 flex-wrap justify-center">
          {groupNames.map((name, i) => (
            <button
              key={name}
              type="button"
              onClick={() => setCurrentPageIndex(i)}
              className={`min-w-[2.25rem] px-2 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                i === currentPageIndex
                  ? 'bg-blue-600 text-white border-2 border-blue-600'
                  : 'border-2 border-gray-300 text-gray-700 hover:bg-gray-100'
              }`}
              aria-label={`Page ${i + 1}: ${name}`}
              aria-current={i === currentPageIndex ? 'page' : undefined}
            >
              {i + 1}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={goNext}
          disabled={currentPageIndex >= totalPages - 1}
          className="px-3 py-1.5 rounded-lg border-2 border-gray-300 text-gray-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors text-sm"
          aria-label="Page suivante"
        >
          Suivant
        </button>
      </div>
      {/* Current page title */}
      <h3 className="text-lg font-semibold text-gray-800 mb-3 flex-shrink-0">
        {currentGroupName}
        <span className="ml-2 text-sm font-normal text-gray-500">
          ({currentFields.length} champ{currentFields.length !== 1 ? 's' : ''})
        </span>
      </h3>
      {/* Fields for current group */}
      <div className="flex-1 min-h-0 overflow-auto">
        <FormFieldList
          fields={currentFields}
          rootConfidenceScores={rootConfidenceScores}
          hasExecutedPipeline={hasExecutedPipeline}
          layout={layout}
        />
      </div>
    </div>
  );
}
