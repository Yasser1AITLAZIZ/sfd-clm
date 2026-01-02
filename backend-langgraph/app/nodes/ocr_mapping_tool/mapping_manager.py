"""Mapping Manager for mapping Salesforce fields to OCR text"""
from __future__ import annotations
import asyncio
import json
import time
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage

from app.state import TextBlock, Document
from app.config.config_loader import get_config_loader
from app.config.llm_builder import LLMBuilderFactory
from app.core.config import limits_config


_MAPPING_PROMPT_SYSTEM = """Tu es un expert en extraction de données structurées depuis des documents OCR.

TON OBJECTIF PRINCIPAL: Remplir le champ 'dataValue_target_AI' pour chaque champ du formulaire.

RÈGLE D'OR (GOLDEN RULE):
⚠️ Si tu ne trouves PAS l'information dans le texte OCR (qui est la référence de toutes les informations),
   tu DOIS mettre "non disponible" dans 'dataValue_target_AI'.
   Ne mets JAMAIS null, mets TOUJOURS "non disponible" si l'information n'est pas trouvée.

RÈGLES CRITIQUES:
1. POUR LES CHAMPS AVEC possibleValues (picklist, radio):
   - Analyse le texte OCR
   - Identifie la valeur la plus proche parmi les possibleValues
   - Insère EXACTEMENT cette valeur dans 'dataValue_target_AI'
   - Si aucune valeur ne correspond → "non disponible"

2. POUR LES CHAMPS SANS possibleValues (text, number, textarea):
   - Analyse le texte OCR
   - Extrais la valeur directement depuis le texte
   - Insère cette valeur dans 'dataValue_target_AI'
   - Si la valeur n'est pas trouvée → "non disponible"

3. STRUCTURE DE RÉPONSE:
   - Retourne le MÊME JSON avec la même structure
   - Ne change PAS les autres champs
   - Remplis UNIQUEMENT 'dataValue_target_AI' (et 'confidence')

4. CONFIDENCE:
   - Ajoute 'confidence' (0.0 à 1.0) pour chaque champ
   - 1.0 = valeur trouvée avec certitude
   - 0.0 = valeur non trouvée (donc "non disponible")

Format de réponse JSON:
{
  "filled_form_json": [
    {
      "label": "...",
      "type": "...",
      "required": true,
      "possibleValues": [...],
      "defaultValue": null,
      "dataValue_target_AI": "valeur extraite ou 'non disponible'",
      "confidence": 0.95
    }
  ]
}
"""


class MappingManager:
    """Mapping Manager for mapping Salesforce fields to OCR text"""
    
    def __init__(self, llm_builder):
        """Initialize Mapping Manager with LLM builder"""
        cfg = get_config_loader().get_agent_config("mapping")
        
        # Get provider and model from config
        provider = cfg.get("provider", "openai")
        model = cfg["model"]
        
        # Create LLM builder and build model
        builder = LLMBuilderFactory.create_builder(provider)
        self.model = builder.build_llm(
            model=model,
            temperature=cfg.get("temperature", 0.0),
        )
        # Use LLM extraction timeout if available, otherwise fallback to default
        self.timeout_s = float(cfg.get("llm_extraction_timeout", 120))
    
    
    def _prepare_text_blocks_summary(self, text_blocks: List[TextBlock]) -> List[Dict[str, Any]]:
        """
        Prepare text blocks summary with pagination support.
        
        Args:
            text_blocks: List of text blocks
            
        Returns:
            List of block summaries
        """
        max_blocks = limits_config.max_text_blocks
        max_block_length = limits_config.max_text_block_length
        
        blocks_summary = []
        for i, block in enumerate(text_blocks[:max_blocks]):
            blocks_summary.append({
                "block_id": block.block_id,
                "text": block.text[:max_block_length] + ("..." if len(block.text) > max_block_length else ""),
                "block_type": block.block_type,
                "confidence": block.confidence
            })
        
        if len(text_blocks) > max_blocks:
            print(f"⚠️ [Mapping] Truncated {len(text_blocks)} blocks to {max_blocks} blocks")
        
        return blocks_summary

    async def map_fields_to_ocr(
        self,
        documents: List[Document],
        form_json: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Map Salesforce fields to OCR text, processing page by page.
        
        Args:
            documents: List of documents with pages containing OCR text
            form_json: List of field objects (same structure as input)
            
        Returns:
            Dictionary with filled_form_json (same structure with dataValue_target_AI filled)
        """
        print(f"🗺️ [Mapping] Starting page-by-page field mapping...")
        print(f"📄 [Mapping] Documents: {len(documents)}")
        print(f"📋 [Mapping] Fields to map: {len(form_json)}")
        
        # Prepare form JSON for prompt (ensure it's a list of dicts)
        form_json_for_prompt = []
        for field in form_json:
            if isinstance(field, dict):
                form_json_for_prompt.append(field)
            elif hasattr(field, 'model_dump'):
                form_json_for_prompt.append(field.model_dump())
            else:
                # Convert to dict
                form_json_for_prompt.append(dict(field) if hasattr(field, '__dict__') else {})
        
        # Collect all pages from all documents with their OCR data
        all_pages = []
        for doc in documents:
            for page in doc.pages:
                if page.ocr_text and page.processed:
                    all_pages.append({
                        "page_number": page.page_number,
                        "ocr_text": page.ocr_text,
                        "text_blocks": page.text_blocks,
                        "quality_score_ocerization": page.quality_score_ocerization,
                        "doc_id": doc.id
                    })
        
        print(f"📄 [Mapping] Processing {len(all_pages)} pages")
        
        if not all_pages:
            # No pages to process, return empty result
            print("⚠️ [Mapping] No processed pages found, filling with 'non disponible'")
            filled_form_json = []
            for field in form_json_for_prompt:
                field_copy = field.copy() if isinstance(field, dict) else {}
                field_copy["dataValue_target_AI"] = "non disponible"
                field_copy["confidence"] = 0.0
                field_copy["quality_score"] = 0.0
                filled_form_json.append(field_copy)
            
            return {
                "filled_form_json": filled_form_json,
                "confidence_scores": {}
            }
        
        # Process each page separately and merge results
        filled_form_json = None
        page_results = []  # Store results per page for tracking
        
        for page_idx, page_data in enumerate(all_pages):
            page_num = page_data["page_number"]
            ocr_text = page_data["ocr_text"]
            text_blocks = page_data["text_blocks"]
            page_quality = page_data["quality_score_ocerization"]
            
            print(f"🔄 [Mapping] Processing page {page_num} ({page_idx + 1}/{len(all_pages)}) - {len(ocr_text)} chars, quality={page_quality:.2f}")
            
            # Prepare text blocks summary for this page
            blocks_summary = self._prepare_text_blocks_summary(text_blocks)
            
            # Build prompt
            system = SystemMessage(content=_MAPPING_PROMPT_SYSTEM)
            
            prompt_data = {
                "ocr_text": ocr_text,
                "text_blocks": blocks_summary,
                "form_json": form_json_for_prompt,
                "page_info": {
                    "page_number": page_num,
                    "total_pages": len(all_pages),
                    "quality_score_ocerization": page_quality
                }
            }
            
            human = HumanMessage(content=json.dumps(prompt_data, ensure_ascii=False, indent=2))
            
            try:
                start_time = time.time()
                resp = await asyncio.wait_for(
                    self.model.ainvoke([system, human]),
                    timeout=self.timeout_s
                )
                request_time = time.time() - start_time
                print(f"📥 [Mapping] Page {page_num} response received in {request_time:.2f}s")
                
                # Parse response
                content = resp.content
                if isinstance(content, str):
                    # Remove code fences if present
                    content = content.strip()
                    if content.startswith("```"):
                        lines = content.split("\n")
                        content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                    data = json.loads(content)
                else:
                    data = content
                
                # Get filled_form_json from response
                page_filled_form_json = data.get("filled_form_json", [])
                
                if page_filled_form_json:
                    # Store page result for tracking
                    page_results.append({
                        "page_number": page_num,
                        "quality_score_ocerization": page_quality,
                        "filled_form_json": page_filled_form_json
                    })
                    
                    # Merge results using quality-weighted logic
                    if filled_form_json is None:
                        # First page: initialize with its results and calculate quality_score for each field
                        filled_form_json = []
                        for field in page_filled_form_json:
                            field_copy = field.copy()
                            field_conf = field_copy.get("confidence", 0.0)
                            # Calculate and store quality_score (weighted confidence)
                            field_copy["quality_score"] = field_conf * page_quality
                            filled_form_json.append(field_copy)
                    else:
                        # Merge with existing results using quality-weighted logic
                        for i, field in enumerate(page_filled_form_json):
                            if i < len(filled_form_json):
                                existing_value = filled_form_json[i].get("dataValue_target_AI")
                                new_value = field.get("dataValue_target_AI")
                                existing_conf = filled_form_json[i].get("confidence", 0.0)
                                new_conf = field.get("confidence", 0.0)
                                
                                # Get existing quality_score (which is the weighted confidence)
                                existing_quality_score = filled_form_json[i].get("quality_score", 0.0)
                                
                                # Calculate weighted confidences
                                weighted_existing = existing_quality_score  # Already weighted
                                weighted_new = new_conf * page_quality
                                
                                # Merging logic:
                                # 1. Prefer non-"non disponible" over "non disponible"
                                # 2. If both have values, prefer higher weighted confidence
                                should_replace = False
                                
                                if new_value != "non disponible" and existing_value == "non disponible":
                                    # New value is available, existing is not -> replace
                                    should_replace = True
                                elif new_value != "non disponible" and existing_value != "non disponible":
                                    # Both have values -> compare weighted confidence
                                    if weighted_new > weighted_existing:
                                        should_replace = True
                                # If new is "non disponible" and existing is not, keep existing
                                
                                if should_replace:
                                    field_copy = field.copy()
                                    field_copy["quality_score"] = weighted_new
                                    filled_form_json[i] = field_copy
                                    print(f"  ✓ [Mapping] Field {i} updated from page {page_num} (weighted conf: {weighted_new:.3f} > {weighted_existing:.3f})")
                
            except asyncio.TimeoutError:
                print(f"⏰ [Mapping] Timeout for page {page_num} after {self.timeout_s}s")
                continue
            except json.JSONDecodeError as e:
                print(f"❌ [Mapping] JSON decode error for page {page_num}: {e}")
                continue
            except Exception as e:
                print(f"❌ [Mapping] Error processing page {page_num}: {e}")
                import traceback
                print(f"   Traceback: {traceback.format_exc()}")
                continue
        
        # If no response, create filled_form_json with "non disponible" for all fields
        if filled_form_json is None:
            print("⚠️ [Mapping] No successful response, filling with 'non disponible'")
            filled_form_json = []
            for field in form_json_for_prompt:
                field_copy = field.copy() if isinstance(field, dict) else {}
                field_copy["dataValue_target_AI"] = "non disponible"
                field_copy["confidence"] = 0.0
                field_copy["quality_score"] = 0.0
                filled_form_json.append(field_copy)
        
        # Post-process: ensure all fields have dataValue_target_AI, confidence, and quality_score
        for field in filled_form_json:
            if "dataValue_target_AI" not in field or field.get("dataValue_target_AI") is None:
                field["dataValue_target_AI"] = "non disponible"
            if "confidence" not in field:
                field["confidence"] = 0.0 if field.get("dataValue_target_AI") == "non disponible" else 0.5
            if "quality_score" not in field:
                # Calculate quality_score if missing (shouldn't happen, but safety check)
                field["quality_score"] = field.get("confidence", 0.0) * 1.0  # Default page quality of 1.0
        
        # Extract confidence scores for backward compatibility
        confidence_scores = {}
        for field in filled_form_json:
            label = field.get("label", "")
            if label:
                confidence_scores[label] = field.get("confidence", 0.0)
        
        # Calculate overall quality_score as average of per-field quality_scores
        overall_quality_score = None
        if filled_form_json:
            field_quality_scores = [f.get("quality_score", 0.0) for f in filled_form_json if f.get("quality_score") is not None]
            if field_quality_scores:
                overall_quality_score = sum(field_quality_scores) / len(field_quality_scores)
        
        print(f"✅ [Mapping] Filled {len(filled_form_json)} fields across {len(page_results)} pages")
        if overall_quality_score is not None:
            print(f"📊 [Mapping] Overall quality score: {overall_quality_score:.2f}")
        
        return {
            "filled_form_json": filled_form_json,
            "confidence_scores": confidence_scores,
            "quality_score": overall_quality_score
        }

