"""Q/A Manager - ReAct sub-agent with qa_validation_tool."""
from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from app.state import QASubAgentState
from app.config.config_loader import get_config_loader
from app.config.llm_builder import LLMBuilderFactory
from .qa_validation_tool import qa_validation_tool


QA_MANAGER_PROMPT = """Tu es l'agent responsable de la qualité finale et de la validation globale du formulaire de sinistre.

## Tool disponible

- `qa_validation_tool` : Valide la qualité et la cohérence globale du formulaire prérempli.

## Processus

1. Appelle `qa_validation_tool` pour analyser le filled_form_json.
2. Examine le rapport (overall_quality, issues, suggestions).
3. Retourne une synthèse pour l'utilisateur si nécessaire.
"""


class QAManager:
    """ReAct sub-agent for Q/A with qa_validation_tool."""

    def __init__(self) -> None:
        cfg = get_config_loader().get_agent_config("qa_manager")
        provider = cfg.get("provider", "openai")
        model = cfg["model"]
        builder = LLMBuilderFactory.create_builder(provider)
        temperature = cfg.get("temperature", 0.1)
        if cfg.get("reasoning_effort"):
            self.model = builder.build_llm(model=model, reasoning_effort=cfg.get("reasoning_effort", "medium"))
        else:
            self.model = builder.build_llm(model=model, temperature=temperature)
        self.remaining_steps = int(cfg.get("remaining_steps", 10))

    def create_agent(self):
        """Create the ReAct agent with qa_validation_tool."""
        return create_react_agent(
            self.model,
            tools=[qa_validation_tool],
            state_schema=QASubAgentState,
            prompt=QA_MANAGER_PROMPT,
        )
