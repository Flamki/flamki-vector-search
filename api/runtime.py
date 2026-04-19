from __future__ import annotations

import logging
import threading
from pathlib import Path

import config_manager
from Stage_2.database import Database
from Stage_3.tool_registry import ToolRegistry
from paths import ROOT_DIR
from plugin_discovery import discover_services, discover_tools
from vectorai import get_vector_store

logger = logging.getLogger("APIRuntime")


class SearchRuntime:
    """Singleton runtime that provides DB/services/tools for API routes."""

    def __init__(self):
        self.config = config_manager.load()
        self.db = Database(self.config["db_path"])
        self.services = discover_services(ROOT_DIR, self.config)
        self._service_load_attempted: set[str] = set()

        self.tool_registry = ToolRegistry(self.db, self.config, self.services)
        discover_tools(ROOT_DIR, self.tool_registry, self.config)

        self.vector_store = get_vector_store(self.config)

    def ensure_service_loaded(self, name: str):
        svc = self.services.get(name)
        if not svc:
            return None
        if svc.loaded:
            return svc
        if name in self._service_load_attempted:
            return svc if svc.loaded else None
        self._service_load_attempted.add(name)
        try:
            svc.load()
            logger.info(f"Loaded service for API runtime: {name}")
        except Exception as exc:
            logger.warning(f"Could not load service '{name}' for API runtime: {exc}")
            return None
        return svc if svc.loaded else None

    def search(self, query: str, top_k: int, file_type: str | None, after_date: str | None):
        self.ensure_service_loaded("text_embedder")
        result = self.tool_registry.call(
            "hybrid_search",
            query=query,
            max_results=top_k,
            file_type=file_type,
            after_date=after_date,
        )
        if not result.success:
            raise RuntimeError(result.error or "Hybrid search failed")
        return result.data or []

    def image_embedder(self):
        return self.ensure_service_loaded("image_embedder")

    def text_embedder(self):
        return self.ensure_service_loaded("text_embedder")

    def status(self):
        stats = self.db.get_system_stats()
        vector_stats = self.vector_store.stats()
        with self.db.lock:
            cur = self.db.conn.execute("SELECT COUNT(*) FROM files")
            total_files = int(cur.fetchone()[0])

        return {
            "files_total": total_files,
            "files_by_modality": stats.get("files", {}),
            "tasks": stats.get("tasks", {}),
            "vectorai": vector_stats,
            "db_path": str(Path(self.config["db_path"]).resolve()),
        }

    def shutdown(self):
        for service in self.services.values():
            if getattr(service, "loaded", False):
                try:
                    service.unload()
                except Exception:
                    pass


_runtime_lock = threading.Lock()
_runtime: SearchRuntime | None = None


def get_runtime() -> SearchRuntime:
    global _runtime
    if _runtime is not None:
        return _runtime
    with _runtime_lock:
        if _runtime is None:
            _runtime = SearchRuntime()
    return _runtime
