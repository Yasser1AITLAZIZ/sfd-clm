"""do_mapping_tool - mapping des champs depuis l'OCR (avec validation_feedback optionnel)."""
from __future__ import annotations
from typing import Annotated, Any

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from app.state import PreFillingSubAgentState, Document
from app.nodes.ocr_mapping_tool.mapping_manager import MappingManager
from app.config.llm_builder import LLMBuilderFactory

_mapping_manager: MappingManager | None = None


def _get_mapping_manager() -> MappingManager:
    global _mapping_manager
    if _mapping_manager is None:
        _mapping_manager = MappingManager(LLMBuilderFactory.create_builder("openai"))
    return _mapping_manager


@tool(description="Effectue le mapping des champs depuis l'OCR (première passe ou correction avec feedback de validation).")
async def do_mapping_tool(
    state: Annotated[Any, InjectedState],
) -> Command:
    """
    Calls MappingManager.map_fields_to_ocr with validation_feedback from validation_results.expert_validation.
    Returns Command(update={ filled_form_json, confidence_scores, quality_score }).
    """
    if not isinstance(state, PreFillingSubAgentState):
        state = PreFillingSubAgentState(**state) if isinstance(state, dict) else state

    documents = getattr(state, "documents", []) or []
    form_json = getattr(state, "form_json", []) or []
    validation_results = getattr(state, "validation_results", {}) or {}
    validation_feedback = validation_results.get("expert_validation") if validation_results else None

    # Deserialize documents if dicts (e.g. from Shared Storage)
    docs = []
    for d in documents:
        if isinstance(d, Document):
            docs.append(d)
        elif isinstance(d, dict):
            # Rebuild Document with pages as PageOCR
            from app.state import PageOCR
            pages = []
            for p in d.get("pages", []):
                if isinstance(p, dict):
                    pages.append(PageOCR(**p))
                else:
                    pages.append(p)
            docs.append(Document(**{**d, "pages": pages}))
        else:
            docs.append(d)

    result = await _get_mapping_manager().map_fields_to_ocr(
        documents=docs,
        form_json=form_json,
        validation_feedback=validation_feedback,
    )

    return Command(update={
        "filled_form_json": result.get("filled_form_json"),
        "confidence_scores": result.get("confidence_scores", {}),
        "quality_score": result.get("quality_score"),
    })
