"""Mapping Manager for mapping Salesforce fields to OCR text"""
from __future__ import annotations
import asyncio
import json
import time
from typing import Dict, Any, List, Tuple
from langchain_core.messages import SystemMessage, HumanMessage

from app.state import MCPAgentState, TextBlock
from app.config.config_loader import get_config_loader
from app.config.llm_builder import LLMBuilderFactory
from app.core.config import limits_config


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
        # Use LLM extraction timeout if available, otherwise fallback to default
        self.timeout_s = float(cfg.get("llm_extraction_timeout", cfg.get("timeout_s", 120)))
    
    def _chunk_ocr_text(self, ocr_text: str) -> List[str]:
        """
        Chunk OCR text into smaller pieces with overlap for context preservation.
        
        Args:
            ocr_text: Full OCR text
            
        Returns:
            List of text chunks
        """
        if len(ocr_text) <= limits_config.max_ocr_text_length:
            return [ocr_text]
        
        chunks = []
        chunk_size = limits_config.ocr_text_chunk_size
        overlap = limits_config.ocr_text_chunk_overlap
        start = 0
        
        while start < len(ocr_text):
            end = start + chunk_size
            chunk = ocr_text[start:end]
            
            # Try to break at word boundary if not at end
            if end < len(ocr_text):
                last_space = chunk.rfind(' ')
                if last_space > chunk_size * 0.8:  # Only break if we're not too far from end
                    chunk = chunk[:last_space]
                    end = start + last_space
            
            chunks.append(chunk)
            start = end - overlap  # Overlap for context
            
        return chunks
    
    def _prioritize_fields(self, fields_dictionary: Dict[str, Any]) -> List[Tuple[str, Any]]:
        """
        Prioritize fields: required fields first, then by type.
        
        Args:
            fields_dictionary: Dictionary of fields
            
        Returns:
            List of (field_name, field_info) tuples in priority order
        """
        required_fields = []
        optional_fields = []
        
        for field_name, field_info in fields_dictionary.items():
            if isinstance(field_info, dict) and field_info.get("required", False):
                required_fields.append((field_name, field_info))
            else:
                optional_fields.append((field_name, field_info))
        
        # Sort required fields by type (picklist/radio first for better matching)
        def sort_key(item):
            field_info = item[1]
            if isinstance(field_info, dict):
                field_type = field_info.get("type", "text").lower()
                if field_type in ["picklist", "radio"]:
                    return (0, field_type)
                elif field_type == "number":
                    return (1, field_type)
                else:
                    return (2, field_type)
            return (3, "text")
        
        required_fields.sort(key=sort_key)
        optional_fields.sort(key=sort_key)
        
        return required_fields + optional_fields
    
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
        ocr_text: str,
        text_blocks: List[TextBlock],
        fields_dictionary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Map Salesforce fields to OCR text with intelligent pagination and chunking.
        
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
        
        # Prioritize fields (required first)
        prioritized_fields = self._prioritize_fields(fields_dictionary)
        
        # Prepare text blocks summary with limits
        blocks_summary = self._prepare_text_blocks_summary(text_blocks)
        
        # Prepare fields description
        fields_description = []
        for field_name, field_info in prioritized_fields:
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
        
        # Chunk OCR text if needed
        ocr_chunks = self._chunk_ocr_text(ocr_text)
        
        if len(ocr_chunks) > 1:
            print(f"📄 [Mapping] OCR text split into {len(ocr_chunks)} chunks for processing")
        
        # Process each chunk and aggregate results
        all_field_mappings = {}
        all_extracted_data = {}
        all_confidence_scores = {}
        
        for chunk_idx, ocr_chunk in enumerate(ocr_chunks):
            print(f"🔄 [Mapping] Processing chunk {chunk_idx + 1}/{len(ocr_chunks)} ({len(ocr_chunk)} chars)")
            
            # Build prompt
            system = SystemMessage(content=_MAPPING_PROMPT_SYSTEM)
            
            prompt_data = {
                "ocr_text": ocr_chunk,
                "text_blocks": blocks_summary,
                "fields_to_extract": fields_description,
                "chunk_info": {
                    "chunk_number": chunk_idx + 1,
                    "total_chunks": len(ocr_chunks)
                } if len(ocr_chunks) > 1 else None
            }
            
            human = HumanMessage(content=json.dumps(prompt_data, ensure_ascii=False, indent=2))
            
            try:
                start_time = time.time()
                resp = await asyncio.wait_for(
                    self.model.ainvoke([system, human]),
                    timeout=self.timeout_s
                )
                request_time = time.time() - start_time
                print(f"📥 [Mapping] Chunk {chunk_idx + 1} response received in {request_time:.2f}s")
                
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
                
                # Aggregate results (keep highest confidence for each field)
                chunk_field_mappings = data.get("field_mappings", {})
                chunk_extracted_data = data.get("extracted_data", {})
                chunk_confidence_scores = data.get("confidence_scores", {})
                
                for field_name in chunk_extracted_data.keys():
                    chunk_confidence = chunk_confidence_scores.get(field_name, 0.0)
                    existing_confidence = all_confidence_scores.get(field_name, 0.0)
                    
                    # Keep the result with higher confidence
                    if chunk_confidence > existing_confidence:
                        all_extracted_data[field_name] = chunk_extracted_data[field_name]
                        all_confidence_scores[field_name] = chunk_confidence
                        if field_name in chunk_field_mappings:
                            all_field_mappings[field_name] = chunk_field_mappings[field_name]
                
            except asyncio.TimeoutError:
                print(f"⏰ [Mapping] Timeout for chunk {chunk_idx + 1} after {self.timeout_s}s")
                continue
            except json.JSONDecodeError as e:
                print(f"❌ [Mapping] JSON decode error for chunk {chunk_idx + 1}: {e}")
                continue
            except Exception as e:
                print(f"❌ [Mapping] Error processing chunk {chunk_idx + 1}: {e}")
                continue
        
        # Ensure all fields have confidence scores
        for field_name in all_extracted_data.keys():
            if field_name not in all_confidence_scores:
                all_confidence_scores[field_name] = all_field_mappings.get(field_name, {}).get("confidence", 0.0)
        
        print(f"✅ [Mapping] Mapped {len(all_extracted_data)} fields")
        if all_confidence_scores:
            avg_confidence = sum(all_confidence_scores.values()) / len(all_confidence_scores)
            print(f"📊 [Mapping] Average confidence: {avg_confidence:.2f}")
        
        return {
            "field_mappings": all_field_mappings,
            "extracted_data": all_extracted_data,
            "confidence_scores": all_confidence_scores
        }

