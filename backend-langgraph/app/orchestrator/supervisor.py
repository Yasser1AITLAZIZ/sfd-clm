"""Supervisor ReAct Agent for MCP requests"""
from __future__ import annotations
import sys
import os
import re
import time
from typing import Any, Dict, Optional, Iterable, List
import yaml
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig, Runnable
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    AIMessage,
    ToolMessage,
    FunctionMessage,
)

from app.state import MCPAgentState
from app.config.llm_builder import LLMBuilderFactory
from app.config.config_loader import get_config_loader
from app.nodes.ocr_mapping_tool import ocr_and_mapping_tool

load_dotenv(override=True)


SUPERVISOR_PROMPT = """Tu es un agent supervisor pour le traitement de sinistres via MCP (Model Context Protocol).

Ton rôle est de:
1. Recevoir les requêtes MCP avec des documents et des champs Salesforce à remplir
2. Utiliser les tools disponibles pour extraire les données des documents
3. Retourner les données extraites avec scores de confiance

## Tools disponibles

- `ocr_and_mapping_tool`: Extrait le texte des documents avec OCR et mappe les champs Salesforce au texte extrait. 
  Utilise cette tool quand tu as des documents à traiter et des champs à extraire.

## Processus

1. **Analyse la requête**: Identifie les documents fournis et les champs à extraire
2. **Appelle ocr_and_mapping_tool**: Pour traiter les documents et extraire les données
3. **Vérifie les résultats**: Examine les données extraites et les scores de confiance
4. **Réponds à l'utilisateur**: Présente les résultats de manière claire et structurée

## Format de réponse

- Réponds toujours en français
- Sois concis et factuel
- Indique les champs extraits avec leurs valeurs
- Mentionne les scores de confiance si disponibles
- Si des champs sont manquants ou ont une faible confiance, indique-le clairement

## Règles importantes

- N'invente jamais de données
- Utilise uniquement les données extraites par les tools
- Si une donnée n'est pas disponible, indique "Non disponible"
- Ne mentionne pas les détails techniques (tools, prompts, etc.) à l'utilisateur
"""


def load_supervisor_config() -> Dict[str, Any]:
    """Load supervisor configuration section from `config_agent.yaml`."""
    config_path = Path(__file__).parents[1] / "config" / "config_agent.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config.get('supervisor', {})


_SUP_CONF = load_supervisor_config()


# ------------------------------
#   Sanitize helpers
# ------------------------------

# supprime les data:...;base64,AAAA...
_DATA_URL_RE = re.compile(r"data:[^;]+;base64,[A-Za-z0-9+/=\s]+", re.MULTILINE)

def _strip_data_urls(s: str, placeholder: str = "[[binary omitted]]") -> str:
    """Remove inline base64 data URLs to avoid sending large binary payloads."""
    return _DATA_URL_RE.sub(placeholder, s)

def _truncate(s: str, max_chars: int = 4000) -> str:
    """Truncate long strings to a safe maximum length for logging/LLM input."""
    return s if len(s) <= max_chars else (s[:max_chars] + " …[truncated]")

def _clone_msg_with_content(msg: BaseMessage, content: str) -> BaseMessage:
    """Clone a message preserving metadata while replacing its textual content."""
    return type(msg)(content=content, **{k: v for k, v in msg.__dict__.items() if k != "content"})

def _purge_additional_kwargs(m: BaseMessage) -> BaseMessage:
    """Remove attachments-like fields from `additional_kwargs` to keep messages lean."""
    if hasattr(m, "additional_kwargs") and isinstance(m.additional_kwargs, dict):
        ak = dict(m.additional_kwargs)
        for k in list(ak.keys()):
            if k in ("attachments", "files", "images", "image_urls", "image"):
                ak.pop(k, None)
        return type(m)(
            content=m.content,
            **{
                **{k: v for k, v in m.__dict__.items() if k not in ("content", "additional_kwargs")},
                "additional_kwargs": ak
            }
        )
    return m

def _coerce_content_to_str(msg: BaseMessage) -> BaseMessage:
    """Convert message content into a sanitized string representation."""
    content = msg.content
    if isinstance(content, list):
        parts: List[str] = []
        for blk in content:
            if isinstance(blk, dict):
                t = blk.get("type")
                if t == "text" and isinstance(blk.get("text"), str):
                    parts.append(blk["text"])
                elif t in {"image", "file", "image_url", "file_url", "file_path", "path"}:
                    label = t.upper()
                    if t in {"file", "image"} and isinstance(blk.get("data"), str):
                        parts.append(f"[ATTACHMENT:{label} size≈{len(blk['data'])}b64]")
                    elif t == "image_url":
                        url = (blk.get("image_url") or {}).get("url")
                        parts.append(f"[ATTACHMENT:IMAGE_URL {url}]")
                    elif t == "file_url":
                        parts.append(f"[ATTACHMENT:FILE_URL {blk.get('url')}]")
                    elif t in {"file_path","path"}:
                        parts.append(f"[ATTACHMENT:PATH {blk.get('path')}]")
        new_content = _truncate(_strip_data_urls("\n".join(parts)))
        return _clone_msg_with_content(msg, new_content)

    cleaned = _truncate(_strip_data_urls(str(content)))
    return _clone_msg_with_content(msg, cleaned)


def _sanitize_messages_for_model(messages: Iterable[BaseMessage]) -> List[BaseMessage]:
    """Sanitize chat history for the model while preserving tool traces."""
    out: List[BaseMessage] = []
    for m in messages:
        if isinstance(m, FunctionMessage):
            continue

        if isinstance(m, (HumanMessage, SystemMessage, AIMessage, ToolMessage)):
            m = _purge_additional_kwargs(m)
            out.append(_coerce_content_to_str(m))
    return out


# ------------------------------
#   Runnable proxy SANITIZING
# ------------------------------

class _SanitizingModelRunnable(Runnable[List[BaseMessage], BaseMessage]):
    """Runnable wrapper around a ChatModel that sanitizes inputs."""

    def __init__(self, model):
        self._model = model

    async def ainvoke(self, messages: List[BaseMessage], config: Optional[RunnableConfig] = None) -> BaseMessage:
        print(f"🤖 [Supervisor] Starting LLM request...")        
        print(f"📊 [Supervisor] Model: {getattr(self._model, 'deployment_name', getattr(self._model, 'model_name', 'unknown'))}")
        print(f"📝 [Supervisor] Messages count: {len(messages)}")
        
        sanitized = _sanitize_messages_for_model(messages)
        
        try:
            print(f"📤 [Supervisor] Sending request to LLM...")
            start_time = time.time()
            
            resp = await self._model.ainvoke(sanitized, config)
            
            request_time = time.time() - start_time
            print(f"📥 [Supervisor] LLM response received in {request_time:.2f}s")
            print(f"📄 [Supervisor] Response type: {type(resp)}")
            print(f"📄 [Supervisor] Response content length: {len(getattr(resp, 'content', ''))}")
            
            return resp
            
        except Exception as e:
            print(f"❌ [Supervisor] LLM request failed: {e}")
            print(f"🔍 [Supervisor] Error type: {type(e).__name__}")
            raise

    def invoke(self, messages: List[BaseMessage], config: Optional[RunnableConfig] = None) -> BaseMessage:
        """Synchronous variant of `ainvoke` with the same sanitization."""
        sanitized = _sanitize_messages_for_model(messages)
        resp = self._model.invoke(sanitized, config)
        return resp

    def bind_tools(self, tools):
        bound = self._model.bind_tools(tools)
        return _SanitizingModelRunnable(bound)

    def with_structured_output(self, *args, **kwargs):
        bound = self._model.with_structured_output(*args, **kwargs)
        return _SanitizingModelRunnable(bound)

    def __getattr__(self, item):
        return getattr(self._model, item)


# ------------------------------
#   Supervisor wrapper
# ------------------------------

async def supervisor_wrapper(state: MCPAgentState, config: Optional[RunnableConfig] = None) -> MCPAgentState:
    """Run the ReAct supervisor agent with sanitized history and tools."""
    
    print(f"🤖 [Supervisor] Initializing supervisor agent...")        
    
    # 1) Modèle brut
    provider = _SUP_CONF.get('provider', 'openai')
    model_name = _SUP_CONF['model']
    
    llm_builder = LLMBuilderFactory.create_builder(provider)
    
    if _SUP_CONF.get('temperature', None) == None:
        if _SUP_CONF.get('reasoning_effort', None) != None:
            print(f"🤖 [Supervisor] Using reasoning_effort: {_SUP_CONF.get('reasoning_effort', None)}")
            raw_model = llm_builder.build_llm(
                model=model_name,
                reasoning_effort=_SUP_CONF.get('reasoning_effort', 'low')
            )
        else:
            raw_model = llm_builder.build_llm(
                model=model_name
            )
    else:
        raw_model = llm_builder.build_llm(
            model=model_name,
            temperature=_SUP_CONF.get('temperature', 0.1),
        )
    
    # 2) Wrap en Runnable sanitizer
    model_runnable = _SanitizingModelRunnable(raw_model)

    # 3) Agent ReAct
    supervisor_agent = create_react_agent(
        model=model_runnable,
        tools=[ocr_and_mapping_tool],
        prompt=SUPERVISOR_PROMPT,
        state_schema=MCPAgentState,
        name=_SUP_CONF.get('name', 'mcp_supervisor'),
    )

    # 4) Run
    result: MCPAgentState = await supervisor_agent.ainvoke(state, config)
    return result

