"""Shared template storage - singleton indexé par record_id for template info (Claim case)."""
from __future__ import annotations
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class SharedTemplateStorage:
    """
    Singleton in-memory storage for template info (form_json, documents_classified, ocr_consolidated, etc.)
    indexed by record_id. Thread-safe. Optional TTL for cleanup.
    """

    _instance: Optional["SharedTemplateStorage"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "SharedTemplateStorage":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._access_lock = threading.Lock()
        self._initialized = True

    def get_template_info(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Récupère le template info pour un record_id (retourne None si absent)."""
        with self._access_lock:
            return self._storage.get(record_id)

    def set_template_info(self, record_id: str, template_info: Dict[str, Any]) -> None:
        """Stocke ou met à jour le template info pour un record_id."""
        now = datetime.now(timezone.utc).isoformat()
        with self._access_lock:
            existing = self._storage.get(record_id)
            created_at = existing.get("created_at", now) if existing else now
            self._storage[record_id] = {
                **template_info,
                "last_updated": now,
                "created_at": created_at,
            }

    def has_template_info(self, record_id: str) -> bool:
        """Vérifie si un template info existe pour un record_id."""
        with self._access_lock:
            return record_id in self._storage

    def clear_template_info(self, record_id: str) -> None:
        """Supprime le template info pour un record_id (cleanup)."""
        with self._access_lock:
            self._storage.pop(record_id, None)
