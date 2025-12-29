"""OCR Manager for asynchronous document processing"""
from __future__ import annotations
import asyncio
import json
import time
from hashlib import sha256
from typing import Tuple, List
from langchain_core.messages import HumanMessage, SystemMessage

from app.state import MCPAgentState, PageOCR, TextBlock, Document
from app.config.config_loader import get_config_loader
from app.config.llm_builder import LLMBuilderFactory
from app.utils.memory_manager import MemoryManager


_PROMPT_SYSTEM = """Tu es un expert en OCR (Optical Character Recognition).
Ton rôle est d'analyser des images de documents et d'extraire tout le texte visible avec précision.

Instructions:
1. Décris TOUS les éléments visibles dans l'image (texte, tableaux, formulaires, etc.)
2. Extrais le texte de manière structurée et organisée
3. Identifie les blocs de texte avec leurs positions (bounding boxes)
4. Évalue la qualité de l'OCR (score de 0 à 1)
5. Liste les problèmes éventuels (flou, texte manuscrit, etc.)

Format de réponse JSON:
{
  "text": "texte extrait complet",
  "quality_score_ocerization": 0.95,
  "quality_justification": "Texte clair et lisible",
  "issues": [],
  "text_blocks": [
    {
      "text": "contenu du bloc",
      "bbox": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.1},
      "block_type": "paragraph",
      "confidence": 0.95
    }
  ]
}
"""


class OCRManager:
    """OCR Manager for processing documents asynchronously"""
    
    def __init__(self, llm_builder):
        """Initialize OCR Manager with LLM builder"""
        cfg = get_config_loader().get_agent_config("ocr")
        self.enabled = cfg.get("enabled", True)
        
        # Get provider and model from config
        provider = cfg.get("provider", "openai")
        model = cfg["model"]
        
        # Create LLM builder and build model
        builder = LLMBuilderFactory.create_builder(provider)
        self.model = builder.build_llm(
            model=model,
            temperature=cfg.get("temperature", 0.0),
        )
        self.concurrency = int(cfg.get("concurrency_limit", 4))
        # Use per-page timeout if available, otherwise fallback to default
        self.timeout_s = float(cfg.get("ocr_timeout_per_page", 60))
        self.memory_manager = MemoryManager()

    def _generate_block_id(self, text: str, bbox: dict) -> str:
        """Generate a unique block ID from text content and position."""
        position_str = f"{bbox.get('x', 0):.4f}_{bbox.get('y', 0):.4f}_{bbox.get('width', 0):.4f}_{bbox.get('height', 0):.4f}"
        content = f"{text}|{position_str}"
        return sha256(content.encode('utf-8')).hexdigest()[:16]

    def _parse_text_blocks(self, data: dict) -> List[TextBlock]:
        """Parse text_blocks from LLM response and generate block IDs."""
        text_blocks_data = data.get("text_blocks", [])
        if not isinstance(text_blocks_data, list):
            return []
        
        text_blocks = []
        for block_data in text_blocks_data:
            try:
                text = block_data.get("text", "")
                bbox = block_data.get("bbox", {})
                block_type = block_data.get("block_type", "paragraph")
                confidence = float(block_data.get("confidence", 0.0))
                
                # Validate bbox structure
                if not isinstance(bbox, dict):
                    print(f"⚠️ [OCR] Invalid bbox format, skipping block: {text[:50]}...")
                    continue
                
                # Ensure bbox has required fields with defaults
                bbox_normalized = {
                    "x": float(bbox.get("x", 0.0)),
                    "y": float(bbox.get("y", 0.0)),
                    "width": float(bbox.get("width", 0.0)),
                    "height": float(bbox.get("height", 0.0))
                }
                
                # Validate bbox coordinates are in [0,1]
                if not all(0.0 <= v <= 1.0 for v in bbox_normalized.values()):
                    print(f"⚠️ [OCR] Bbox coordinates out of range [0,1], skipping block: {text[:50]}...")
                    continue
                
                # Generate block_id
                block_id = self._generate_block_id(text, bbox_normalized)
                
                text_blocks.append(TextBlock(
                    text=text,
                    bbox=bbox_normalized,
                    block_type=block_type,
                    confidence=confidence,
                    block_id=block_id
                ))
            except Exception as e:
                print(f"⚠️ [OCR] Error parsing text block: {e}, skipping")
                continue
        
        return text_blocks

    async def _ocr_page(self, page: PageOCR) -> Tuple[str, float, str, list, List[TextBlock]]:
        """Process a single page and return OCR results."""
        print(f"🔍 [OCR] Starting OCR for page: mime={page.image_mime}, b64_len={len(page.image_b64)}")
        
        system = SystemMessage(content=_PROMPT_SYSTEM)
        
        human = HumanMessage(content=[
            {"type": "text", "text": "Analyse cette image complètement : décrit tous les composants de l'image fournit, en toute précision. Règle d'or : Tu doit faire une description/extraction détaillée, pointue, complète, exhaustive, même si l'image est peu lisible ou contient un texte manuscrit."},
            {"type": "image_url", "image_url": {"url": f"data:{page.image_mime};base64,{page.image_b64}", "detail": "high"}}
        ])
        
        print(f"📤 [OCR] Sending request to LLM")
        print(f"🖼️ [OCR] Image size: {len(page.image_b64)} chars base64")
        print(f"📋 [OCR] Image MIME: {page.image_mime}")
        
        try:
            start_time = time.time()
            resp = await asyncio.wait_for(self.model.ainvoke([system, human]), timeout=self.timeout_s)
            request_time = time.time() - start_time
            print(f"📥 [OCR] Received response in {request_time:.2f}s")
            
            content = resp.content
            if isinstance(content, str):
                print(f"📝 [OCR] Parsing JSON response: {content[:200]}...")
                data = json.loads(content)
            else:
                data = content
            
            text = data.get("text", "")
            if text == "":
                print(f"⚠️ [OCR] Warning: empty text received")
            quality = float(data.get("quality_score_ocerization", 0.0))
            justification = data.get("quality_justification", "")
            issues = list(data.get("issues", []))
            
            # Parse text_blocks from response
            text_blocks = self._parse_text_blocks(data)
            print(f"📦 [OCR] Parsed {len(text_blocks)} text blocks")
            
            # Combine OCR text
            final_text = text if text and text.strip() and text != "Aucun texte visible" else "[Aucun texte visible]"
            
            print(f"✅ [OCR] Final result: {len(final_text)} chars, quality={quality}, issues={len(issues)}, blocks={len(text_blocks)}")
            return final_text, quality, justification, issues, text_blocks
            
        except asyncio.TimeoutError:
            print(f"⏰ [OCR] Timeout after {self.timeout_s}s")
            return "", 0.0, '', [f"ocr_timeout:{self.timeout_s}s"], []
        except json.JSONDecodeError as e:
            print(f"❌ [OCR] JSON decode error: {e}")
            print(f"📝 [OCR] Raw response: {content}")
            return "", 0.0, '', [f"ocr_json_error:{e}"], []
        except Exception as e:
            print(f"❌ [OCR] General error: {e}")
            return "", 0.0, '', [f"ocr_error:{e}"], []

    async def process(self, state: MCPAgentState) -> MCPAgentState:
        """Process all documents in the state asynchronously."""
        print("🔍 [OCR Manager] Starting OCR processing...")
        self.memory_manager.log_memory_usage("before OCR processing")
        sem = asyncio.Semaphore(self.concurrency)
        tasks = []
        
        # Create a copy of documents to avoid concurrency issues
        documents = [doc.model_copy() for doc in state.documents]
        print(f"📊 [OCR Manager] Found {len(documents)} documents")

        async def run_one(doc_idx: int, page_idx: int):
            async with sem:
                page = documents[doc_idx].pages[page_idx]
                doc = documents[doc_idx]
                print(f"🔄 [OCR Manager] Processing doc {doc_idx}, page {page_idx}")
                try:
                    text, qs, qj, issues, text_blocks = await self._ocr_page(page)
                    print(f"✅ [OCR Manager] OCR success: {len(text)} chars, quality_ocr={qs}, blocks={len(text_blocks)}")
                    
                    # Update page with OCR results
                    documents[doc_idx].pages[page_idx] = page.model_copy(update={
                        "ocr_text": text,
                        "quality_score_ocerization": qs,
                        "quality_justification": qj,
                        "issues": issues,
                        "text_blocks": text_blocks,
                        "processed": True
                    })
                    
                    # Cleanup memory after processing each page
                    self.memory_manager.cleanup_memory()
                except Exception as e:
                    print(f"❌ [OCR Manager] OCR error: {e}")
                    documents[doc_idx].pages[page_idx] = page.model_copy(update={
                        "ocr_text": "",
                        "quality_score_ocerization": 0.0,
                        "quality_justification": "",
                        "issues": [f"ocr_error: {e}"],
                        "text_blocks": [],
                        "processed": True
                    })

        # Create tasks for all unprocessed pages
        for di, d in enumerate(documents):
            for pi, p in enumerate(d.pages):
                if not p.processed:
                    print(f"📋 [OCR Manager] Adding task for doc {di}, page {pi}")
                    tasks.append(asyncio.create_task(run_one(di, pi)))
                else:
                    print(f"⏭️ [OCR Manager] Skipping doc {di}, page {pi} (already processed)")

        print(f"🚀 [OCR Manager] Starting {len(tasks)} OCR tasks...")
        if tasks:
            await asyncio.gather(*tasks)

        # Consolidate OCR text from all pages
        all_text_blocks = []
        consolidated_text = []
        for doc in documents:
            for page in doc.pages:
                if page.ocr_text:
                    consolidated_text.append(page.ocr_text)
                all_text_blocks.extend(page.text_blocks)
        
        # Update state
        state = state.model_copy(update={
            "documents": documents,
            "ocr_text": "\n".join(consolidated_text),
            "text_blocks": all_text_blocks
        })
        
        # Final memory cleanup
        self.memory_manager.cleanup_memory()
        self.memory_manager.log_memory_usage("after OCR processing")
        
        print(f"✅ [OCR Manager] Processing complete: {len(consolidated_text)} pages, {len(all_text_blocks)} text blocks")
        return state


def ocr_manager_wrapper(llm_builder):
    """Wrapper function to create OCR manager instance"""
    agent = OCRManager(llm_builder)
    async def wrapper(state: MCPAgentState):
        return await agent.process(state)
    return wrapper

