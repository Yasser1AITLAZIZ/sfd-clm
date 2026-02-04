from __future__ import annotations
import os
import logging
from dotenv import load_dotenv

log = logging.getLogger("sfd-clm.observability")
_BOOT_ONCE = False

load_dotenv(override=True)

def setup_phoenix_observability(
    *,
    project_name: str = "sfd-clm-langgraph",
) -> None:
    """
    Configuration d'observabilité simplifiée pour éviter les erreurs OpenTelemetry
    """
    global _BOOT_ONCE
    if _BOOT_ONCE:
        return
    _BOOT_ONCE = True

    # Désactiver l'observabilité pour éviter les erreurs par défaut
    log.info("[Observability] Observability disabled by default to avoid OpenTelemetry errors")
    
    # Optionnel : activer seulement si nécessaire
    if os.getenv("ENABLE_PHOENIX", "true").lower() == "true":
        try:
            from phoenix.otel import register
            from openinference.instrumentation.langchain import LangChainInstrumentor
            
            # Configuration simplifiée
            os.environ.setdefault("OTEL_PYTHON_CONTEXT", "contextvars")
            
            endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")
            protocol = os.getenv("PHOENIX_OTLP_PROTOCOL", "http/protobuf")
            
            tracer_provider = register(
                endpoint=endpoint,
                protocol=protocol,
                project_name=project_name,
                batch=True,
                verbose=False,  # Désactiver les prints verbeux
                set_global_tracer_provider=True,
            )
            
            LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
            log.info("[Phoenix] OpenInference LangChain instrumented")
            
            # NOTE IMPORTANTE : Ne pas utiliser trace_node() pour les nodes LangGraph
            # LangChainInstrumentor instrumente automatiquement :
            # - Les nodes LangGraph (chaque node devient un span)
            # - Les agents ReAct (create_react_agent crée ses propres spans)
            # - Les chaînes LangChain (chains, tools, etc.)
            # Utiliser trace_node() en plus créerait des spans redondants.
            # Le decorator trace_node() est utile uniquement pour du code Python
            # personnalisé qui n'est pas déjà instrumenté par LangChainInstrumentor.
            
        except Exception as e:
            log.warning("[Phoenix] Observability setup failed: %s", e)
    else:
        log.info("[Observability] Phoenix observability disabled (set ENABLE_PHOENIX=true to enable)")

