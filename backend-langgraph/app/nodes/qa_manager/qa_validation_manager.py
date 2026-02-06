"""Q/A Validation Manager - quality and consistency check."""
from __future__ import annotations
import asyncio
import json
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from app.state import Document
from app.config.config_loader import get_config_loader
from app.config.llm_builder import LLMBuilderFactory


QA_VALIDATION_PROMPT = """Tu es un expert en qualité et cohérence globale de formulaires de sinistre.

Tu dois analyser le formulaire prérempli (filled_form_json) et fournir :
- overall_quality : score 0.0 à 1.0
- issues : liste de problèmes (champs manquants, incohérences, etc.)
- suggestions : améliorations suggérées

Format de réponse JSON strict (pas de texte autour) :
{
  "overall_quality": 0.85,
  "issues": [
    {"field": "...", "description": "...", "severity": "warning" | "info" }
  ],
  "suggestions": ["...", "..."]
}
"""


class QAValidationManager:
    """Validates filled form for quality and consistency (config: qa_validation)."""

    def __init__(self) -> None:
        cfg = get_config_loader().get_agent_config("qa_validation")
        provider = cfg.get("provider", "openai")
        model = cfg["model"]
        builder = LLMBuilderFactory.create_builder(provider)
        self.model = builder.build_llm(
            model=model,
            temperature=cfg.get("temperature", 0.1),
        )
        self.timeout_s = float(cfg.get("llm_extraction_timeout", 120))

    async def validate_qa(
        self,
        filled_form_json: List[Dict[str, Any]],
        form_json: List[Dict[str, Any]],
        documents: List[Document],
    ) -> Dict[str, Any]:
        """Returns { "qa_validation": { overall_quality, issues, suggestions } }."""
        payload = {
            "filled_form_json": filled_form_json[:80],
            "form_json": form_json[:50],
        }
        system = SystemMessage(content=QA_VALIDATION_PROMPT)
        human = HumanMessage(content=json.dumps(payload, ensure_ascii=False, indent=2))

        try:
            resp = await asyncio.wait_for(
                self.model.ainvoke([system, human]),
                timeout=self.timeout_s,
            )
        except asyncio.TimeoutError:
            return {
                "qa_validation": {
                    "overall_quality": 0.5,
                    "issues": [],
                    "suggestions": [],
                    "error": "validation_timeout",
                }
            }

        content = resp.content
        if isinstance(content, str):
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                data = {"overall_quality": 0.5, "issues": [], "suggestions": []}
        else:
            data = content

        return {"qa_validation": data}
