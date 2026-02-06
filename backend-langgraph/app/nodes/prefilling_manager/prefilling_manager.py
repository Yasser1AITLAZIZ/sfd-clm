"""Pre-filling Manager - ReAct sub-agent with do_mapping_tool and expert_validation_tool."""
from __future__ import annotations
from typing import Any, Dict

from langgraph.prebuilt import create_react_agent

from app.state import PreFillingSubAgentState
from app.config.config_loader import get_config_loader
from app.config.llm_builder import LLMBuilderFactory
from .do_mapping_tool import do_mapping_tool
from app.nodes.validation_expert import expert_validation_tool


PREFILLING_PROMPT = """Tu es l'agent responsable du préremplissage du formulaire de déclaration de sinistre.

## Tools disponibles

- `do_mapping_tool` : Effectue le mapping des champs depuis l'OCR (première passe ou correction avec feedback).
- `expert_validation_tool` : Analyse la cohérence du préremplissage et rapporte les problèmes (duplications, valeurs illogiques, dates impossibles).

## Processus

1. Appelle `do_mapping_tool` pour obtenir un premier filled_form_json.
2. Appelle `expert_validation_tool` pour analyser la cohérence et obtenir un rapport.
3. Si le rapport contient des problèmes critiques (severity "critical") et suggested_correction pour certains champs, rappelle `do_mapping_tool` une seule fois pour appliquer les corrections.
4. Si seulement des valeurs illogiques sont signalées (ex: date 2015), ne pas corriger automatiquement ; considérer le formulaire final.
5. Si le rapport contient seulement des warnings, considérer le formulaire acceptable.
6. Retourne le formulaire final une fois la validation satisfaisante ou les corrections critiques appliquées.

## Règles anti-boucle CRITIQUES

- NE JAMAIS appeler do_mapping_tool et expert_validation_tool en boucle infinie.
- Maximum 2 itérations : première passe mapping → validation → correction (si critique) → validation finale.
- Si remaining_steps <= 0, arrêter immédiatement et retourner le formulaire actuel.
- Si validation_results.expert_validation.iteration_count >= 2, arrêter et retourner le formulaire actuel.
- Ne pas rappeler expert_validation_tool si elle a déjà été appelée 2 fois.
"""


class PreFillingManager:
    """ReAct sub-agent for pre-filling with do_mapping_tool and expert_validation_tool."""

    def __init__(self) -> None:
        cfg = get_config_loader().get_agent_config("prefilling_manager")
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
        """Create the ReAct agent with do_mapping_tool and expert_validation_tool."""
        return create_react_agent(
            self.model,
            tools=[do_mapping_tool, expert_validation_tool],
            state_schema=PreFillingSubAgentState,
            prompt=PREFILLING_PROMPT,
        )
