"""Handoff tool for routing after supervisor"""
from typing import Literal
from app.state import MCPAgentState


def route_after_supervisor(state: MCPAgentState) -> Literal["__end__"]:
    """
    Route after supervisor execution.
    
    For now, always ends the workflow after supervisor completes.
    In the future, we could add conditional routing based on state.
    """
    # Check if we should continue or end
    # For now, always end after supervisor completes
    if state.remaining_steps <= 0:
        return "__end__"
    
    # If extraction is complete, end
    if state.extracted_data and len(state.extracted_data) > 0:
        return "__end__"
    
    # Otherwise, end (supervisor handles everything via tools)
    return "__end__"

