"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


class ReceiveRequestSchema(BaseModel):
    """Request schema for receiving user request"""
    record_id: str = Field(..., description="Salesforce record ID", min_length=1)
    session_id: Optional[str] = Field(default=None, description="Session ID (null for new session)")
    user_message: str = Field(..., description="User message", min_length=1)
    
    @field_validator("record_id", "user_message")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate that string fields are not empty"""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()
    
    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session_id format"""
        if v is None:
            return None
        if not v.strip():
            return None
        return v.strip()


class RequestSalesforceDataSchema(BaseModel):
    """Request schema for requesting Salesforce data"""
    record_id: str = Field(..., description="Salesforce record ID", min_length=1)
    
    @field_validator("record_id")
    @classmethod
    def validate_record_id(cls, v: str) -> str:
        """Validate record_id format"""
        if not v or not v.strip():
            raise ValueError("record_id cannot be empty")
        return v.strip()


class DocumentResponseSchema(BaseModel):
    """Document response schema"""
    document_id: str
    name: str
    url: str
    type: str
    indexed: bool


# Salesforce Form Fields Schemas (new format from Salesforce API)
class SalesforceFormFieldSchema(BaseModel):
    """Schema for Salesforce form field (new format)"""
    label: str
    apiName: Optional[str] = None
    type: str  # text, picklist, radio, number, textarea
    required: bool
    possibleValues: List[str] = Field(default_factory=list)
    defaultValue: Optional[Any] = None
    dataValue_target_AI: Optional[Any] = None  # Field for AI-extracted value (normalized to null initially)


class SalesforceFormFieldsResponseSchema(BaseModel):
    """Schema for Salesforce form fields response (new format)"""
    fields: List[SalesforceFormFieldSchema]


class SalesforceDataResponseSchema(BaseModel):
    """Salesforce data response schema"""
    record_id: str
    record_type: str
    documents: List[DocumentResponseSchema]
    fields_to_fill: List[SalesforceFormFieldSchema]  # Use original schema directly


class InitializationResponseSchema(BaseModel):
    """Response schema for initialization flow"""
    status: Literal["initialization"] = "initialization"
    record_id: str
    session_id: str
    salesforce_data: SalesforceDataResponseSchema
    next_step: Literal["preprocessing"] = "preprocessing"


class ContinuationResponseSchema(BaseModel):
    """Response schema for continuation flow"""
    status: Literal["continuation"] = "continuation"
    session_id: str
    user_message: str
    next_step: Literal["prompt_building"] = "prompt_building"


class ErrorResponseSchema(BaseModel):
    """Error response schema"""
    status: Literal["error"] = "error"
    error: Dict[str, Any]


class ConversationMessageSchema(BaseModel):
    """Schema for conversation message"""
    role: Literal["user", "assistant"]
    message: str
    timestamp: str  # ISO format datetime string


class SessionContextSchema(BaseModel):
    """Schema for session context"""
    salesforce_data: SalesforceDataResponseSchema
    conversation_history: List[ConversationMessageSchema] = Field(default_factory=list)
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=lambda: {
        "preprocessing_completed": False,
        "prompt_built": False,
        "langgraph_processed": False
    })


class SessionSchema(BaseModel):
    """Schema for complete session"""
    session_id: str
    record_id: str
    created_at: str  # ISO format datetime string
    updated_at: str  # ISO format datetime string
    expires_at: str  # ISO format datetime string
    context: SessionContextSchema


# New refactored session schemas
class SessionInputDataSchema(BaseModel):
    """Schema for session input data (what is sent to langgraph)"""
    salesforce_data: SalesforceDataResponseSchema
    user_message: str
    context: Dict[str, Any] = Field(default_factory=dict)  # documents, fields, session_id
    metadata: Dict[str, Any] = Field(default_factory=dict)  # record_id, record_type, timestamp
    prompt: Optional[str] = None
    timestamp: str  # ISO format datetime string


class LanggraphResponseDataSchema(BaseModel):
    """Schema for langgraph response data (complete response from langgraph)"""
    filled_form_json: Optional[List[Dict[str, Any]]] = None  # Primary format with all fields filled (same structure as input)
    extracted_data: Dict[str, Any] = Field(default_factory=dict)  # Deprecated: kept for backward compatibility
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    quality_score: Optional[float] = None
    field_mappings: Dict[str, str] = Field(default_factory=dict)
    processing_time: Optional[float] = None
    ocr_text_length: Optional[int] = None
    text_blocks_count: Optional[int] = None
    timestamp: str  # ISO format datetime string
    status: Literal["success", "error", "partial"] = "success"
    error: Optional[str] = None


class InteractionRequestSchema(BaseModel):
    """Schema for a single interaction request"""
    user_message: str
    prompt: Optional[str] = None
    timestamp: str  # ISO format datetime string


class InteractionResponseSchema(BaseModel):
    """Schema for a single interaction response"""
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    timestamp: str  # ISO format datetime string


class InteractionHistoryItemSchema(BaseModel):
    """Schema for a single interaction in the history"""
    interaction_id: str
    request: InteractionRequestSchema
    response: Optional[InteractionResponseSchema] = None
    processing_time: Optional[float] = None
    status: Literal["success", "error", "partial", "pending"] = "pending"


class ProcessingMetadataSchema(BaseModel):
    """Schema for processing metadata"""
    preprocessing_completed: bool = False
    preprocessing_timestamp: Optional[str] = None
    prompt_built: bool = False
    prompt_built_timestamp: Optional[str] = None
    langgraph_processed: bool = False
    langgraph_processed_timestamp: Optional[str] = None
    workflow_id: Optional[str] = None
    total_processing_time: Optional[float] = None
    additional_metadata: Dict[str, Any] = Field(default_factory=dict)


class RefactoredSessionSchema(BaseModel):
    """Schema for refactored session structure"""
    session_id: str
    record_id: str
    created_at: str  # ISO format datetime string
    updated_at: str  # ISO format datetime string
    expires_at: str  # ISO format datetime string
    status: Literal["active", "completed", "failed", "expired"] = "active"
    input_data: SessionInputDataSchema
    langgraph_response: Optional[LanggraphResponseDataSchema] = None
    interactions_history: List[InteractionHistoryItemSchema] = Field(default_factory=list)
    processing_metadata: ProcessingMetadataSchema = Field(default_factory=ProcessingMetadataSchema)


class WorkflowRequestSchema(BaseModel):
    """Request schema for workflow execution"""
    record_id: str = Field(..., description="Salesforce record ID", min_length=1)
    session_id: Optional[str] = Field(default=None, description="Session ID (null for new session)")
    user_message: str = Field(..., description="User message", min_length=1)
    
    @field_validator("record_id", "user_message")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate that string fields are not empty"""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class WorkflowStepSchema(BaseModel):
    """Schema for workflow step"""
    step_name: str
    status: Literal["pending", "completed", "failed", "skipped"]
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class WorkflowResponseSchema(BaseModel):
    """Response schema for workflow execution"""
    status: Literal["completed", "failed", "paused", "pending"]
    workflow_id: str
    current_step: Optional[str] = None
    steps_completed: List[str] = Field(default_factory=list)
    data: Dict[str, Any] = Field(default_factory=dict)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    started_at: str
    completed_at: Optional[str] = None


# Preprocessing Schemas
class DocumentMetadataSchema(BaseModel):
    """Schema for document metadata"""
    filename: str
    size: int  # Size in bytes
    mime_type: str
    pages_count: int = 0  # For PDFs
    dimensions: Optional[Dict[str, int]] = None  # For images: {"width": 1920, "height": 1080}
    orientation: Optional[str] = None  # "portrait", "landscape", "square"


class ProcessedDocumentSchema(BaseModel):
    """Schema for processed document"""
    document_id: str
    name: str
    url: str
    type: str
    indexed: bool
    metadata: DocumentMetadataSchema
    processed: bool = True




class ContextSummarySchema(BaseModel):
    """Schema for context summary"""
    record_type: str
    objective: str
    documents_available: List[Dict[str, Any]] = Field(default_factory=list)
    fields_to_extract: List[Dict[str, Any]] = Field(default_factory=list)
    business_rules: List[str] = Field(default_factory=list)


class PreprocessedDataSchema(BaseModel):
    """Schema for preprocessed data"""
    record_id: str
    record_type: str
    processed_documents: List[ProcessedDocumentSchema] = Field(default_factory=list)
    salesforce_data: SalesforceDataResponseSchema  # Keep original salesforce data with fields_to_fill
    context_summary: ContextSummarySchema
    validation_results: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)


# Prompting Schemas
class InitializationPromptSchema(BaseModel):
    """Schema for initialization prompt"""
    prompt: str
    record_id: str
    record_type: str
    documents_count: int
    fields_count: int


class ContinuationPromptSchema(BaseModel):
    """Schema for continuation prompt"""
    prompt: str
    session_id: str
    history_length: int


class PromptResponseSchema(BaseModel):
    """Schema for prompt response"""
    prompt: str
    scenario_type: Literal["initialization", "extraction", "clarification", "validation", "continuation"]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OptimizedPromptSchema(BaseModel):
    """Schema for optimized prompt"""
    prompt: str
    original_length: int
    optimized_length: int
    tokens_estimated: int
    quality_score: float  # 0-100
    optimizations_applied: List[str] = Field(default_factory=list)
    cost_estimated: Optional[float] = None


class PromptMetricsSchema(BaseModel):
    """Schema for prompt metrics"""
    tokens_used: int
    cost_estimated: Optional[float] = None
    quality_score: float
    processing_time_seconds: Optional[float] = None


# MCP Schemas
class MCPMetadataSchema(BaseModel):
    """Schema for MCP message metadata"""
    record_id: str
    record_type: str
    timestamp: str  # ISO format datetime string


class MCPMessageSchema(BaseModel):
    """Schema for MCP message"""
    message_id: str
    prompt: str
    context: Dict[str, Any]
    metadata: MCPMetadataSchema


class MCPResponseSchema(BaseModel):
    """Schema for MCP response"""
    message_id: str
    filled_form_json: Optional[List[Dict[str, Any]]] = None  # Same structure as input with dataValue_target_AI filled
    extracted_data: Dict[str, Any] = Field(default_factory=dict)  # Deprecated: kept for backward compatibility
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    quality_score: Optional[float] = None  # Overall quality score from LangGraph
    status: Literal["success", "error", "partial"] = "success"
    error: Optional[str] = None


class LanggraphResponseSchema(BaseModel):
    """Schema for Langgraph response"""
    filled_form_json: Optional[List[Dict[str, Any]]] = None  # Same structure as input with dataValue_target_AI filled
    extracted_data: Dict[str, Any] = Field(default_factory=dict)  # Deprecated: kept for backward compatibility
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    quality_score: Optional[float] = None
    processing_time: Optional[float] = None
    tokens_used: Optional[int] = None


class MCPConnectionSchema(BaseModel):
    """Schema for MCP connection status"""
    connected: bool
    langgraph_url: str
    last_ping: Optional[str] = None


class MCPHealthCheckSchema(BaseModel):
    """Schema for MCP health check"""
    status: Literal["ok", "error"]
    message: Optional[str] = None


# Task Queue Schemas
class TaskStatusSchema(BaseModel):
    """Schema for task status"""
    task_id: str
    status: Literal["pending", "processing", "completed", "failed", "not_found", "error"]
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TaskResponseSchema(BaseModel):
    """Schema for task response"""
    task_id: str
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None