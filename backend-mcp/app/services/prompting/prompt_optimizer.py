"""Prompt optimizer for optimizing prompts for performance and cost"""
from typing import Dict, Any, Optional
import logging
import hashlib

from app.core.logging import get_logger, safe_log
from app.models.schemas import (
    PromptResponseSchema,
    OptimizedPromptSchema,
    PromptMetricsSchema
)

logger = get_logger(__name__)


class PromptOptimizer:
    """Optimizer for prompts"""
    
    def __init__(self):
        """Initialize prompt optimizer"""
        self.prompt_cache: Dict[str, str] = {}
        
        safe_log(
            logger,
            logging.INFO,
            "PromptOptimizer initialized"
        )
    
    async def optimize(
        self,
        prompt_response: PromptResponseSchema,
        max_tokens: Optional[int] = None
    ) -> OptimizedPromptSchema:
        """
        Optimize prompt for performance and cost.
        
        Args:
            prompt_response: Prompt response schema
            max_tokens: Maximum tokens allowed (default: None = no limit)
            
        Returns:
            Optimized prompt schema
        """
        try:
            prompt = prompt_response.prompt if prompt_response.prompt else ""
            
            safe_log(
                logger,
                logging.INFO,
                "Optimizing prompt",
                original_length=len(prompt),
                max_tokens=max_tokens or "none"
            )
            
            # Check cache
            prompt_hash = self._hash_prompt(prompt)
            if prompt_hash in self.prompt_cache:
                cached_prompt = self.prompt_cache[prompt_hash]
                safe_log(
                    logger,
                    logging.INFO,
                    "Using cached prompt",
                    prompt_hash=prompt_hash[:8]
                )
                return OptimizedPromptSchema(
                    prompt=cached_prompt,
                    original_length=len(prompt),
                    optimized_length=len(cached_prompt),
                    tokens_estimated=self.count_tokens(cached_prompt),
                    quality_score=100.0,
                    optimizations_applied=[]
                )
            
            # Count tokens
            tokens_estimated = self.count_tokens(prompt)
            
            # Validate quality
            quality_score = self.validate_prompt_quality(prompt)
            
            optimized_prompt = prompt
            optimizations_applied = []
            
            # Compress if needed
            if max_tokens and tokens_estimated > max_tokens:
                safe_log(
                    logger,
                    logging.INFO,
                    "Prompt exceeds max tokens, compressing",
                    tokens_estimated=tokens_estimated,
                    max_tokens=max_tokens
                )
                
                optimized_prompt, applied = await self.compress_prompt_if_needed(
                    prompt,
                    max_tokens
                )
                optimizations_applied.extend(applied)
            
            # Cache optimized prompt
            optimized_hash = self._hash_prompt(optimized_prompt)
            self.prompt_cache[optimized_hash] = optimized_prompt
            
            result = OptimizedPromptSchema(
                prompt=optimized_prompt,
                original_length=len(prompt),
                optimized_length=len(optimized_prompt),
                tokens_estimated=self.count_tokens(optimized_prompt),
                quality_score=quality_score,
                optimizations_applied=optimizations_applied,
                cost_estimated=self._estimate_cost(optimized_prompt)
            )
            
            safe_log(
                logger,
                logging.INFO,
                "Prompt optimized",
                original_length=len(prompt),
                optimized_length=len(optimized_prompt),
                tokens_estimated=result.tokens_estimated,
                quality_score=quality_score
            )
            
            return result
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error optimizing prompt",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error"
            )
            return OptimizedPromptSchema(
                prompt=prompt_response.prompt if prompt_response else "",
                original_length=len(prompt_response.prompt) if prompt_response else 0,
                optimized_length=len(prompt_response.prompt) if prompt_response else 0,
                tokens_estimated=0,
                quality_score=0.0,
                optimizations_applied=[]
            )
    
    def count_tokens(self, prompt: str) -> int:
        """
        Count tokens in prompt (estimation).
        
        Uses simple estimation: 1 token ≈ 4 characters
        
        Args:
            prompt: Prompt text
            
        Returns:
            Estimated token count
        """
        try:
            if not prompt:
                return 0
            
            # Simple estimation: 1 token ≈ 4 characters
            # This is a rough estimate; for accurate counting, use tiktoken
            estimated_tokens = len(prompt) // 4
            
            return max(1, estimated_tokens)  # At least 1 token
            
        except Exception:
            return 0
    
    async def compress_prompt_if_needed(
        self,
        prompt: str,
        max_tokens: int
    ) -> tuple[str, list[str]]:
        """
        Compress prompt if it exceeds max_tokens.
        
        Args:
            prompt: Prompt text
            max_tokens: Maximum tokens allowed
            
        Returns:
            Tuple of (compressed_prompt, list_of_optimizations_applied)
        """
        try:
            optimizations = []
            compressed = prompt
            
            current_tokens = self.count_tokens(compressed)
            
            # Strategy 1: Reduce conversation history (if present)
            if "Historique récent" in compressed and current_tokens > max_tokens:
                # Keep only summary of history
                lines = compressed.split("\n")
                new_lines = []
                in_history = False
                for line in lines:
                    if "Historique récent" in line:
                        in_history = True
                        new_lines.append(line)
                        new_lines.append("- Résumé: Conversation précédente...")
                    elif in_history and line.startswith("-"):
                        # Skip detailed history
                        continue
                    elif in_history and not line.startswith("-"):
                        in_history = False
                        new_lines.append(line)
                    else:
                        new_lines.append(line)
                
                compressed = "\n".join(new_lines)
                current_tokens = self.count_tokens(compressed)
                optimizations.append("reduced_conversation_history")
            
            # Strategy 2: Summarize long document descriptions
            if current_tokens > max_tokens:
                # Truncate long sections
                sections = compressed.split("\n\n")
                new_sections = []
                for section in sections:
                    if len(section) > 500:  # Long section
                        # Keep first and last parts
                        truncated = section[:250] + "\n...\n" + section[-250:]
                        new_sections.append(truncated)
                        optimizations.append("truncated_long_sections")
                    else:
                        new_sections.append(section)
                
                compressed = "\n\n".join(new_sections)
                current_tokens = self.count_tokens(compressed)
            
            # Strategy 3: Simplify instructions
            if current_tokens > max_tokens and "Instructions" in compressed:
                # Replace detailed instructions with summary
                lines = compressed.split("\n")
                new_lines = []
                in_instructions = False
                for line in lines:
                    if "Instructions" in line:
                        in_instructions = True
                        new_lines.append(line)
                        new_lines.append("Extraire et valider les données selon les règles métier.")
                    elif in_instructions and line.strip() and not line.startswith("#"):
                        # Skip detailed instructions
                        continue
                    elif in_instructions and line.startswith("#"):
                        in_instructions = False
                        new_lines.append(line)
                    elif not in_instructions:
                        new_lines.append(line)
                
                compressed = "\n".join(new_lines)
                optimizations.append("simplified_instructions")
            
            return compressed, optimizations
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error compressing prompt",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return prompt, []
    
    def validate_prompt_quality(self, prompt: str) -> float:
        """
        Validate prompt quality and return score (0-100).
        
        Args:
            prompt: Prompt text
            
        Returns:
            Quality score from 0 to 100
        """
        try:
            if not prompt:
                return 0.0
            
            score = 100.0
            
            # Check for required elements
            required_elements = [
                "Documents",
                "Champs",
                "Requête"
            ]
            
            for element in required_elements:
                if element.lower() not in prompt.lower():
                    score -= 20
            
            # Check for ambiguities (simple check)
            ambiguous_words = ["peut-être", "probablement", "peut être", "?"]
            for word in ambiguous_words:
                if word in prompt.lower():
                    score -= 5
            
            # Check length (too short or too long is bad)
            if len(prompt) < 100:
                score -= 30
            elif len(prompt) > 10000:
                score -= 20
            
            # Ensure score is between 0 and 100
            score = max(0.0, min(100.0, score))
            
            return score
            
        except Exception:
            return 50.0  # Default score on error
    
    def _hash_prompt(self, prompt: str) -> str:
        """Generate hash for prompt (for caching)"""
        try:
            return hashlib.md5(prompt.encode()).hexdigest()
        except Exception:
            return ""
    
    async def optimize_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Optimize prompt wrapper method for workflow orchestrator.
        
        Args:
            prompt: Prompt text string
            
        Returns:
            Dict with prompt, optimizations_applied
        """
        try:
            # Create a minimal PromptResponseSchema
            prompt_response = PromptResponseSchema(
                prompt=prompt,
                scenario_type="extraction",
                metadata={}
            )
            
            # Optimize
            optimized = await self.optimize(prompt_response)
            
            return {
                "prompt": optimized.prompt if optimized.prompt else prompt,
                "optimizations_applied": optimized.optimizations_applied if optimized.optimizations_applied else []
            }
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error in optimize_prompt wrapper",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error"
            )
            # Return original prompt
            return {
                "prompt": prompt,
                "optimizations_applied": []
            }
    
    def _estimate_cost(self, prompt: str) -> Optional[float]:
        """
        Estimate cost for prompt (if API pricing is known).
        
        Args:
            prompt: Prompt text
            
        Returns:
            Estimated cost in USD or None if unknown
        """
        # TODO: Implement cost estimation if API pricing is known
        # For now, return None
        return None

