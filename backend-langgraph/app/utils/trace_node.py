from __future__ import annotations
import functools
import json
import os
from typing import Any, Callable, Awaitable, Dict

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Mode d'émission pour les nœuds:
#  - "events" (défaut) : ajoute des events sur le span courant (aucune nouvelle ligne node:* dans Phoenix)
#  - "span"            : recrée un span par nœud (ancien comportement)
_MODE = (os.getenv("PHOENIX_NODE_TRACE_MODE") or "events").lower().strip()

_tracer = trace.get_tracer("sfd-clm.nodes")


def _safe_json(obj: Any, limit: int = 12_000) -> str:
    """
    Sérialisation compacte et bornée (évite d'inonder Phoenix).
    """
    try:
        txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        txt = str(obj)
    if len(txt) > limit:
        return txt[:limit] + "…[truncated]"
    return txt


def _summ_state(state: Any) -> Dict[str, Any]:
    """
    Résumé 'pre/post' lisible dans Phoenix.
    On évite les payloads volumineux (images b64, etc.).
    """
    get = (state.get if isinstance(state, dict) else getattr)

    def _val(name: str, default=None):
        try:
            return get(name, default) if get is state.get else getattr(state, name, default)
        except Exception:
            return default

    # documents: compte, types et pages (pas de contenu)
    docs = _val("documents", []) or []
    doc_types = []
    pages = 0
    for d in docs:
        try:
            t = getattr(d, "type", None) or (d.get("type") if isinstance(d, dict) else None)
            doc_types.append(t or "autre")
            p = getattr(d, "pages", None) or (d.get("pages") if isinstance(d, dict) else [])
            pages += len(p or [])
        except Exception:
            pass

    # extracted_data
    extracted_data = _val("extracted_data", {}) or {}
    if not isinstance(extracted_data, dict):
        try:
            extracted_data = {}
        except Exception:
            extracted_data = {}

    # messages: seulement le compte + rôles (si dispo)
    messages = _val("messages", []) or []
    roles = []
    for m in messages[:6]:
        try:
            r = getattr(m, "type", None) or m.__class__.__name__.lower()
            roles.append(r)
        except Exception:
            roles.append("msg")
    if len(messages) > 6:
        roles.append(f"+{len(messages)-6} more")

    out = {
        "record_id": _val("record_id"),
        "session_id": _val("session_id"),
        "messages": {"count": len(messages), "head_roles": roles},
        "documents": {"count": len(docs), "types": doc_types, "pages": pages},
        "extracted_data": {"count": len(extracted_data) if isinstance(extracted_data, dict) else 0},
        "fields_dictionary": {"count": len(_val("fields_dictionary", {}))},
        "ocr_text_length": len(_val("ocr_text", "") or ""),
        "text_blocks_count": len(_val("text_blocks", []) or []),
        "quality_score": _val("quality_score"),
        "remaining_steps": _val("remaining_steps"),
    }
    return out


def trace_node(name: str) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    Observabilité des nœuds LangGraph.

    - MODE 'events' (défaut): n'émet PAS de span → ajoute seulement des events
      "node:<name>:pre/post" sur le span courant (donc pas de lignes `node:*` dans Phoenix).
    - MODE 'span': crée un span pour chaque nœud, avec input/output en attributs.
    """
    def deco(fn: Callable[..., Awaitable[Any]]):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            state = args[0] if args else None

            # ---------------------------
            # MODE EVENTS (par défaut)
            # ---------------------------
            if _MODE != "span":
                current = trace.get_current_span()
                # pre
                try:
                    current.add_event(
                        f"node:{name}:pre",
                        {"state": _safe_json(_summ_state(state))}
                    )
                except Exception:
                    pass

                try:
                    result = await fn(*args, **kwargs)
                except BaseException as e:
                    # Exceptions de contrôle de flux LangGraph: ne pas marquer en ERROR
                    ename = e.__class__.__name__
                    msg = str(e)
                    is_control_flow = ("ParentCommand" in ename) or ("ParentCommand" in msg) or ("Command(" in msg)
                    if is_control_flow:
                        try:
                            current.add_event(
                                f"node:{name}:control_flow",
                                {"detail": (msg[:500] + "…") if len(msg) > 500 else msg}
                            )
                        except Exception:
                            pass
                        raise
                    # Vraie erreur
                    try:
                        current.record_exception(e)
                        current.set_status(Status(StatusCode.ERROR, description=msg[:500]))
                    except Exception:
                        pass
                    raise
                else:
                    # post
                    try:
                        current.add_event(
                            f"node:{name}:post",
                            {"state": _safe_json(_summ_state(result))}
                        )
                    except Exception:
                        pass
                    return result

            # ---------------------------
            # MODE SPAN (optionnel)
            # ---------------------------
            with _tracer.start_as_current_span(f"node:{name}") as span:
                # métadonnées légères & IO
                try:
                    record_id = getattr(state, "record_id", None) or (state.get("record_id") if isinstance(state, dict) else None)
                    session_id = getattr(state, "session_id", None) or (state.get("session_id") if isinstance(state, dict) else None)
                    if record_id:
                        span.set_attribute("record.id", str(record_id))
                    if session_id:
                        span.set_attribute("session.id", str(session_id))
                    # Aide à l'affichage Phoenix
                    span.set_attribute("openinference.span.kind", "CHAIN")
                    span.set_attribute("openinference.node.name", name)
                    span.set_attribute("openinference.input", _safe_json(_summ_state(state)))
                except Exception:
                    pass

                try:
                    result = await fn(*args, **kwargs)
                except BaseException as e:
                    ename = e.__class__.__name__
                    msg = str(e)
                    is_control_flow = ("ParentCommand" in ename) or ("ParentCommand" in msg) or ("Command(" in msg)
                    if is_control_flow:
                        span.add_event(
                            "langgraph.control_flow",
                            {"detail": (msg[:500] + "…") if len(msg) > 500 else msg}
                        )
                        raise
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, description=msg[:500]))
                    raise
                else:
                    try:
                        span.set_attribute("openinference.output", _safe_json(_summ_state(result)))
                    except Exception:
                        pass
                    return result

        return wrapper
    return deco

