// Individual form field component
import { useState, useEffect } from 'react';
import type { MatchedField } from '../../types/form';
import { isNotAvailable, getScoreColorClass, getConfidenceScore } from '../../utils/fieldMatcher';
import { formatConfidence, formatQualityScore } from '../../utils/formatters';

interface FormFieldProps {
  field: MatchedField;
  rootConfidenceScores?: Record<string, number>;
  hasExecutedPipeline?: boolean;
  compact?: boolean;
}

export function FormField({ field, rootConfidenceScores, hasExecutedPipeline = false, compact = false }: FormFieldProps) {
  const confidence = getConfidenceScore(field, rootConfidenceScores);
  const isNotAvail = isNotAvailable(field.dataValue_target_AI);
  
  // Local state for form field value (allows user interaction before pipeline execution)
  const initialValue = field.dataValue_target_AI || field.defaultValue || '';
  const [localValue, setLocalValue] = useState(initialValue);
  
  // Update local value when field data changes (including when reset to null/empty on restart)
  useEffect(() => {
    const newValue = field.dataValue_target_AI || field.defaultValue || '';
    // Always update to ensure reset works correctly when field.dataValue_target_AI becomes null
    setLocalValue(newValue);
  }, [field.dataValue_target_AI, field.defaultValue]);
  
  // Determine border color based on field state
  let borderColor = 'border-gray-300';
  if (field.isMatched) {
    if (isNotAvail) {
      borderColor = 'border-yellow-400 bg-yellow-50';
    } else {
      borderColor = 'border-green-400 bg-green-50';
    }
  }

  const renderInput = () => {
    // Use local value for user interaction, fallback to field data
    const value = localValue;
    // Only disable if pipeline was executed and field was matched (meaning it has AI-extracted value)
    // Allow editing before execution or if field wasn't matched
    const disabled = hasExecutedPipeline && field.isMatched && !isNotAvail;

    switch (field.type) {
      case 'text':
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => setLocalValue(e.target.value)}
            disabled={disabled}
            className={`w-full px-4 py-3 border-2 rounded-xl transition-all duration-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${borderColor} ${
              disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'
            } text-gray-900 placeholder-gray-400`}
            placeholder={isNotAvail ? 'Non disponible' : ''}
          />
        );
      case 'number':
        return (
          <input
            type="number"
            value={value}
            onChange={(e) => setLocalValue(e.target.value)}
            disabled={disabled}
            className={`w-full px-4 py-3 border-2 rounded-xl transition-all duration-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${borderColor} ${
              disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'
            } text-gray-900 placeholder-gray-400`}
            placeholder={isNotAvail ? 'Non disponible' : ''}
          />
        );
      case 'textarea':
        return (
          <textarea
            value={value}
            onChange={(e) => setLocalValue(e.target.value)}
            disabled={disabled}
            rows={4}
            className={`w-full px-4 py-3 border-2 rounded-xl transition-all duration-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${borderColor} ${
              disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'
            } text-gray-900 placeholder-gray-400 resize-y`}
            placeholder={isNotAvail ? 'Non disponible' : ''}
          />
        );
      case 'picklist':
        return (
          <select
            value={value}
            onChange={(e) => setLocalValue(e.target.value)}
            disabled={disabled}
            className={`w-full px-4 py-3 border-2 rounded-xl transition-all duration-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${borderColor} ${
              disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'
            } text-gray-900`}
          >
            {field.possibleValues.length > 0 ? (
              <>
                <option value="">Select an option...</option>
                {field.possibleValues.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </>
            ) : (
              <option value="">No options available</option>
            )}
          </select>
        );
      case 'radio':
        return (
          <div className="space-y-3">
            {field.possibleValues.length > 0 ? (
              field.possibleValues.map((option) => (
                <label key={option} className="flex items-center p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
                  <input
                    type="radio"
                    name={field.label}
                    value={option}
                    checked={value === option}
                    onChange={(e) => setLocalValue(e.target.value)}
                    disabled={disabled}
                    className="w-4 h-4 text-blue-600 focus:ring-blue-500 focus:ring-2 border-gray-300 cursor-pointer"
                  />
                  <span className={`ml-3 ${disabled ? 'text-gray-500' : 'text-gray-900'}`}>{option}</span>
                </label>
              ))
            ) : (
              <span className="text-gray-500">No options available</span>
            )}
          </div>
        );
      default:
        return <div className="text-gray-500">Unknown field type</div>;
    }
  };

  if (compact) {
    return (
      <div className={`p-4 border-2 rounded-xl shadow-md transition-all duration-200 hover:shadow-lg ${borderColor}`}>
        <div className="mb-2">
          <label className="block text-sm font-semibold text-gray-900 mb-1">
            {field.label}
            {field.required && <span className="text-red-500 ml-1">*</span>}
          </label>
          {field.apiName && (
            <span className="text-xs text-gray-500 font-mono bg-gray-100 px-1.5 py-0.5 rounded">{field.apiName}</span>
          )}
        </div>
        {renderInput()}
        {field.isMatched && (
          <div className="mt-2 flex gap-1">
            <div className={`px-2 py-1 rounded text-xs font-semibold ${getScoreColorClass(confidence)}`}>
              {formatConfidence(confidence)}
            </div>
          </div>
        )}
        {hasExecutedPipeline && isNotAvail && (
          <div className="mt-2 p-1.5 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
            Value not available
          </div>
        )}
        {hasExecutedPipeline && !field.isMatched && (
          <div className="mt-2 p-1.5 bg-red-50 border border-red-200 rounded text-xs text-red-800">
            Field not found
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`p-6 border-2 rounded-xl shadow-md transition-all duration-200 hover:shadow-lg ${borderColor}`}>
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <label className="block text-base font-semibold text-gray-900 mb-1">
            {field.label}
            {field.required && <span className="text-red-500 ml-1">*</span>}
          </label>
          {field.apiName && (
            <span className="text-xs text-gray-500 font-mono bg-gray-100 px-2 py-1 rounded">{field.apiName}</span>
          )}
        </div>
        <div className="flex gap-2 ml-4">
          {field.isMatched && (
            <>
              <div className={`px-3 py-1.5 rounded-lg text-xs font-semibold border-2 ${getScoreColorClass(confidence)}`}>
                Confidence: {formatConfidence(confidence)}
              </div>
              {field.quality_score !== undefined && (
                <div className={`px-3 py-1.5 rounded-lg text-xs font-semibold border-2 ${getScoreColorClass(field.quality_score)}`}>
                  Quality: {formatQualityScore(field.quality_score)}
                </div>
              )}
            </>
          )}
        </div>
      </div>
      {renderInput()}
      {/* Only show warnings/errors after pipeline execution */}
      {hasExecutedPipeline && isNotAvail && (
        <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800 flex items-center">
          <svg className="w-5 h-5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          <span className="font-medium">Value not available in document</span>
        </div>
      )}
      {hasExecutedPipeline && !field.isMatched && (
        <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800 flex items-center">
          <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          <span className="font-medium">Field not found in output</span>
        </div>
      )}
    </div>
  );
}

