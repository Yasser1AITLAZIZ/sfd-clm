// Form field types based on step1_output.json and step7_output.json

export type FieldType = "text" | "picklist" | "radio" | "number" | "textarea";

export interface FormField {
  label: string;                    // REQUIRED - used for matching
  apiName: string | null;            // Optional, may be null or missing
  type: FieldType;
  required: boolean;
  possibleValues: string[];         // Empty array for text/number/textarea
  defaultValue: string | null;      // May be null
}

export interface FilledFormField {
  label: string;                     // REQUIRED - exact match with input
  apiName?: string | null;          // Optional, may be missing entirely
  type: FieldType;
  required: boolean;
  possibleValues: string[];
  defaultValue: string | null;
  dataValue_target_AI: string;       // REQUIRED - extracted value or "non disponible"
  confidence: number;                // 0.0 to 1.0
  quality_score: number;            // 0.0 to 1.0
}

export interface MatchedField extends FormField {
  dataValue_target_AI?: string | null;
  confidence?: number;
  quality_score?: number;
  isMatched: boolean;
}

export interface Document {
  document_id: string;
  name: string;
  url: string;
  type: string;
  indexed: boolean;
}

export interface MockSalesforceResponse {
  record_id: string;
  record_type: string;
  documents: Document[];
  fields_to_fill: [];               // Empty array in provided example
  fields: FormField[];              // Array of form fields
}

export interface PipelineOutputResponse {
  message_id: string;
  filled_form_json: FilledFormField[];  // Array with dataValue_target_AI filled
  extracted_data: Record<string, any>;  // Empty object in provided example
  confidence_scores: Record<string, number>;  // Keyed by field label
  status: "success" | "error";
  error: string | null;
}

