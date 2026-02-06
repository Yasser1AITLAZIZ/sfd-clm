"""qa_validation_tool - used by Q/A Manager."""
from __future__ import annotations
from typing import Annotated, Any

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from app.state import QASubAgentState, Document
from .qa_validation_manager import QAValidationManager

_manager: QAValidationManager | None = None


def _get_manager() -> QAValidationManager:
    global _manager
    if _manager is None:
        _manager = QAValidationManager()
    return _manager


@tool(description="Valide la qualité et la cohérence globale du formulaire prérempli.")
async def qa_validation_tool(
    state: Annotated[Any, InjectedState],
) -> Command:
    """Calls QAValidationManager.validate_qa and writes result to validation_results.qa_validation."""
    if not isinstance(state, QASubAgentState):
        state = QASubAgentState(**state) if isinstance(state, dict) else state

    filled = getattr(state, "filled_form_json", []) or []
    form_json = getattr(state, "form_json", []) or []
    documents = getattr(state, "documents", []) or []

    docs = []
    for d in documents:
        if isinstance(d, Document):
            docs.append(d)
        elif isinstance(d, dict):
            from app.state import PageOCR
            pages = [PageOCR(**p) if isinstance(p, dict) else p for p in d.get("pages", [])]
            docs.append(Document(**{**d, "pages": pages}))
        else:
            docs.append(d)

    result = await _get_manager().validate_qa(
        filled_form_json=filled,
        form_json=form_json,
        documents=docs,
    )

    validation_results = dict(getattr(state, "validation_results", {}) or {})
    validation_results["qa_validation"] = result.get("qa_validation", {})

    return Command(update={"validation_results": validation_results})
