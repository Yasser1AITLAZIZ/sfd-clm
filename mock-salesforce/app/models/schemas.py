"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
from datetime import datetime


class DocumentSchema(BaseModel):
    """Document schema"""
    document_id: str = Field(..., description="Document identifier")
    name: str = Field(..., description="Document name")
    url: str = Field(..., description="Document URL")
    type: str = Field(..., description="MIME type")
    indexed: bool = Field(default=True, description="Whether document is indexed")
    
    @field_validator("document_id", "name", "url", "type")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate that string fields are not empty"""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class FieldToFillSchema(BaseModel):
    """Field to fill schema (old format)"""
    field_name: str = Field(..., description="Field name")
    field_type: str = Field(..., description="Field type (currency, date, text, etc.)")
    value: Optional[str] = Field(default=None, description="Current value (null if empty)")
    required: bool = Field(default=True, description="Whether field is required")
    label: str = Field(..., description="Field label")
    
    @field_validator("field_name", "field_type", "label")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate that string fields are not empty"""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class SalesforceFormFieldSchema(BaseModel):
    """Salesforce form field schema (new format from Salesforce API)"""
    label: str = Field(..., description="Field label")
    apiName: Optional[str] = Field(default=None, description="API name of the field")
    type: str = Field(..., description="Field type: text, picklist, radio, number, textarea")
    required: bool = Field(default=False, description="Whether field is required")
    possibleValues: List[str] = Field(default_factory=list, description="Possible values for picklist/radio")
    defaultValue: Optional[str] = Field(default=None, description="Default value")
    
    @field_validator("label", "type")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate that string fields are not empty"""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class GetRecordDataRequest(BaseModel):
    """Request schema for getting record data"""
    record_id: str = Field(..., description="Salesforce record ID", min_length=1)
    
    @field_validator("record_id")
    @classmethod
    def validate_record_id(cls, v: str) -> str:
        """Validate record ID format"""
        if not v or not v.strip():
            raise ValueError("record_id cannot be empty")
        # Basic Salesforce ID format validation (starts with alphanumeric)
        if not v.strip()[0].isalnum():
            raise ValueError("Invalid record_id format")
        return v.strip()


class GetRecordDataResponse(BaseModel):
    """Response schema for record data (supports both old and new format)"""
    record_id: str = Field(..., description="Salesforce record ID")
    record_type: str = Field(default="Claim", description="Record type")
    documents: List[DocumentSchema] = Field(default_factory=list, description="List of documents")
    fields_to_fill: List[FieldToFillSchema] = Field(default_factory=list, description="Fields to fill (old format)")
    fields: List[SalesforceFormFieldSchema] = Field(default_factory=list, description="Fields (new format)")
    
    def to_dict_new_format(self) -> dict:
        """Convert to new format dict with 'fields' instead of 'fields_to_fill'"""
        return {
            "record_id": self.record_id,
            "record_type": self.record_type,
            "documents": [doc.model_dump() for doc in self.documents],
            "fields": [field.model_dump() for field in self.fields] if self.fields else []
        }
    
    def to_dict_old_format(self) -> dict:
        """Convert to old format dict with 'fields_to_fill'"""
        return {
            "record_id": self.record_id,
            "record_type": self.record_type,
            "documents": [doc.model_dump() for doc in self.documents],
            "fields_to_fill": [field.model_dump() for field in self.fields_to_fill]
        }
    
    class Config:
        json_schema_extra = {
            "example": {
                "record_id": "001XXXX",
                "record_type": "Claim",
                "documents": [
                    {
                        "document_id": "doc_1",
                        "name": "facture.pdf",
                        "url": "https://example.com/documents/facture.pdf",
                        "type": "application/pdf",
                        "indexed": True
                    }
                ],
                "fields_to_fill": [
                    {
                        "field_name": "montant_total",
                        "field_type": "currency",
                        "value": None,
                        "required": True,
                        "label": "Montant total"
                    }
                ]
            }
        }


class SendUserRequestSchema(BaseModel):
    """Request schema for sending user request from Apex"""
    record_id: str = Field(..., description="Salesforce record ID", min_length=1)
    session_id: Optional[str] = Field(default=None, description="Session ID (null for new session)")
    user_request: str = Field(..., description="User request message", min_length=1)
    
    @field_validator("record_id", "user_request")
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


class SendUserRequestResponseSchema(BaseModel):
    """Response schema for send user request"""
    status: Literal["sent"] = "sent"
    request_id: str
    record_id: str
    session_id: Optional[str] = None
    timestamp: str  # ISO format datetime string

