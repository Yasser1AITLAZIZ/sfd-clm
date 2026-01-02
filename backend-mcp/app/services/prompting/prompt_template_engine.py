"""Prompt template engine using Jinja2"""
from typing import Dict, Any, Optional
import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template

from app.core.logging import get_logger, safe_log

logger = get_logger(__name__)


class PromptTemplateEngine:
    """Engine for loading and rendering prompt templates"""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize template engine.
        
        Args:
            templates_dir: Directory containing templates (default: app/services/prompting/templates)
        """
        if templates_dir is None:
            # Default to templates directory relative to this file
            base_dir = Path(__file__).parent
            templates_dir = str(base_dir / "templates")
        
        try:
            self.env = Environment(
                loader=FileSystemLoader(templates_dir),
                trim_blocks=True,
                lstrip_blocks=True
            )
            
            safe_log(
                logger,
                logging.INFO,
                "PromptTemplateEngine initialized",
                templates_dir=templates_dir
            )
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Failed to initialize template engine",
                templates_dir=templates_dir,
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            # Fallback to string templates
            self.env = None
    
    def load_template(self, scenario_type: str) -> Optional[Template]:
        """
        Load template for scenario type.
        
        Args:
            scenario_type: Type of scenario (initialization, extraction, clarification, validation)
            
        Returns:
            Jinja2 template or None if not found
        """
        try:
            template_name = f"{scenario_type}_template.j2"
            
            if self.env is None:
                safe_log(
                    logger,
                    logging.WARNING,
                    "Template engine not initialized, using default template",
                    scenario_type=scenario_type
                )
                return self._get_default_template(scenario_type)
            
            template = self.env.get_template(template_name)
            
            safe_log(
                logger,
                logging.INFO,
                "Template loaded",
                scenario_type=scenario_type,
                template_name=template_name
            )
            
            return template
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error loading template",
                scenario_type=scenario_type,
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            # Return default template on error
            return self._get_default_template(scenario_type)
    
    def render_template(
        self,
        template: Template,
        variables: Dict[str, Any]
    ) -> str:
        """
        Render template with variables.
        
        Args:
            template: Jinja2 template
            variables: Dictionary of variables for template
            
        Returns:
            Rendered prompt string
        """
        try:
            if template is None:
                safe_log(
                    logger,
                    logging.WARNING,
                    "Template is None, returning empty string"
                )
                return ""
            
            rendered = template.render(**variables)
            
            safe_log(
                logger,
                logging.INFO,
                "Template rendered",
                prompt_length=len(rendered) if rendered else 0
            )
            
            return rendered
            
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "Error rendering template",
                error_type=type(e).__name__,
                error_message=str(e) if e else "Unknown"
            )
            return ""
    
    def _get_default_template(self, scenario_type: str) -> Template:
        """Get default template as fallback"""
        default_templates = {
            "initialization": """# Contexte
Type de record: {{ record_type }}
Objectif: {{ objective }}

# Documents disponibles
{% for doc in documents %}
- {{ doc.name }} ({{ doc.type }})
{% endfor %}

# Form Fields (JSON)
{{ form_json }}
{% endfor %}

# Requête utilisateur
{{ user_request }}

# Instructions
{{ instructions }}
""",
            "extraction": """# Extraction de données
{{ context_summary }}

# Documents
{{ documents_description }}

# Champs à extraire
{{ fields_to_fill }}

# Requête
{{ user_request }}
""",
            "clarification": """# Clarification nécessaire
{{ context_summary }}

# Historique conversation
{{ conversation_history }}

# Question
{{ user_request }}
""",
            "validation": """# Validation des données
{{ context_summary }}

# Données extraites
{{ extracted_data }}

# Requête
{{ user_request }}
"""
        }
        
        template_str = default_templates.get(
            scenario_type,
            default_templates["initialization"]
        )
        
        return Template(template_str)

