"""Q/A Manager - sub-agent with qa_validation_tool."""
from __future__ import annotations
import logging

from app.state import MCPAgentState, Document, QASubAgentState
from app.utils.singletons import get_shared_storage
from .qa_manager import QAManager

logger = logging.getLogger(__name__)


def _documents_from_template(template_info: dict) -> list:
    """Build list of Document from template_info['documents_classified']."""
    docs = []
    for d in template_info.get("documents_classified", []):
        if isinstance(d, Document):
            docs.append(d)
        elif isinstance(d, dict):
            from app.state import PageOCR
            pages = [PageOCR(**p) if isinstance(p, dict) else p for p in d.get("pages", [])]
            docs.append(Document(**{**d, "pages": pages}))
        else:
            docs.append(d)
    return docs


async def qa_manager_node(state: MCPAgentState) -> MCPAgentState:
    """
    1. Get template_info from Shared Storage (or state fallback).
    2. Build QASubAgentState from state.filled_form_json and template_info.
    3. Run QAManager ReAct agent.
    4. Update state.validation_results.qa_validation, user_response_message, step_completed.
    """
    shared_storage = get_shared_storage()
    template_info = shared_storage.get_template_info(state.record_id)

    if template_info is None:
        logger.warning("[Q/A] No template_info for record_id=%s, using state fallback", state.record_id)
        documents = state.documents
        form_json = state.form_json or []
    else:
        documents = _documents_from_template(template_info)
        form_json = template_info.get("form_json", state.form_json or [])

    filled_form_json = state.filled_form_json or []
    if not filled_form_json:
        return state.model_copy(update={
            "user_response_message": "Veuillez d'abord préremplir le formulaire pour lancer la validation Q/A.",
            "step_completed": "qa",
        })

    manager = QAManager()
    agent = manager.create_agent()

    sub_state = QASubAgentState(
        filled_form_json=filled_form_json,
        form_json=form_json,
        documents=documents,
        record_id=state.record_id,
        remaining_steps=manager.remaining_steps,
        validation_results=dict(state.validation_results or {}),
    )

    result = await agent.ainvoke(sub_state, config={"recursion_limit": manager.remaining_steps})

    if isinstance(result, dict):
        validation_results = result.get("validation_results", {})
    else:
        validation_results = getattr(result, "validation_results", {}) or {}

    qa_validation = validation_results.get("qa_validation", {})
    vr_global = dict(state.validation_results or {})
    vr_global["qa_validation"] = qa_validation

    overall = qa_validation.get("overall_quality")
    user_response_message = "Validation Q/A terminée."
    if overall is not None:
        user_response_message = f"Validation Q/A terminée. Qualité globale : {overall:.2f}."

    return state.model_copy(update={
        "validation_results": vr_global,
        "user_response_message": user_response_message,
        "step_completed": "qa",
    })


__all__ = ["QAManager", "qa_manager_node"]
