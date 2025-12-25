"""State operations utilities"""
from typing import Dict, Any
from app.state import MCPAgentState


def copy_update(state: MCPAgentState, updates: Dict[str, Any]) -> MCPAgentState:
    """Create a copy of state with updates"""
    return state.model_copy(update=updates)


def add_ai(state: MCPAgentState, message: str) -> MCPAgentState:
    """Add an AI message to the state"""
    from langchain_core.messages import AIMessage
    from langgraph.graph.message import add_messages
    
    new_message = AIMessage(content=message)
    updated_messages = add_messages([], [new_message])
    
    return state.model_copy(update={
        "messages": list(state.messages) + updated_messages
    })

