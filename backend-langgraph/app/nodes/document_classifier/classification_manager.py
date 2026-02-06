"""Document classifier - classifies each page by type (page_type, confidence, evidence)."""
from __future__ import annotations
import asyncio
import json
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from app.state import Document, PageOCR
from app.config.config_loader import get_config_loader
from app.config.llm_builder import LLMBuilderFactory


CLASSIFICATION_PROMPT_SYSTEM = """Tu es un expert en classification de documents de sinistres auto.

Tu dois classifier CHAQUE page d'un document selon un type fermé. Ne pas inventer de types.

Types autorisés (exactement) :
- constat_amiable : constat amiable d'accident
- permis_conduire : permis de conduire
- carte_grise : carte grise / certificat d'immatriculation
- piece_identite : pièce d'identité (CNI, passeport)
- facture : facture, devis
- photo_degat : photo de dégât / véhicule
- attestation : attestation d'assurance, courrier
- autre : tout autre document non listé

Pour chaque page, fournis :
- page_type : un des types ci-dessus
- page_type_confidence : nombre entre 0 et 1
- page_type_evidence : courte phrase justifiant le type (extrait du texte ou description)

Format de réponse JSON strict (pas de texte autour) :
{
  "pages": [
    {
      "page_number": 1,
      "page_type": "constat_amiable",
      "page_type_confidence": 0.95,
      "page_type_evidence": "Formulaire constat amiable avec champs lieu, date, véhicules."
    }
  ]
}
"""


class ClassificationManager:
    """Classifies document pages by type using LLM (config: document_classifier)."""

    def __init__(self) -> None:
        cfg = get_config_loader().get_agent_config("document_classifier")
        provider = cfg.get("provider", "openai")
        model = cfg["model"]
        builder = LLMBuilderFactory.create_builder(provider)
        self.model = builder.build_llm(
            model=model,
            temperature=cfg.get("temperature", 0.0),
        )
        self.timeout_s = float(cfg.get("llm_extraction_timeout", 60))

    async def classify_documents_by_pages(
        self, documents: List[Document]
    ) -> List[Document]:
        """
        Classify each page of the given documents. Returns new list of documents
        with page_type, page_type_confidence, page_type_evidence set on each page.
        """
        if not documents:
            return []

        # Build flat list of (doc_idx, page_idx, page) with ocr_text
        items: List[tuple[int, int, PageOCR]] = []
        for di, doc in enumerate(documents):
            for pi, page in enumerate(doc.pages):
                if page.ocr_text and page.processed:
                    items.append((di, pi, page))

        if not items:
            return [doc.model_copy() for doc in documents]

        # Single LLM call with all pages (truncate if too many)
        pages_for_prompt = []
        for di, pi, page in items[:50]:  # limit 50 pages
            pages_for_prompt.append({
                "page_number": page.page_number,
                "ocr_text": (page.ocr_text or "")[:2000],
            })

        system = SystemMessage(content=CLASSIFICATION_PROMPT_SYSTEM)
        human = HumanMessage(content=json.dumps({"pages": pages_for_prompt}, ensure_ascii=False, indent=2))

        try:
            resp = await asyncio.wait_for(
                self.model.ainvoke([system, human]),
                timeout=self.timeout_s,
            )
        except asyncio.TimeoutError:
            print("⚠️ [Classification] Timeout, returning documents without page_type")
            return [doc.model_copy() for doc in documents]

        content = resp.content
        if isinstance(content, str):
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
            data = json.loads(content)
        else:
            data = content

        # Map page_number -> classification
        class_by_page: Dict[int, Dict[str, Any]] = {}
        for p in data.get("pages", []):
            num = p.get("page_number")
            if num is not None:
                class_by_page[num] = {
                    "page_type": p.get("page_type", "autre"),
                    "page_type_confidence": float(p.get("page_type_confidence", 0.5)),
                    "page_type_evidence": p.get("page_type_evidence") or "",
                }

        # Apply to documents
        result = []
        for doc in documents:
            new_pages = []
            for page in doc.pages:
                cls = class_by_page.get(page.page_number, {})
                new_pages.append(page.model_copy(update={
                    "page_type": cls.get("page_type"),
                    "page_type_confidence": cls.get("page_type_confidence", 0.0),
                    "page_type_evidence": cls.get("page_type_evidence"),
                }))
            result.append(doc.model_copy(update={"pages": new_pages}))

        return result
