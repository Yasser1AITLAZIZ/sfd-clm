"""OCR and Mapping Tool - Combined tool for OCR and field mapping"""
from __future__ import annotations
from typing import Annotated, Any
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from langchain_core.tools import InjectedToolCallId
from langgraph.types import Command
from langchain_core.messages import ToolMessage
import json

from app.state import MCPAgentState
from app.config.llm_builder import LLMBuilderFactory
from .ocr_manager import OCRManager
from .mapping_manager import MappingManager


# Global instances (will be initialized on first use)
_ocr_manager = None
_mapping_manager = None


def _get_ocr_manager():
    """Get or create OCR manager instance"""
    global _ocr_manager
    if _ocr_manager is None:
        llm_builder = LLMBuilderFactory.create_builder("openai")  # Will use config
        _ocr_manager = OCRManager(llm_builder)
    return _ocr_manager


def _get_mapping_manager():
    """Get or create mapping manager instance"""
    global _mapping_manager
    if _mapping_manager is None:
        llm_builder = LLMBuilderFactory.create_builder("openai")  # Will use config
        _mapping_manager = MappingManager(llm_builder)
    return _mapping_manager


def _with_tool_message(state: Any, *, name: str, content: str, tool_call_id: str | None):
    """Helper to add tool message to state"""
    from langchain_core.messages import BaseMessage
    from typing import List
    
    if hasattr(state, "messages"):
        msgs: List[BaseMessage] = list(getattr(state, "messages") or [])
    else:
        msgs = list((state or {}).get("messages", []) or [])
    msgs.append(ToolMessage(name=name, content=content, tool_call_id=tool_call_id))
    return {"messages": msgs}


@tool(description="Extrait le texte des documents avec OCR et mappe les champs Salesforce au texte extrait. Retourne les données extraites avec scores de confiance.")
async def ocr_and_mapping_tool(
    state: Annotated[Any, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Tool combinant OCR et mapping des champs.
    
    Cette tool:
    1. Traite tous les documents avec OCR Manager (extraction de texte)
    2. Mappe les champs Salesforce au texte OCR extrait avec Mapping Manager
    3. Met à jour le state avec extracted_data, confidence_scores, et field_mappings
    """
    print("🔧 [OCR+Mapping Tool] Starting combined OCR and mapping...")
    
    try:
        # Convert state to MCPAgentState if needed
        if not isinstance(state, MCPAgentState):
            state = MCPAgentState(**state) if isinstance(state, dict) else state
        
        # Step 1: OCR Processing
        print("📄 [OCR+Mapping Tool] Step 1: OCR processing...")
        ocr_manager = _get_ocr_manager()
        state = await ocr_manager.process(state)
        
        # Step 2: Field Mapping
        print("🗺️ [OCR+Mapping Tool] Step 2: Field mapping...")
        mapping_manager = _get_mapping_manager()
        mapping_results = await mapping_manager.map_fields_to_ocr(
            ocr_text=state.ocr_text or "",
            text_blocks=state.text_blocks,
            fields_dictionary=state.fields_dictionary
        )
        
        # Calculate quality score (average of confidence scores)
        quality_score = None
        if mapping_results.get("confidence_scores"):
            quality_score = sum(mapping_results["confidence_scores"].values()) / len(mapping_results["confidence_scores"])
        
        # Prepare update patch
        patch = {
            "field_mappings": mapping_results.get("field_mappings", {}),
            "extracted_data": mapping_results.get("extracted_data", {}),
            "confidence_scores": mapping_results.get("confidence_scores", {}),
            "ocr_text": state.ocr_text,
            "text_blocks": [block.model_dump() for block in state.text_blocks],
            "documents": [doc.model_dump() for doc in state.documents]
        }
        if quality_score is not None:
            patch["quality_score"] = quality_score
        
        # Create tool message
        content = json.dumps({
            "status": "completed",
            "fields_extracted": len(mapping_results.get("extracted_data", {})),
            "quality_score": quality_score,
            "ocr_text_length": len(state.ocr_text or ""),
            "text_blocks_count": len(state.text_blocks)
        }, indent=2)
        
        patch.update(_with_tool_message(
            state,
            name="ocr_and_mapping_tool",
            content=content,
            tool_call_id=tool_call_id
        ))
        
        print(f"✅ [OCR+Mapping Tool] Completed: {len(mapping_results.get('extracted_data', {}))} fields extracted")
        if quality_score is not None:
            print(f"📊 [OCR+Mapping Tool] Quality score: {quality_score:.2f}")
        else:
            print(f"📊 [OCR+Mapping Tool] Quality score: None (no confidence scores available)")
        
        return Command(update=patch, graph=Command.PARENT)
        
    except Exception as e:
        print(f"❌ [OCR+Mapping Tool] Error: {e}")
        import traceback
        error_content = json.dumps({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }, indent=2)
        
        patch = _with_tool_message(
            state,
            name="ocr_and_mapping_tool",
            content=error_content,
            tool_call_id=tool_call_id
        )
        patch["errors"] = list(getattr(state, "errors", []) or []) + [f"ocr_mapping_error: {str(e)}"]
        
        return Command(update=patch, graph=Command.PARENT)

