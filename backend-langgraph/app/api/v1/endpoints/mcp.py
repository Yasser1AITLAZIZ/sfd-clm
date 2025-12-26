"""MCP endpoint for processing requests"""
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional
import logging
import uuid
import random
import asyncio
from datetime import datetime

from app.core.logging import get_logger, safe_log
from app.core.config import settings
from app.state import MCPAgentState, Document, PageOCR
from app.utils.singletons import get_compiled_graph

logger = get_logger(__name__)

router = APIRouter()


def generate_mock_extracted_data(fields_dictionary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate mock extracted data based on fields_dictionary.
    
    Args:
        fields_dictionary: Dictionary of field definitions
        
    Returns:
        Dictionary of extracted field values
    """
    extracted_data = {}
    
    # Sample data generators based on field labels
    sample_texts = {
        "nom": "Jean Dupont",
        "prénom": "Jean",
        "adresse": "123 Rue de la Paix, 75001 Paris",
        "téléphone": "+33 1 23 45 67 89",
        "email": "jean.dupont@example.com",
        "date": "2024-01-15",
        "commentaire": "Ceci est un commentaire de test généré automatiquement pour simuler l'extraction de données depuis un document.",
        "search": "Recherche effectuée avec succès"
    }
    
    for field_name, field_config in fields_dictionary.items():
        field_type = field_config.get("type", "text").lower()
        field_label = field_config.get("label", "").lower()
        is_required = field_config.get("required", False)
        possible_values = field_config.get("possibleValues", [])
        default_value = field_config.get("defaultValue")
        
        # Skip optional fields 30% of the time
        if not is_required and random.random() < 0.3:
            extracted_data[field_name] = None
            continue
        
        # Generate value based on type
        if field_type in ["picklist", "radio"]:
            # Select from possible values
            if possible_values:
                extracted_data[field_name] = random.choice(possible_values)
            elif default_value:
                extracted_data[field_name] = default_value
            else:
                extracted_data[field_name] = "Valeur par défaut"
        
        elif field_type == "number":
            # Generate random number
            if "taux" in field_label or "pourcentage" in field_label:
                extracted_data[field_name] = round(random.uniform(0, 100), 2)
            elif "nombre" in field_label:
                extracted_data[field_name] = random.randint(1, 10)
            else:
                extracted_data[field_name] = random.randint(0, 10000)
        
        elif field_type == "textarea":
            # Generate multi-line text
            if "commentaire" in field_label:
                extracted_data[field_name] = sample_texts.get("commentaire", "Commentaire généré automatiquement pour les tests.")
            else:
                extracted_data[field_name] = "Texte multi-lignes généré automatiquement.\nLigne 2 du texte.\nLigne 3 du texte."
        
        else:  # text or other
            # Try to match label to sample data
            value = None
            for key, sample_value in sample_texts.items():
                if key in field_label:
                    value = sample_value
                    break
            
            if value is None:
                # Generate based on label
                if "date" in field_label:
                    value = "2024-01-15"
                elif "numéro" in field_label or "n°" in field_label:
                    value = f"{random.randint(1000, 9999)}"
                else:
                    # Use label as base for value
                    value = f"Valeur pour {field_config.get('label', field_name)}"
            
            extracted_data[field_name] = value
    
    return extracted_data


def generate_mock_confidence_scores(
    extracted_data: Dict[str, Any],
    fields_dictionary: Dict[str, Any]
) -> Dict[str, float]:
    """
    Generate mock confidence scores for extracted data.
    
    Args:
        extracted_data: Dictionary of extracted field values
        fields_dictionary: Dictionary of field definitions
        
    Returns:
        Dictionary of confidence scores (0.0-1.0)
    """
    confidence_scores = {}
    
    for field_name, value in extracted_data.items():
        if value is None:
            confidence_scores[field_name] = 0.0
            continue
        
        field_config = fields_dictionary.get(field_name, {})
        is_required = field_config.get("required", False)
        field_type = field_config.get("type", "text").lower()
        
        # Required fields have higher confidence (0.85-0.95)
        if is_required:
            confidence_scores[field_name] = round(random.uniform(0.85, 0.95), 2)
        # Picklist/radio with possible values have high confidence (0.80-0.95)
        elif field_type in ["picklist", "radio"] and field_config.get("possibleValues"):
            confidence_scores[field_name] = round(random.uniform(0.80, 0.95), 2)
        # Optional fields have lower confidence (0.70-0.85)
        else:
            confidence_scores[field_name] = round(random.uniform(0.70, 0.85), 2)
    
    return confidence_scores


def generate_mock_ocr_data(documents: list) -> Dict[str, Any]:
    """
    Generate mock OCR data based on documents.
    
    Args:
        documents: List of document data
        
    Returns:
        Dictionary with ocr_text_length, text_blocks_count, and field_mappings
    """
    total_pages = sum(len(doc.get("pages", [])) for doc in documents)
    
    # Estimate OCR text length (roughly 500-2000 chars per page)
    ocr_text_length = total_pages * random.randint(500, 2000)
    
    # Estimate text blocks (roughly 10-30 blocks per page)
    text_blocks_count = total_pages * random.randint(10, 30)
    
    # Generate sample OCR text
    ocr_text = " ".join([
        "Document traité avec succès.",
        "Texte extrait automatiquement pour simulation.",
        "Données OCR générées pour les tests."
    ] * (total_pages * 2))
    
    return {
        "ocr_text_length": ocr_text_length,
        "text_blocks_count": text_blocks_count,
        "ocr_text": ocr_text[:ocr_text_length]  # Truncate to estimated length
    }


async def mock_process_mcp_request(request: Request) -> JSONResponse:
    """
    Mock MCP request processing that simulates the full workflow.
    
    Returns mock data in the exact format expected by backend-mcp.
    """
    request_id = str(uuid.uuid4())
    record_id = None
    session_id = None
    
    try:
        # Parse request body
        body = await request.json()
        
        record_id = body.get("record_id", "")
        session_id = body.get("session_id")
        user_request = body.get("user_request", "")
        documents_data = body.get("documents", [])
        fields_dictionary = body.get("fields_dictionary", {})
        
        # #region agent log
        import json as json_lib
        import time
        try:
            with open(r'c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_lib.dumps({"id":f"log_{int(time.time()*1000)}_mock_received","timestamp":int(time.time()*1000),"location":"mcp.py:195","message":"Mock request received","data":{"record_id":record_id,"fields_dict_keys":list(fields_dictionary.keys()),"fields_dict_count":len(fields_dictionary)},"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + "\n")
        except: pass
        # #endregion
        
        # Validate required fields
        if not record_id or not record_id.strip():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_RECORD_ID",
                        "message": "record_id cannot be empty"
                    }
                }
            )
        
        safe_log(
            logger,
            logging.INFO,
            "Mock MCP request received",
            request_id=request_id,
            record_id=record_id,
            session_id=session_id or "none",
            documents_count=len(documents_data),
            fields_count=len(fields_dictionary)
        )
        
        # Simulate processing time (1-3 seconds)
        processing_time = random.uniform(1.0, 3.0)
        await asyncio.sleep(processing_time)
        
        # Generate mock extracted data
        extracted_data = generate_mock_extracted_data(fields_dictionary)
        # #region agent log
        try:
            with open(r'c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_lib.dumps({"id":f"log_{int(time.time()*1000)}_mock_data_generated","timestamp":int(time.time()*1000),"location":"mcp.py:220","message":"Mock extracted data generated","data":{"extracted_data_keys":list(extracted_data.keys()),"extracted_data_count":len(extracted_data),"sample_data":dict(list(extracted_data.items())[:3])},"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + "\n")
        except: pass
        # #endregion
        
        # Generate mock confidence scores
        confidence_scores = generate_mock_confidence_scores(extracted_data, fields_dictionary)
        # #region agent log
        try:
            with open(r'c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_lib.dumps({"id":f"log_{int(time.time()*1000)}_mock_response_built","timestamp":int(time.time()*1000),"location":"mcp.py:268","message":"Mock response built","data":{"extracted_data_count":len(extracted_data),"confidence_scores_count":len(confidence_scores),"quality_score":quality_score,"response_status":"success"},"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + "\n")
        except: pass
        # #endregion
        
        # Calculate quality score (average of confidence scores)
        if confidence_scores:
            quality_score = round(sum(confidence_scores.values()) / len(confidence_scores), 2)
        else:
            quality_score = 0.85
        
        # Generate mock OCR data
        ocr_data = generate_mock_ocr_data(documents_data)
        
        # Generate field mappings (map each field to a location in OCR text)
        field_mappings = {}
        for field_name in extracted_data.keys():
            if extracted_data[field_name] is not None:
                field_mappings[field_name] = {
                    "location": f"Page 1, Block {random.randint(1, 20)}",
                    "confidence": confidence_scores.get(field_name, 0.85)
                }
        
        safe_log(
            logger,
            logging.INFO,
            "Mock MCP request processed",
            request_id=request_id,
            record_id=record_id,
            fields_extracted=len(extracted_data),
            quality_score=quality_score,
            processing_time=processing_time
        )
        
        # Build response in exact format expected by backend-mcp
        response_data = {
            "extracted_data": extracted_data,
            "confidence_scores": confidence_scores,
            "quality_score": quality_score,
            "field_mappings": field_mappings,
            "processing_time": round(processing_time, 2),
            "ocr_text_length": ocr_data["ocr_text_length"],
            "text_blocks_count": ocr_data["text_blocks_count"]
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "data": response_data
            }
        )
        
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Error in mock MCP request processing",
            request_id=request_id,
            record_id=record_id or "unknown",
            session_id=session_id or "none",
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred in mock mode",
                    "details": str(e) if e else None
                }
            }
        )


@router.post(
    "/api/langgraph/process-mcp-request",
    status_code=status.HTTP_200_OK,
    summary="Process MCP request with LangGraph",
    description="Receives MCP request with documents and fields, processes with OCR and mapping, returns extracted data"
)
async def process_mcp_request(request: Request) -> JSONResponse:
    """
    Process MCP request using LangGraph workflow.
    
    Expected request body:
    {
        "record_id": "string",
        "session_id": "string (optional)",
        "user_request": "string",
        "documents": [
            {
                "id": "string",
                "type": "string",
                "pages": [
                    {
                        "page_number": 1,
                        "image_b64": "base64 string",
                        "image_mime": "image/jpeg"
                    }
                ]
            }
        ],
        "fields_dictionary": {
            "field_name": {
                "label": "string",
                "type": "string",
                "required": bool,
                "possibleValues": []
            }
        }
    }
    """
    # #region agent log
    import json as json_lib
    import time
    import os
    try:
        with open(r'c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json_lib.dumps({"id":f"log_{int(time.time()*1000)}_check_mock_mode","timestamp":int(time.time()*1000),"location":"mcp.py:361","message":"Checking mock_mode setting","data":{"mock_mode":settings.mock_mode,"mock_mode_type":type(settings.mock_mode).__name__,"env_mock_mode":os.getenv("MOCK_MODE","not_set")},"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + "\n")
    except Exception as e:
        # Log to stderr if file write fails
        import sys
        print(f"DEBUG LOG ERROR: {e}", file=sys.stderr)
    # #endregion
    # Check if mock mode is enabled
    if settings.mock_mode:
        # #region agent log
        try:
            with open(r'c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_lib.dumps({"id":f"log_{int(time.time()*1000)}_using_mock","timestamp":int(time.time()*1000),"location":"mcp.py:309","message":"Using mock mode","data":{},"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + "\n")
        except: pass
        # #endregion
        return await mock_process_mcp_request(request)
    
    # Original LangGraph processing
    request_id = str(uuid.uuid4())
    record_id = None
    session_id = None
    
    try:
        # Parse request body
        body = await request.json()
        
        record_id = body.get("record_id", "")
        session_id = body.get("session_id")
        user_request = body.get("user_request", "")
        documents_data = body.get("documents", [])
        fields_dictionary = body.get("fields_dictionary", {})
        
        # Validate required fields
        if not record_id or not record_id.strip():
            safe_log(
                logger,
                logging.WARNING,
                "Empty record_id provided",
                request_id=request_id,
                endpoint="/api/langgraph/process-mcp-request"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_RECORD_ID",
                        "message": "record_id cannot be empty"
                    }
                }
            )
        
        if not user_request or not user_request.strip():
            safe_log(
                logger,
                logging.WARNING,
                "Empty user_request provided",
                request_id=request_id,
                record_id=record_id
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error": {
                        "code": "INVALID_USER_REQUEST",
                        "message": "user_request cannot be empty"
                    }
                }
            )
        
        safe_log(
            logger,
            logging.INFO,
            "MCP request received",
            request_id=request_id,
            record_id=record_id,
            session_id=session_id or "none",
            documents_count=len(documents_data),
            fields_count=len(fields_dictionary)
        )
        
        # Convert documents data to Document objects
        documents = []
        for doc_data in documents_data:
            pages = []
            for page_data in doc_data.get("pages", []):
                pages.append(PageOCR(
                    page_number=page_data.get("page_number", 1),
                    image_b64=page_data.get("image_b64", ""),
                    image_mime=page_data.get("image_mime", "image/jpeg"),
                    processed=False
                ))
            
            documents.append(Document(
                id=doc_data.get("id", str(uuid.uuid4())),
                type=doc_data.get("type", ""),
                pages=pages,
                metadata=doc_data.get("metadata", {})
            ))
        
        # Initialize state
        initial_state = MCPAgentState(
            record_id=record_id,
            session_id=session_id,
            user_request=user_request,
            documents=documents,
            fields_dictionary=fields_dictionary,
            remaining_steps=50
        )
        
        # Add initial user message
        from langchain_core.messages import HumanMessage
        initial_state.messages.append(HumanMessage(content=user_request))
        
        # Get compiled graph and execute
        graph = get_compiled_graph()
        
        safe_log(
            logger,
            logging.INFO,
            "Starting LangGraph execution",
            request_id=request_id,
            record_id=record_id
        )
        
        start_time = datetime.utcnow()
        
        # Execute graph
        config = {"configurable": {"thread_id": f"{record_id}_{session_id or 'new'}"}}
        final_state = await graph.ainvoke(initial_state, config)
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        safe_log(
            logger,
            logging.INFO,
            "LangGraph execution completed",
            request_id=request_id,
            record_id=record_id,
            execution_time=execution_time,
            fields_extracted=len(final_state.extracted_data),
            quality_score=final_state.quality_score
        )
        
        # Build response
        response_data = {
            "extracted_data": final_state.extracted_data,
            "confidence_scores": final_state.confidence_scores,
            "quality_score": final_state.quality_score,
            "field_mappings": final_state.field_mappings,
            "processing_time": execution_time,
            "ocr_text_length": len(final_state.ocr_text or ""),
            "text_blocks_count": len(final_state.text_blocks)
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "data": response_data
            }
        )
        
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Error processing MCP request",
            request_id=request_id,
            record_id=record_id or "unknown",
            session_id=session_id or "none",
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred",
                    "details": str(e) if e else None
                }
            }
        )

