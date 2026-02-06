"""Handoff tool for routing after supervisor (intention + state)."""
from __future__ import annotations
from typing import Any, Literal

from app.state import MCPAgentState
from app.config.config_loader import get_config_loader
from app.utils.singletons import get_shared_storage


def route_after_supervisor(state: MCPAgentState | dict[str, Any]) -> Literal["ocr_synthesizer", "prefilling_manager", "qa_manager", "__end__"]:
    """
    Route after supervisor: intention + state.
    Reads next_step (set by Supervisor tools) and optionally state (Shared Storage, filled_form_json).
    """
    try:
        config = get_config_loader().get_config()
    except Exception:
        config = {}
    use_intent_routing = config.get("use_intent_routing", True)

    if not use_intent_routing:
        return "__end__"

    next_step = state.get("next_step") if isinstance(state, dict) else getattr(state, "next_step", None)
    if next_step in ("ocr_synthesizer", "prefilling_manager", "qa_manager"):
        return next_step

    # Fallback: infer from user_intent + state when next_step not set
    user_intent = state.get("user_intent") if isinstance(state, dict) else getattr(state, "user_intent", None)
    record_id = state.get("record_id") or "" if isinstance(state, dict) else (getattr(state, "record_id", None) or "")
    has_template = get_shared_storage().has_template_info(record_id) if record_id else False
    filled = state.get("filled_form_json") if isinstance(state, dict) else getattr(state, "filled_form_json", None)
    has_filled = bool(filled and len(filled) > 0)

    if user_intent == "process_documents":
        return "ocr_synthesizer"
    if user_intent == "prefill_form":
        if not has_template and not has_filled:
            return "ocr_synthesizer"  # Run OCR first then prefill
        return "prefilling_manager"
    if user_intent == "qa_session" and has_filled:
        return "qa_manager"
    if user_intent == "full_pipeline":
        if not has_template:
            return "ocr_synthesizer"
        if not has_filled:
            return "prefilling_manager"
        return "qa_manager"

    return "__end__"


def route_after_ocr(state: MCPAgentState | dict[str, Any]) -> Literal["prefilling_manager", "supervisor", "__end__"]:
    """
    After OCR Synthesizer: if intention = process_documents only → END;
    else → prefilling_manager (to continue) or supervisor.
    """
    user_intent = state.get("user_intent") if isinstance(state, dict) else getattr(state, "user_intent", None)
    if user_intent == "process_documents":
        return "__end__"
    return "prefilling_manager"


def route_after_prefilling(state: MCPAgentState | dict[str, Any]) -> Literal["qa_manager", "supervisor", "__end__"]:
    """
    After Pre-filling Manager: en général END ; ou qa_manager si intention = full_pipeline.
    """
    user_intent = state.get("user_intent") if isinstance(state, dict) else getattr(state, "user_intent", None)
    if user_intent == "full_pipeline":
        return "qa_manager"
    return "__end__"


def route_after_qa(state: MCPAgentState | dict[str, Any]) -> Literal["supervisor", "__end__"]:
    """After Q/A Manager: generally END."""
    return "__end__"

