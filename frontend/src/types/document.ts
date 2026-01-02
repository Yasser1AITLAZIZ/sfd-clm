// Document types

export interface DocumentMetadata {
  document_id: string;
  name: string;
  url: string;
  type: string;
  indexed: boolean;
}

export interface OCRTextBlock {
  page_number: number;
  block_index: number;
  text: string;
  confidence?: number;
  bounding_box?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface FieldMapping {
  field_label: string;
  ocr_text: string;
  confidence: number;
  source_page?: number;
  source_block?: number;
}

