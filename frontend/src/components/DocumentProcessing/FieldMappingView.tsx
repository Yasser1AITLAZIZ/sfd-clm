// Field-to-OCR mapping component
import type { FieldMapping } from '../../types/document';
import { formatConfidence } from '../../utils/formatters';

interface FieldMappingViewProps {
  mappings: FieldMapping[];
  selectedField?: string | null;
  onFieldSelect?: (fieldLabel: string) => void;
}

export function FieldMappingView({ mappings, selectedField, onFieldSelect }: FieldMappingViewProps) {
  return (
    <div className="space-y-4">
      {mappings.map((mapping, index) => {
        const isSelected = selectedField === mapping.field_label;
        const confidenceColor =
          mapping.confidence >= 0.8
            ? 'bg-green-100 text-green-700 border-green-400'
            : mapping.confidence >= 0.5
            ? 'bg-yellow-100 text-yellow-700 border-yellow-400'
            : 'bg-red-100 text-red-700 border-red-400';

        return (
          <div
            key={index}
            className={`border-2 rounded-xl p-4 cursor-pointer transition-all duration-200 ${
              isSelected ? 'border-blue-500 bg-blue-50 shadow-md' : 'border-gray-200 hover:border-blue-300 hover:shadow-md'
            }`}
            onClick={() => onFieldSelect?.(mapping.field_label)}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-gray-900">{mapping.field_label}</h3>
              <div className="flex items-center space-x-2">
                {mapping.source_page && (
                  <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium">
                    Page {mapping.source_page}
                  </span>
                )}
                <span className={`px-3 py-1 rounded-lg text-xs font-bold border-2 ${confidenceColor}`}>
                  {formatConfidence(mapping.confidence)}
                </span>
              </div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 border border-gray-200">
              {mapping.ocr_text}
            </div>
            {isSelected && (
              <div className="mt-3 pt-3 border-t border-blue-200">
                <div className="flex items-center text-xs text-blue-700">
                  <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  <span>Selected - Highlighted in OCR text</span>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

