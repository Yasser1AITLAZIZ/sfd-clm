"""Pre-filling Manager - sub-agent with do_mapping_tool and expert_validation_tool."""
from __future__ import annotations
import logging

from app.state import MCPAgentState, Document, PreFillingSubAgentState
from app.utils.singletons import get_shared_storage
from .prefilling_manager import PreFillingManager

logger = logging.getLogger(__name__)


def _documents_from_template(template_info: dict) -> list:
    """Build list of Document from template_info['documents_classified'] (dicts)."""
    docs = []
    for d in template_info.get("documents_classified", []):
        if isinstance(d, Document):
            docs.append(d)
        elif isinstance(d, dict):
            from app.state import PageOCR
            pages = []
            for p in d.get("pages", []):
                pages.append(PageOCR(**p) if isinstance(p, dict) else p)
            docs.append(Document(**{**d, "pages": pages}))
        else:
            docs.append(d)
    return docs


async def prefilling_manager_node(state: MCPAgentState) -> MCPAgentState:
    """
    1. Get template_info from Shared Storage.
    2. Build PreFillingSubAgentState from template_info.
    3. Run PreFillingManager ReAct agent.
    4. Update state with filled_form_json, validation_results, user_response_message, step_completed.
    """
    shared_storage = get_shared_storage()
    template_info = shared_storage.get_template_info(state.record_id)

    if template_info is None:
        logger.warning("[Pre-filling] No template_info for record_id=%s, using state fallback", state.record_id)
        documents = state.documents
        form_json = state.form_json or []
    else:
        documents = _documents_from_template(template_info)
        form_json = template_info.get("form_json", state.form_json or [])

    if not form_json:
        return state.model_copy(update={
            "user_response_message": "Aucun formulaire (form_json) disponible pour le préremplissage.",
            "step_completed": "prefill",
        })

    manager = PreFillingManager()
    agent = manager.create_agent()

    sub_state = PreFillingSubAgentState(
        documents=documents,
        form_json=form_json,
        record_id=state.record_id,
        remaining_steps=manager.remaining_steps,
        iteration_count=0,
        filled_form_json=None,
        validation_results={},
    )

    result = await agent.ainvoke(sub_state, config={"recursion_limit": manager.remaining_steps})

    # Extract result (can be dict or PreFillingSubAgentState)
    if isinstance(result, dict):
        filled_form_json = result.get("filled_form_json")
        validation_results = result.get("validation_results", {})
        iteration_count = result.get("iteration_count", 0)
    else:
        filled_form_json = getattr(result, "filled_form_json", None)
        validation_results = getattr(result, "validation_results", {}) or {}
        iteration_count = getattr(result, "iteration_count", 0)

    if iteration_count >= 2:
        logger.warning("[Pre-filling] iteration_count >= 2 after run")

    expert_validation = validation_results.get("expert_validation", {})
    vr_global = dict(state.validation_results or {})
    vr_global["expert_validation"] = expert_validation
    vr_global["iteration_count"] = iteration_count

    user_response_message = "Préremplissage terminé."
    if filled_form_json:
        user_response_message = f"Préremplissage terminé : {len(filled_form_json)} champs remplis."

    return state.model_copy(update={
        "filled_form_json": filled_form_json or state.filled_form_json,
        "validation_results": vr_global,
        "user_response_message": user_response_message,
        "step_completed": "prefill",
    })


__all__ = ["PreFillingManager", "prefilling_manager_node"]
