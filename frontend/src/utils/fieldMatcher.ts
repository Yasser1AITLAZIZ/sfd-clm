// Field matching utility - CRITICAL for matching fields by exact label
import type { FormField, FilledFormField, MatchedField } from '../types/form';

/**
 * Matches input form fields with output filled form fields by exact label (case-sensitive)
 * 
 * @param inputFields - Array of form fields from mock Salesforce (step1_output.json)
 * @param outputFields - Array of filled form fields from pipeline output (step7_output.json)
 * @returns Array of matched fields with dataValue_target_AI, confidence, and quality_score
 */
export function matchFields(
  inputFields: FormField[],
  outputFields: FilledFormField[]
): MatchedField[] {
  const matched: MatchedField[] = [];
  const unmatchedLabels: string[] = [];

  // Normalize output fields for easier matching (handle case-insensitive as fallback)
  const outputFieldsMap = new Map<string, FilledFormField>();
  const outputFieldsLowerMap = new Map<string, FilledFormField>();
  
  for (const outputField of outputFields) {
    if (outputField.label) {
      outputFieldsMap.set(outputField.label, outputField);
      outputFieldsLowerMap.set(outputField.label.toLowerCase().trim(), outputField);
    }
  }

  for (const inputField of inputFields) {
    // Exact label matching (case-sensitive) - primary method
    let matchedOutput = outputFieldsMap.get(inputField.label);
    
    // Fallback: case-insensitive matching if exact match fails
    if (!matchedOutput) {
      matchedOutput = outputFieldsLowerMap.get(inputField.label.toLowerCase().trim());
      if (matchedOutput) {
        console.warn(`Field matched case-insensitively: "${inputField.label}" -> "${matchedOutput.label}"`);
      }
    }

    if (matchedOutput) {
      matched.push({
        ...inputField,
        dataValue_target_AI: matchedOutput.dataValue_target_AI,
        confidence: matchedOutput.confidence,
        quality_score: matchedOutput.quality_score,
        isMatched: true
      });
    } else {
      console.warn(`Field not found in output: "${inputField.label}"`);
      unmatchedLabels.push(inputField.label);
      matched.push({
        ...inputField,
        dataValue_target_AI: null,
        confidence: 0,
        quality_score: 0,
        isMatched: false
      });
    }
  }

  // Validate all fields matched
  if (unmatchedLabels.length > 0) {
    console.error(`Unmatched fields (${unmatchedLabels.length}): ${unmatchedLabels.join(', ')}`);
    console.log('Available output field labels:', Array.from(outputFieldsMap.keys()));
  }

  return matched;
}

/**
 * Gets confidence score for a field, with fallback to root-level confidence_scores
 */
export function getConfidenceScore(
  field: MatchedField,
  rootConfidenceScores?: Record<string, number>
): number {
  if (field.confidence !== undefined) {
    return field.confidence;
  }
  if (rootConfidenceScores && field.label in rootConfidenceScores) {
    return rootConfidenceScores[field.label];
  }
  return 0;
}

/**
 * Checks if a field value indicates "not available"
 */
export function isNotAvailable(value: string | null | undefined): boolean {
  if (value === null || value === undefined) return true;
  const normalized = String(value).toLowerCase().trim();
  return normalized === "non disponible" || normalized === "" || normalized === "null" || normalized === "undefined";
}

/**
 * Gets color class for confidence/quality score
 */
export function getScoreColorClass(score: number): string {
  if (score >= 0.8) return "text-green-600 bg-green-50 border-green-200";
  if (score >= 0.5) return "text-yellow-600 bg-yellow-50 border-yellow-200";
  return "text-red-600 bg-red-50 border-red-200";
}

