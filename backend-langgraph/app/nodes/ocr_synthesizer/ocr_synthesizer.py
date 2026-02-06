"""OCR Synthesizer - OCR + classification and write to Shared Storage."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.state import MCPAgentState, Document
from app.config.config_loader import get_config_loader
from app.nodes.ocr_mapping_tool.ocr_manager import OCRManager
from app.nodes.document_classifier import ClassificationManager
from app.utils.singletons import get_shared_storage
from app.config.llm_builder import LLMBuilderFactory


class OCRSynthesizer:
    """
    OCR + Classification and write to Shared Storage.
    Uses OCRManager and ClassificationManager; writes template_info by record_id.
    """

    def __init__(self) -> None:
        get_config_loader().get_agent_config("ocr_synthesizer")
        llm_builder = LLMBuilderFactory.create_builder("openai")
        self._ocr_manager = OCRManager(llm_builder)
        self._classifier = ClassificationManager()

    async def synthesize(self, state: MCPAgentState) -> MCPAgentState:
        """
        1. OCR via OCRManager.process(state)
        2. Classify pages via ClassificationManager
        3. Write template_info to Shared Storage
        4. Set user_response_message and step_completed
        """
        # 1. OCR
        state = await self._ocr_manager.process(state)

        # 2. Classify (may fail; continue without classification)
        try:
            documents_classified = await self._classifier.classify_documents_by_pages(state.documents)
            state = state.model_copy(update={"documents": documents_classified})
        except Exception as e:
            print(f"⚠️ [OCR Synthesizer] Classification failed: {e}, continuing without page_type")

        # 3. Build classification summary and write Shared Storage
        classification_summary: Dict[str, Any] = {}
        for doc in state.documents:
            for page in doc.pages:
                if page.page_type:
                    classification_summary[page.page_type] = classification_summary.get(page.page_type, 0) + 1

        now = datetime.now(timezone.utc).isoformat()
        template_info: Dict[str, Any] = {
            "form_json": state.form_json,
            "documents_classified": [doc.model_dump() for doc in state.documents],
            "ocr_consolidated": state.ocr_text or "",
            "classification_summary": classification_summary,
            "last_updated": now,
            "created_at": now,
        }
        get_shared_storage().set_template_info(state.record_id, template_info)

        # 4. User response message and step_completed
        num_pages = sum(len(d.pages) for d in state.documents)
        num_classified = sum(1 for d in state.documents for p in d.pages if p.page_type)
        user_response_message = (
            f"Documents traités : {num_pages} page(s), {num_classified} classifiée(s). "
            f"Résumé types : {classification_summary or '—'}."
        )
        user_intent = getattr(state, "user_intent", None) or (state.get("user_intent") if isinstance(state, dict) else None)
        step_completed = "ocr_only" if user_intent == "process_documents" else "ocr_only"

        state = state.model_copy(update={
            "user_response_message": user_response_message,
            "step_completed": step_completed,
        })
        return state
