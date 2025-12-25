"""Mapping Manager for mapping Salesforce fields to OCR text"""
from __future__ import annotations
import asyncio
import json
import time
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage

from app.state import MCPAgentState, TextBlock
from app.config.config_loader import get_config_loader
from app.config.llm_builder import LLMBuilderFactory


_MAPPING_PROMPT_SYSTEM = """Tu es un expert en extraction de données structurées depuis des documents.
Ton rôle est de mapper les champs demandés aux informations extraites du texte OCR.

Instructions:
1. Analyse le texte OCR et les blocs de texte fournis
2. Identifie les correspondances entre les champs demandés et le texte
3. Pour chaque champ, trouve la valeur la plus pertinente dans le texte
4. Indique la confiance de chaque mapping (0.0 à 1.0)
5. Si un champ n'est pas trouvé, indique null avec confiance 0.0

Format de réponse JSON:
{
  "field_mappings": {
    "field_name": {
      "value": "valeur extraite",
      "confidence": 0.95,
      "source": "block_id ou 'text'",
      "justification": "explication de l'extraction"
    }
  },
  "extracted_data": {
    "field_name": "valeur finale"
  },
  "confidence_scores": {
    "field_name": 0.95
  }
}
"""


class MappingManager:
    """Mapping Manager for mapping Salesforce fields to OCR text"""
    
    def __init__(self, llm_builder):
        """Initialize Mapping Manager with LLM builder"""
        cfg = get_config_loader().get_agent_config("ocr_mapping_tool")
        
        # Get provider and model from config
        provider = cfg.get("provider", "openai")
        model = cfg["model"]
        
        # Create LLM builder and build model
        builder = LLMBuilderFactory.create_builder(provider)
        self.model = builder.build_llm(
            model=model,
            temperature=cfg.get("temperature", 0.0),
        )
        self.timeout_s = int(cfg.get("timeout_s", 60))

    async def map_fields_to_ocr(
        self,
        ocr_text: str,
        text_blocks: List[TextBlock],
        fields_dictionary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Map Salesforce fields to OCR text.
        
        Args:
            ocr_text: Consolidated OCR text from all pages
            text_blocks: List of text blocks with bounding boxes
            fields_dictionary: Dictionary of fields to extract
            
        Returns:
            Dictionary with field_mappings, extracted_data, and confidence_scores
        """
        print(f"🗺️ [Mapping] Starting field mapping...")
        print(f"📝 [Mapping] OCR text length: {len(ocr_text)}")
        print(f"📦 [Mapping] Text blocks: {len(text_blocks)}")
        print(f"📋 [Mapping] Fields to map: {len(fields_dictionary)}")
        
        # Prepare text blocks summary for LLM
        blocks_summary = []
        for i, block in enumerate(text_blocks[:50]):  # Limit to 50 blocks
            blocks_summary.append({
                "block_id": block.block_id,
                "text": block.text[:200],  # Truncate long text
                "block_type": block.block_type,
                "confidence": block.confidence
            })
        
        # Prepare fields description
        fields_description = []
        for field_name, field_info in fields_dictionary.items():
            if isinstance(field_info, dict):
                label = field_info.get("label", field_name)
                field_type = field_info.get("type", "text")
                required = field_info.get("required", False)
                possible_values = field_info.get("possibleValues", [])
                
                field_desc = {
                    "field_name": field_name,
                    "label": label,
                    "type": field_type,
                    "required": required
                }
                if possible_values:
                    field_desc["possible_values"] = possible_values
                fields_description.append(field_desc)
            else:
                fields_description.append({
                    "field_name": field_name,
                    "label": str(field_info),
                    "type": "text",
                    "required": False
                })
        
        # Build prompt
        system = SystemMessage(content=_MAPPING_PROMPT_SYSTEM)
        
        prompt_data = {
            "ocr_text": ocr_text[:5000],  # Limit OCR text length
            "text_blocks": blocks_summary,
            "fields_to_extract": fields_description
        }
        
        human = HumanMessage(content=json.dumps(prompt_data, ensure_ascii=False, indent=2))
        
        try:
            start_time = time.time()
            resp = await asyncio.wait_for(
                self.model.ainvoke([system, human]),
                timeout=self.timeout_s
            )
            request_time = time.time() - start_time
            print(f"📥 [Mapping] LLM response received in {request_time:.2f}s")
            
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
            
            # Extract results
            field_mappings = data.get("field_mappings", {})
            extracted_data = data.get("extracted_data", {})
            confidence_scores = data.get("confidence_scores", {})
            
            # Ensure all fields have confidence scores
            for field_name in extracted_data.keys():
                if field_name not in confidence_scores:
                    confidence_scores[field_name] = field_mappings.get(field_name, {}).get("confidence", 0.0)
            
            print(f"✅ [Mapping] Mapped {len(extracted_data)} fields")
            print(f"📊 [Mapping] Average confidence: {sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0:.2f}")
            
            return {
                "field_mappings": field_mappings,
                "extracted_data": extracted_data,
                "confidence_scores": confidence_scores
            }
            
        except asyncio.TimeoutError:
            print(f"⏰ [Mapping] Timeout after {self.timeout_s}s")
            return {
                "field_mappings": {},
                "extracted_data": {},
                "confidence_scores": {}
            }
        except json.JSONDecodeError as e:
            print(f"❌ [Mapping] JSON decode error: {e}")
            print(f"📝 [Mapping] Raw response: {content[:500]}")
            return {
                "field_mappings": {},
                "extracted_data": {},
                "confidence_scores": {}
            }
        except Exception as e:
            print(f"❌ [Mapping] General error: {e}")
            return {
                "field_mappings": {},
                "extracted_data": {},
                "confidence_scores": {}
            }

