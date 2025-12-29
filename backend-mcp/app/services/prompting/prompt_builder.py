"""Prompt builder for constructing prompts from preprocessed data"""
from typing import Dict, Any, Optional, List
import logging

from app.core.logging import get_logger, safe_log
from app.models.schemas import (
    PreprocessedDataSchema,
    SessionContextSchema,
    InitializationPromptSchema,
    ContinuationPromptSchema,
    PromptResponseSchema
)
from .prompt_template_engine import PromptTemplateEngine

logger = get_logger(__name__)


class PromptBuilder:
    """Builder for constructing prompts"""
    
    def __init__(self):
        """Initialize prompt builder"""
        self.template_engine = PromptTemplateEngine()
        
        safe_log(
            logger,
            logging.INFO,
            "PromptBuilder initialized"
        )
    
    async def build_initialization_prompt(
        self,
        preprocessed_data: PreprocessedDataSchema,
        user_request: str
    ) -> PromptResponseSchema:
        """
        Build prompt for new session (initialization flow).
        
        Args:
            preprocessed_data: Preprocessed data schema
            user_request: User request message
            
        Returns:
            Prompt response schema
        """
        try:
            record_id = preprocessed_data.record_id if preprocessed_data.record_id else "unknown"
            
            safe_log(
                logger,
                logging.INFO,
                "Building initialization prompt",
                record_id=record_id
            )
            
            # Format documents section
            documents_section = self.format_documents_section(
                preprocessed_data.processed_documents
            )
            
            # Format fields section
            fields_section = self.format_fields_section(
                preprocessed_data.fields_dictionary
            )
            
            # Get instructions for record type
            instructions = self._get_instructions_for_record_type(
                preprocessed_data.record_type
            )
            
            # Load template
            template = self.template_engine.load_template("initialization")
            
            # Prepare variables
            variables = {
                "record_type": preprocessed_data.record_type,
                "objective": preprocessed_data.context_summary.objective,
                "documents": [
                    {
                        "name": doc.name if hasattr(doc, 'name') else "unknown",
                        "type": doc.type if hasattr(doc, 'type') else "unknown",
                        "quality_score": doc.quality_score if hasattr(doc, 'quality_score') else 0
                    }
                    for doc in preprocessed_data.processed_documents
                ],
                "fields": [
                    {
                        "label": field.label if hasattr(field, 'label') else "Unknown",
                        "field_type": field.field_type if hasattr(field, 'field_type') else "text",
                        "required": field.required if hasattr(field, 'required') else True,
                        "description": field.description if hasattr(field, 'description') else "",
                        "examples": field.examples if hasattr(field, 'examples') else []
                    }
                    for field in preprocessed_data.fields_dictionary.prioritized_fields
                ],
                "user_request": user_request,
                "instructions": instructions
            }
            
            # Render template
            prompt_text = self.template_engine.render_template(template, variables)
            
            # Calculate metrics
            prompt_length = len(prompt_text)
            estimated_tokens = prompt_length // 4  # Rough estimate: 1 token ≈ 4 chars
            
            result = PromptResponseSchema(
                prompt=prompt_text,
                scenario_type="initialization",
                metadata={
                    "record_id": record_id,
                    "record_type": preprocessed_data.record_type,
                    "prompt_length": prompt_length,
                    "estimated_tokens": estimated_tokens,
                    "documents_count": len(preprocessed_data.processed_documents),
                    "fields_count": len(preprocessed_data.fields_dictionary.fields)
                }
            )
            
            safe_log(
                logger,
                logging.INFO,
                "Initialization prompt built",
                record_id=record_id,
                prompt_length=prompt_length,
                estimated_tokens=estimated_tokens
            )
            
            return result
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error building initialization prompt",
                record_id=preprocessed_data.record_id if preprocessed_data else "unknown",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error"
            )
            return PromptResponseSchema(
                prompt="",
                scenario_type="initialization",
                metadata={}
            )
    
    async def build_continuation_prompt(
        self,
        session_context: SessionContextSchema,
        user_request: str
    ) -> PromptResponseSchema:
        """
        Build prompt for existing session (continuation flow).
        
        Args:
            session_context: Session context schema
            user_request: User request message
            
        Returns:
            Prompt response schema
        """
        try:
            safe_log(
                logger,
                logging.INFO,
                "Building continuation prompt",
                history_length=len(session_context.conversation_history) if session_context.conversation_history else 0
            )
            
            # Summarize conversation history
            history_summary = self.summarize_conversation_history(
                session_context.conversation_history
            )
            
            # Format extracted data if available
            extracted_data_section = self.format_extracted_data(
                session_context.extracted_data
            )
            
            # Get initial context from salesforce_data
            salesforce_data = session_context.salesforce_data
            context_summary = f"Record: {salesforce_data.record_id} ({salesforce_data.record_type})"
            
            # Load template
            template = self.template_engine.load_template("clarification")
            
            # Prepare variables
            variables = {
                "context_summary": context_summary,
                "conversation_history": history_summary,
                "extracted_data": extracted_data_section,
                "user_request": user_request
            }
            
            # Render template
            prompt_text = self.template_engine.render_template(template, variables)
            
            # Calculate metrics
            prompt_length = len(prompt_text)
            estimated_tokens = prompt_length // 4
            
            result = PromptResponseSchema(
                prompt=prompt_text,
                scenario_type="continuation",
                metadata={
                    "prompt_length": prompt_length,
                    "estimated_tokens": estimated_tokens,
                    "history_length": len(session_context.conversation_history) if session_context.conversation_history else 0
                }
            )
            
            safe_log(
                logger,
                logging.INFO,
                "Continuation prompt built",
                prompt_length=prompt_length,
                estimated_tokens=estimated_tokens
            )
            
            return result
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error building continuation prompt",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error"
            )
            return PromptResponseSchema(
                prompt="",
                scenario_type="continuation",
                metadata={}
            )
    
    def format_documents_section(self, documents: List[Any]) -> str:
        """Format documents section for prompt"""
        try:
            if not documents:
                return "Aucun document disponible."
            
            lines = ["Documents disponibles:"]
            for i, doc in enumerate(documents, 1):
                name = doc.name if hasattr(doc, 'name') else f"Document {i}"
                doc_type = doc.type if hasattr(doc, 'type') else "unknown"
                quality = doc.quality_score if hasattr(doc, 'quality_score') else 0
                lines.append(f"{i}. {name} ({doc_type}) - Qualité: {quality}%")
            
            return "\n".join(lines)
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error formatting documents section",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return "Erreur lors du formatage des documents."
    
    def format_fields_section(self, fields_dictionary: Any) -> str:
        """Format fields section for prompt"""
        try:
            if not fields_dictionary or not hasattr(fields_dictionary, 'prioritized_fields'):
                return "Aucun champ à remplir."
            
            fields = fields_dictionary.prioritized_fields
            if not fields:
                return "Aucun champ à remplir."
            
            lines = ["Champs à remplir (par ordre de priorité):"]
            for i, field in enumerate(fields, 1):
                label = field.label if hasattr(field, 'label') else "Unknown"
                field_type = field.field_type if hasattr(field, 'field_type') else "text"
                required = "Requis" if field.required else "Optionnel"
                description = field.description if hasattr(field, 'description') else ""
                
                lines.append(f"{i}. {label} ({field_type}) - {required}")
                if description:
                    lines.append(f"   Description: {description}")
                if hasattr(field, 'examples') and field.examples:
                    examples_str = ", ".join(field.examples[:3])  # Max 3 examples
                    lines.append(f"   Exemples: {examples_str}")
            
            return "\n".join(lines)
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error formatting fields section",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return "Erreur lors du formatage des champs."
    
    def summarize_conversation_history(
        self,
        history: List[Any],
        max_exchanges: int = 5
    ) -> str:
        """Summarize conversation history (max 5 last exchanges)"""
        try:
            if not history:
                return "Aucun historique de conversation."
            
            # Get last N exchanges
            recent_history = history[-max_exchanges:] if len(history) > max_exchanges else history
            
            lines = ["Historique récent de la conversation:"]
            for msg in recent_history:
                role = msg.role if hasattr(msg, 'role') else "unknown"
                message = msg.message if hasattr(msg, 'message') else ""
                lines.append(f"- {role.capitalize()}: {message[:100]}...")  # Truncate long messages
            
            return "\n".join(lines)
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error summarizing conversation history",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return "Erreur lors du résumé de l'historique."
    
    def format_extracted_data(self, extracted_data: Dict[str, Any]) -> str:
        """Format extracted data section"""
        try:
            if not extracted_data:
                return "Aucune donnée extraite pour le moment."
            
            lines = ["Données déjà extraites:"]
            for key, value in extracted_data.items():
                lines.append(f"- {key}: {value}")
            
            return "\n".join(lines)
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error formatting extracted data",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return "Erreur lors du formatage des données extraites."
    
    async def build_prompt(
        self,
        user_message: str,
        preprocessed_data: Any,
        routing_status: str
    ) -> Dict[str, Any]:
        """
        Build prompt wrapper method for workflow orchestrator.
        
        Args:
            user_message: User request message
            preprocessed_data: Preprocessed data (can be dict or PreprocessedDataSchema)
            routing_status: "initialization" or "continuation"
            
        Returns:
            Dict with prompt, scenario_type
        """
        try:
            # Convert preprocessed_data to PreprocessedDataSchema if it's a dict
            if isinstance(preprocessed_data, dict):
                # Try to create PreprocessedDataSchema from dict
                from app.models.schemas import PreprocessedDataSchema, ContextSummarySchema
                try:
                    preprocessed_data = PreprocessedDataSchema(**preprocessed_data)
                except Exception:
                    # If conversion fails, create minimal schema
                    preprocessed_data = PreprocessedDataSchema(
                        record_id=preprocessed_data.get("record_id", "unknown"),
                        record_type=preprocessed_data.get("record_type", "Claim"),
                        processed_documents=preprocessed_data.get("processed_documents", []),
                        fields_dictionary=preprocessed_data.get("fields_dictionary", {}),
                        context_summary=ContextSummarySchema(
                            record_type=preprocessed_data.get("record_type", "Claim"),
                            objective="",
                            documents_available=[],
                            fields_to_extract=[],
                            business_rules=[]
                        ),
                        validation_results={"passed": False, "errors": []},
                        metrics={}
                    )
            
            if routing_status == "initialization":
                prompt_response = await self.build_initialization_prompt(
                    preprocessed_data,
                    user_message
                )
            else:
                # For continuation, we'd need session context, but for now use initialization
                prompt_response = await self.build_initialization_prompt(
                    preprocessed_data,
                    user_message
                )
            
            return {
                "prompt": prompt_response.prompt if prompt_response.prompt else "",
                "scenario_type": prompt_response.scenario_type if prompt_response.scenario_type else "extraction"
            }
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error in build_prompt wrapper",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown error"
            )
            # Return fallback
            return {
                "prompt": user_message or "Extract data from documents",
                "scenario_type": "extraction"
            }
    
    def _get_instructions_for_record_type(self, record_type: str) -> str:
        """Get instructions specific to record type"""
        instructions_map = {
            "Claim": """
1. Extraire toutes les informations pertinentes des documents fournis
2. Remplir tous les champs requis avec les données extraites
3. Valider la cohérence des données (montants, dates)
4. Signaler toute ambiguïté ou donnée manquante
""",
            "Invoice": """
1. Extraire le montant total, la date et le bénéficiaire
2. Vérifier la cohérence des montants et dates
3. Valider le format des données extraites
""",
            "default": """
1. Extraire les informations demandées
2. Valider la cohérence des données
3. Signaler les ambiguïtés
"""
        }
        
        return instructions_map.get(record_type, instructions_map["default"])

