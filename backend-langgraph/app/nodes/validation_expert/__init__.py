"""Expert Validation - analyse + rapport (ne modifie pas filled_form_json)."""
from __future__ import annotations
from typing import Annotated, Any

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from app.state import PreFillingSubAgentState
from .validation_manager import ExpertValidationManager

_manager: ExpertValidationManager | None = None


def _get_manager() -> ExpertValidationManager:
    global _manager
    if _manager is None:
        _manager = ExpertValidationManager()
    return _manager


@tool(description="Analyse la cohérence du préremplissage et rapporte les problèmes (duplications, valeurs illogiques, dates impossibles). Ne modifie pas le formulaire.")
async def expert_validation_tool(
    state: Annotated[Any, InjectedState],
) -> Command:
    """
    Expert validation: analyse filled_form_json and writes report to validation_results.expert_validation.
    Never modifies filled_form_json. Anti-loop: max 2 calls (iteration_count >= 2 → error).
    """
    if not isinstance(state, PreFillingSubAgentState):
        state = PreFillingSubAgentState(**state) if isinstance(state, dict) else state

    iteration_count = getattr(state, "iteration_count", 0) or (state.get("iteration_count", 0) if isinstance(state, dict) else 0)
    if iteration_count >= 2:
        return Command(update={
            "validation_results": {
                **getattr(state, "validation_results", {}) or (state.get("validation_results", {}) if isinstance(state, dict) else {}),
                "expert_validation": {"error": "expert_validation_tool called too many times"},
                "iteration_count": iteration_count + 1,
            },
            "errors": list(getattr(state, "errors", []) or []) + ["expert_validation_tool called too many times"],
        })

    from datetime import datetime, timezone
    current_date = datetime.now(timezone.utc).isoformat()[:10]

    filled = getattr(state, "filled_form_json", None) or (state.get("filled_form_json") if isinstance(state, dict) else None)
    documents = getattr(state, "documents", []) or (state.get("documents", []) if isinstance(state, dict) else [])
    form_json = getattr(state, "form_json", []) or (state.get("form_json", []) if isinstance(state, dict) else [])
    record_id = getattr(state, "record_id", "") or (state.get("record_id", "") if isinstance(state, dict) else "")

    # Deserialize documents if they are dicts
    from app.state import Document
    docs = []
    for d in documents:
        if isinstance(d, Document):
            docs.append(d)
        else:
            docs.append(Document(**d) if isinstance(d, dict) else d)

    result = await _get_manager().validate_prefill(
        filled_form_json=filled,
        documents=docs,
        form_json=form_json,
        record_id=record_id,
        current_date=current_date,
    )

    validation_results = dict(getattr(state, "validation_results", {}) or (state.get("validation_results", {}) if isinstance(state, dict) else {}))
    validation_results["expert_validation"] = result.get("expert_validation", {})
    validation_results["iteration_count"] = iteration_count + 1

    return Command(update={"validation_results": validation_results})


__all__ = ["ExpertValidationManager", "expert_validation_tool"]
