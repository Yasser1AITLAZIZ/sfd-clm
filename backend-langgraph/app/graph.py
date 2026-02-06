"""LangGraph workflow definition"""
from __future__ import annotations
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

from app.state import MCPAgentState
from app.orchestrator.supervisor import supervisor_wrapper
from app.utils.handoff_tool import route_after_supervisor, route_after_ocr, route_after_prefilling, route_after_qa
from app.utils.observability import setup_phoenix_observability
from app.nodes.ocr_synthesizer import ocr_synthesizer_node
from app.nodes.prefilling_manager import prefilling_manager_node
from app.nodes.qa_manager import qa_manager_node

load_dotenv(override=True)

# Setup Phoenix observability at module level (like in reference project)
setup_phoenix_observability(project_name="sfd-clm-langgraph")


def create_async_graph():
    """Build the LangGraph workflow for the MCP Agent pipeline.

    Nodes:
    - supervisor: orchestrates routing by intention (ReAct agent)
    - ocr_synthesizer: OCR + classification + Shared Storage
    - prefilling_manager, qa_manager: added in Phase 5/6

    Returns the uncompiled `StateGraph` configured with `MCPAgentState`.
    """
    workflow = (
        StateGraph(MCPAgentState)
        .add_node("supervisor", supervisor_wrapper)
        .add_node("ocr_synthesizer", ocr_synthesizer_node)
        .add_node("prefilling_manager", prefilling_manager_node)
        .add_node("qa_manager", qa_manager_node)
        .add_edge(START, "supervisor")
        .add_conditional_edges(
            "supervisor",
            route_after_supervisor,
            {
                "ocr_synthesizer": "ocr_synthesizer",
                "prefilling_manager": "prefilling_manager",
                "qa_manager": "qa_manager",
                "__end__": END,
            }
        )
        .add_conditional_edges(
            "ocr_synthesizer",
            route_after_ocr,
            {
                "prefilling_manager": "prefilling_manager",
                "__end__": END,
            }
        )
        .add_conditional_edges(
            "prefilling_manager",
            route_after_prefilling,
            {
                "qa_manager": "qa_manager",
                "__end__": END,
            }
        )
        .add_conditional_edges(
            "qa_manager",
            route_after_qa,
            {"__end__": END}
        )
    )
    return workflow

