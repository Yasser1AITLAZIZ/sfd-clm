"""OCR Synthesizer node - OCR + classification + Shared Storage."""
from __future__ import annotations

from app.state import MCPAgentState
from .ocr_synthesizer import OCRSynthesizer

_synthesizer: OCRSynthesizer | None = None


def _get_synthesizer() -> OCRSynthesizer:
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = OCRSynthesizer()
    return _synthesizer


async def ocr_synthesizer_node(state: MCPAgentState) -> MCPAgentState:
    """Node wrapper: run OCR Synthesizer and return updated state."""
    return await _get_synthesizer().synthesize(state)

__all__ = ["OCRSynthesizer", "ocr_synthesizer_node"]
