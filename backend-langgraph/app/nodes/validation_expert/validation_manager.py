"""Expert Validation Manager - analyse et rapport (ne modifie pas filled_form_json)."""
from __future__ import annotations
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.state import Document
from app.config.config_loader import get_config_loader
from app.config.llm_builder import LLMBuilderFactory


EXPERT_VALIDATION_PROMPT_SYSTEM = """Tu es un expert en déclaration de sinistres qui analyse la sortie du Pre-filling Manager Agent.

Objectif : Détecter les incohérences dans le préremplissage et rapporter ces problèmes à l'agent. Tu ne modifies JAMAIS le formulaire directement.

Règles métier :
- Duplication assuré/conducteur : Si même nom/prénom entre champs assuré et conducteur sans preuve dans l'OCR que c'est la même personne → alerte severity "critical" ou "warning".
- Valeurs illogiques : Date de sinistre impossible (trop ancienne, ex. > 2 ans par rapport à current_date, ou future) → severity "critical", issue_type "illogical_date". Exemple : "Date de sinistre 2015 alors qu'on est en 2026 - impossible de traiter un sinistre 11 ans après".
- Autres incohérences de dates : date de naissance > date de sinistre, permis délivré après sinistre.
- Champs requis vides alors que l'OCR contient l'information.
- Formats : immatriculation invalide, montants négatifs.

Entrée : filled_form_json, extraits OCR par page, form_json (schéma), current_date (ISO "YYYY-MM-DD").

Sortie JSON strict (pas de texte autour) :
{
  "overall_quality": 0.0 à 1.0,
  "field_feedback": [
    {
      "field_index": 0,
      "field_label": "...",
      "field_apiName": "...",
      "current_value": "...",
      "issues": ["assuré_conducteur_confusion", "illogical_date", ...],
      "severity": "critical" | "warning" | "info",
      "suggested_correction": null ou "valeur suggérée",
      "confidence_should_be": null ou 0.0-1.0,
      "justification": "Explication du problème",
      "ocr_evidence": null ou "extrait OCR"
    }
  ],
  "cross_field_consistency": [
    {
      "issue_type": "assuré_conducteur_same_name_without_justification" | "illogical_date_range" | "...",
      "affected_fields": [0, 1],
      "description": "...",
      "suggested_fix": "..."
    }
  ],
  "illogical_values": [
    {
      "field_index": 0,
      "field_label": "...",
      "value": "...",
      "reason": "Date de sinistre 2015 alors qu'on est en 2026 - impossible de traiter un sinistre 11 ans après",
      "severity": "critical"
    }
  ]
}
"""


class ExpertValidationManager:
    """Analyse filled_form_json and reports issues (never modifies the form)."""

    def __init__(self) -> None:
        cfg = get_config_loader().get_agent_config("expert_validation")
        provider = cfg.get("provider", "openai")
        model = cfg["model"]
        builder = LLMBuilderFactory.create_builder(provider)
        self.model = builder.build_llm(
            model=model,
            temperature=cfg.get("temperature", 0.1),
        )
        self.timeout_s = float(cfg.get("llm_extraction_timeout", 120))

    async def validate_prefill(
        self,
        filled_form_json: Optional[List[Dict[str, Any]]],
        documents: List[Document],
        form_json: List[Dict[str, Any]],
        record_id: str,
        current_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Returns { "expert_validation": { overall_quality, field_feedback, cross_field_consistency, illogical_values } }.
        Does not modify filled_form_json.
        """
        if current_date is None:
            current_date = datetime.now(timezone.utc).isoformat()[:10]

        # Build OCR summary per page for prompt
        ocr_by_page = []
        for doc in documents:
            for page in doc.pages:
                ocr_by_page.append({
                    "page_number": page.page_number,
                    "ocr_text": (page.ocr_text or "")[:1500],
                    "page_type": page.page_type,
                })

        payload = {
            "filled_form_json": filled_form_json or [],
            "ocr_by_page": ocr_by_page,
            "form_json": form_json[:100],
            "current_date": current_date,
        }
        system = SystemMessage(content=EXPERT_VALIDATION_PROMPT_SYSTEM)
        human = HumanMessage(content=json.dumps(payload, ensure_ascii=False, indent=2))

        try:
            resp = await asyncio.wait_for(
                self.model.ainvoke([system, human]),
                timeout=self.timeout_s,
            )
        except asyncio.TimeoutError:
            return {
                "expert_validation": {
                    "overall_quality": 0.5,
                    "field_feedback": [],
                    "cross_field_consistency": [],
                    "illogical_values": [],
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
                return {
                    "expert_validation": {
                        "overall_quality": 0.5,
                        "field_feedback": [],
                        "cross_field_consistency": [],
                        "illogical_values": [],
                        "error": "invalid_json",
                    }
                }
        else:
            data = content

        return {"expert_validation": data}
