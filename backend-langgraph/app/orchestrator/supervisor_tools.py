"""Supervisor intention tools - set next_step and user_intent for routing."""
from __future__ import annotations
from typing import Annotated, Any
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from app.state import MCPAgentState


def _state_attr(state: Any, key: str, default: Any = None):
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


@tool(description="Déclencher le traitement des documents (OCR + classification). À utiliser quand l'utilisateur demande de traiter, clôturer, rasteriser les documents ou faire l'OCR.")
async def process_documents_tool(
    state: Annotated[Any, InjectedState],
) -> Command:
    """Set next_step=ocr_synthesizer and user_intent=process_documents."""
    return Command(update={
        "next_step": "ocr_synthesizer",
        "user_intent": "process_documents",
    })


@tool(description="Déclencher le préremplissage du formulaire. À utiliser quand l'utilisateur demande de préremplir, pre-fill ou remplir le formulaire.")
async def prefill_form_tool(
    state: Annotated[Any, InjectedState],
) -> Command:
    """Set next_step=prefilling_manager and user_intent=prefill_form."""
    return Command(update={
        "next_step": "prefilling_manager",
        "user_intent": "prefill_form",
    })


@tool(description="Déclencher la session Q&A / validation. À utiliser quand l'utilisateur pose des questions ou demande une vérification.")
async def validate_qa_tool(
    state: Annotated[Any, InjectedState],
) -> Command:
    """Set next_step=qa_manager and user_intent=qa_session."""
    return Command(update={
        "next_step": "qa_manager",
        "user_intent": "qa_session",
    })


def get_supervisor_intention_tools():
    """Return the list of intention tools for the Supervisor."""
    return [process_documents_tool, prefill_form_tool, validate_qa_tool]
