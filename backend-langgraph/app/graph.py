"""LangGraph workflow definition"""
from __future__ import annotations
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

from app.state import MCPAgentState
from app.orchestrator.supervisor import supervisor_wrapper
from app.utils.handoff_tool import route_after_supervisor
from app.utils.observability import setup_phoenix_observability
from app.utils.trace_node import trace_node

load_dotenv(override=True)

# Setup Phoenix observability at module level (like in reference project)
setup_phoenix_observability(project_name="sfd-clm-langgraph")


def create_async_graph():
    """Build the LangGraph workflow for the MCP Agent pipeline.

    Nodes:
    - supervisor: orchestrates routing and extraction using ReAct agent
    - ocr_mapping_tool: combined OCR and field mapping (called via supervisor tool)

    Returns the uncompiled `StateGraph` configured with `MCPAgentState`.
    """
    workflow = (
        StateGraph(MCPAgentState)
        .add_node("supervisor", trace_node("supervisor")(supervisor_wrapper))
        .add_edge(START, "supervisor")
        .add_conditional_edges(
            "supervisor",
            route_after_supervisor,
            {
                "__end__": END,
            }
        )
    )
    return workflow

