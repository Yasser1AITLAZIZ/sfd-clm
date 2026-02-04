"""LangGraph State for MCP Agent"""
from __future__ import annotations
from typing import List, Dict, Optional, Any, Annotated
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class TextBlock(BaseModel):
    """Visual block extracted from OCR with bounding box coordinates.
    
    - text: extracted text content from the block
    - bbox: bounding box coordinates normalized [0,1] relative to image dimensions
      Format: {"x": float, "y": float, "width": float, "height": float}
    - block_type: type of block (paragraph, heading, table_cell, line, field_pair)
    - confidence: confidence score for this block [0,1]
    - block_id: unique identifier (hash of text + position)
    """
    text: str
    bbox: Dict[str, float]  # {x, y, width, height} normalized [0,1]
    block_type: str  # paragraph, heading, table_cell, line, field_pair
    confidence: float  # [0,1]
    block_id: str


class PageOCR(BaseModel):
    """OCR result and quality metrics for a single page image.

    - page_number: 1-based index within the document
    - image_b64/image_mime: original page image payload and mime (can be None after OCR success)
    - ocr_text: extracted text if available
    - quality_score_ocerization: normalized OCR quality score in [0,1]
    - issues: normalized list of quality issues
    - text_blocks: visual blocks with bounding boxes extracted from OCR
    - image_path: path to saved image file on disk (after OCR completion)
    """
    page_number: int
    image_b64: Optional[str] = None  # Can be removed after OCR success to reduce state size
    image_mime: str = ""
    ocr_text: Optional[str] = None
    processed: bool = False
    quality_score_ocerization: float = 0.0
    quality_justification: str = ""
    issues: List[str] = Field(default_factory=list)
    text_blocks: List[TextBlock] = Field(default_factory=list)
    image_path: Optional[str] = None


class Document(BaseModel):
    """Ingested document with classification metadata and page-level OCR.

    The `type_canonical` is a normalized document type when available.
    """
    id: str
    type: str = ""
    type_canonical: Optional[str] = None
    type_confidence: float = 0.0
    evidence_classification: List[Dict] = Field(default_factory=list)
    pages: List[PageOCR] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict)  # filename, mime, size, page_count...


class MCPAgentState(BaseModel):
    """Global state for the MCP Agent workflow.

    This Pydantic model is used as the state schema of the LangGraph.
    It stores MCP request data, documents, OCR results, field mappings,
    extracted data, and the conversation history.
    It remains compatible with `create_react_agent` (requires `remaining_steps`).
    """

    # Autoriser les types non-pydantic (ex: BaseMessage)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # ⚠️ Requis par create_react_agent
    remaining_steps: int = 50

    # Routage / contrôle
    next_step: Optional[str] = None

    # Données MCP
    record_id: str = ""
    session_id: Optional[str] = None
    user_request: str = ""

    # Documents et OCR
    documents: List[Document] = Field(default_factory=list)
    ocr_text: Optional[str] = None
    text_blocks: List[TextBlock] = Field(default_factory=list)

    # Mapping et extraction
    form_json: List[Dict[str, Any]] = Field(default_factory=list)  # Form JSON as-is from input
    filled_form_json: Optional[List[Dict[str, Any]]] = None  # Form JSON with dataValue_target_AI filled
    fields_dictionary: Dict[str, Any] = Field(default_factory=dict)  # Deprecated: kept for compatibility
    field_mappings: Dict[str, Any] = Field(default_factory=dict)  # {field_name: mapping_dict} where mapping_dict can be str or Dict with 'value', 'confidence', 'source', 'justification'
    extracted_data: Dict[str, Any] = Field(default_factory=dict)  # Deprecated: kept for backward compatibility
    confidence_scores: Dict[str, float] = Field(default_factory=dict)

    # Validation
    validation_results: Dict[str, Any] = Field(default_factory=dict)
    quality_score: Optional[float] = None

    # Messages
    messages: Annotated[List[BaseMessage], add_messages] = Field(default_factory=list)

    # Erreurs
    errors: List[str] = Field(default_factory=list)

