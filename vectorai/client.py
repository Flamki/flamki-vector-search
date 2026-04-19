from __future__ import annotations

import logging
import os
import threading
import uuid
from datetime import date, datetime, timezone
from typing import Any

import numpy as np

try:
    from actian_vectorai import (
        Distance,
        Field,
        FilterBuilder,
        PointStruct,
        VectorAIClient,
        VectorParams,
    )
except ImportError:  # pragma: no cover - optional runtime dependency
    Distance = None
    Field = None
    FilterBuilder = None
    PointStruct = None
    VectorAIClient = None
    VectorParams = None

logger = logging.getLogger("VectorAI")


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _normalize_file_type(file_type: str | None) -> str | None:
    if not file_type:
        return None
    ft = file_type.strip().lower()
    if not ft or ft == "all":
        return None
    return ft[1:] if ft.startswith(".") else ft


def _parse_after_date(after_date: str | None) -> datetime | None:
    if not after_date:
        return None
    value = after_date.strip()
    if not value:
        return None

    try:
        parsed = date.fromisoformat(value)
        return datetime(parsed.year, parsed.month, parsed.day, tzinfo=timezone.utc)
    except ValueError:
        pass

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        logger.warning(f"Invalid after_date filter: {after_date!r}")
        return None


def _coerce_count(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        for key in ("count", "total", "value"):
            if key in value:
                try:
                    return int(value[key])
                except Exception:
                    pass
    for attr in ("count", "total", "value"):
        if hasattr(value, attr):
            try:
                return int(getattr(value, attr))
            except Exception:
                pass
    try:
        return int(value)
    except Exception:
        return 0


def _result_field(result: Any, name: str, default: Any = None):
    if hasattr(result, name):
        return getattr(result, name)
    if isinstance(result, dict):
        return result.get(name, default)
    return default


class VectorStore:
    """Actian VectorAI DB wrapper with graceful fallback behavior."""

    TEXT_COLLECTION = "text_vectors"
    # clip-ViT-L-14 embeddings are 768-D in this codebase.
    IMAGE_COLLECTION = "image_vectors_l14_768"
    TEXT_DIM = 384
    IMAGE_DIM = 768

    def __init__(self, config: dict | None = None):
        cfg = config or {}
        self.enabled = _as_bool(
            os.getenv("VECTORAI_ENABLED", cfg.get("vectorai_enabled", "true")),
            default=True,
        )
        self.strict = _as_bool(
            os.getenv("VECTORAI_STRICT", cfg.get("vectorai_strict", "false")),
            default=False,
        )

        self.host = os.getenv("VECTORAI_HOST", cfg.get("vectorai_host", "127.0.0.1"))
        env_port = os.getenv("VECTORAI_PORT")
        if env_port is not None:
            self.port = int(env_port)
        else:
            cfg_port = str(cfg.get("vectorai_port", "50051"))
            # Auto-migrate legacy postgres-style config to VectorAI gRPC default.
            if cfg_port == "5432":
                cfg_port = "50051"
            self.port = int(cfg_port)
        self.endpoint = f"{self.host}:{self.port}"

        self._lock = threading.Lock()
        self._initialized_collections = False
        self._warned_unavailable = False

    def _warn_once(self, message: str):
        if not self._warned_unavailable:
            logger.warning(message)
            self._warned_unavailable = True

    @staticmethod
    def _is_missing_collection_error(exc: Exception) -> bool:
        msg = str(exc).lower()
        return "collection" in msg and "does not exist" in msg

    def _with_client(self):
        if not self.enabled:
            return None
        if VectorAIClient is None:
            self._warn_once("actian_vectorai client package not installed. VectorAI integration disabled.")
            return None

        try:
            return VectorAIClient(self.endpoint)
        except Exception as exc:
            msg = f"Could not create VectorAI client for {self.endpoint}: {exc}"
            if self.strict:
                raise RuntimeError(msg) from exc
            self._warn_once(msg)
            return None

    def available(self) -> bool:
        client = self._with_client()
        if client is None:
            return False
        try:
            with client as c:
                c.health_check()
                self._ensure_collections(c)
            return True
        except Exception as exc:
            if self.strict:
                raise
            self._warn_once(f"Could not connect to VectorAI backend at {self.endpoint}: {exc}")
            return False

    def _ensure_collections(self, client):
        if self._initialized_collections:
            return

        with self._lock:
            if self._initialized_collections:
                return

            existing = set(client.collections.list() or [])

            if self.TEXT_COLLECTION not in existing:
                client.collections.create(
                    self.TEXT_COLLECTION,
                    vectors_config=VectorParams(size=self.TEXT_DIM, distance=Distance.Cosine),
                )

            if self.IMAGE_COLLECTION not in existing:
                client.collections.create(
                    self.IMAGE_COLLECTION,
                    vectors_config=VectorParams(size=self.IMAGE_DIM, distance=Distance.Cosine),
                )

            self._initialized_collections = True

    @staticmethod
    def _as_vector_list(embedding: Any) -> list[float]:
        vec = np.asarray(embedding, dtype=np.float32).reshape(-1)
        return [float(x) for x in vec]

    @staticmethod
    def _as_dt(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        if isinstance(value, str):
            parsed = _parse_after_date(value)
            if parsed:
                return parsed
        return None

    @staticmethod
    def _id_to_uuid(id_value: Any) -> str:
        raw = str(id_value)
        return str(uuid.uuid5(uuid.NAMESPACE_URL, raw))

    def _point_payload(
        self,
        row: dict,
        file_type_default: str,
        index_key: str,
    ) -> tuple[str, list[float], dict]:
        created_at = self._as_dt(row.get("created_at"))
        created_at_ts = created_at.timestamp() if created_at else None

        payload = {
            "row_id": str(row.get("id", "")),
            "path": row.get("path"),
            "file_type": _normalize_file_type(row.get("file_type")) or file_type_default,
            index_key: int(row.get(index_key, 0)),
            "content": row.get("content"),
            "tags": row.get("tags") or [],
            "model_name": row.get("model_name"),
            "created_at": created_at.isoformat() if created_at else None,
            "created_at_ts": created_at_ts,
        }
        point_id = self._id_to_uuid(row.get("id"))
        vector = self._as_vector_list(row["embedding"])
        return point_id, vector, payload

    def upsert_text_vectors(self, rows: list[dict]) -> int:
        if not rows:
            return 0

        points = []
        for row in rows:
            point_id, vector, payload = self._point_payload(row, "unknown", "chunk_index")
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))

        for attempt in range(2):
            try:
                client = self._with_client()
                if client is None:
                    return 0
                with client as c:
                    self._ensure_collections(c)
                    c.points.upsert(self.TEXT_COLLECTION, points)
                    return len(points)
            except Exception as exc:
                if attempt == 0 and self._is_missing_collection_error(exc):
                    # VectorAI may restart and lose collections while this process still
                    # believes they exist. Force re-initialize and retry once.
                    self._initialized_collections = False
                    logger.warning(
                        f"Text collection missing on upsert, reinitializing and retrying: {exc}"
                    )
                    continue
                if self.strict:
                    raise
                logger.warning(f"Text vector upsert failed: {exc}")
                return 0

        return 0

    def upsert_image_vectors(self, rows: list[dict]) -> int:
        if not rows:
            return 0

        points = []
        for row in rows:
            point_id, vector, payload = self._point_payload(row, "image", "image_index")
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))

        for attempt in range(2):
            try:
                client = self._with_client()
                if client is None:
                    return 0
                with client as c:
                    self._ensure_collections(c)
                    c.points.upsert(self.IMAGE_COLLECTION, points)
                    return len(points)
            except Exception as exc:
                if attempt == 0 and self._is_missing_collection_error(exc):
                    self._initialized_collections = False
                    logger.warning(
                        f"Image collection missing on upsert, reinitializing and retrying: {exc}"
                    )
                    continue
                if self.strict:
                    raise
                logger.warning(f"Image vector upsert failed: {exc}")
                return 0

        return 0

    def _build_filter(self, filters: dict | None):
        if not filters or FilterBuilder is None or Field is None:
            return None

        f = filters or {}
        file_type = _normalize_file_type(f.get("file_type"))
        after_date = _parse_after_date(f.get("after_date"))

        builder = FilterBuilder()
        has_any = False

        if file_type:
            builder.must(Field("file_type").eq(file_type))
            has_any = True

        if after_date:
            builder.must(Field("created_at_ts").gte(float(after_date.timestamp())))
            has_any = True

        if not has_any:
            return None
        return builder.build()

    def _post_filter(self, rows: list[dict], filters: dict | None) -> list[dict]:
        if not filters:
            return rows

        folder = filters.get("folder")
        path_prefix = filters.get("path_prefix")
        out = rows

        if folder:
            normalized_folder = os.path.normpath(folder)
            out = [r for r in out if str(r.get("path", "")).startswith(normalized_folder)]

        if path_prefix:
            out = [r for r in out if str(r.get("path", "")).startswith(path_prefix)]

        return out

    def search_text(self, query_vector: Any, top_k: int = 20, filters: dict | None = None) -> list[dict]:
        return self._search_collection(
            collection=self.TEXT_COLLECTION,
            stream_name="text_semantic",
            query_vector=query_vector,
            top_k=top_k,
            filters=filters,
            modality="text",
            index_key="chunk_index",
        )

    def search_images(self, query_vector: Any, top_k: int = 20, filters: dict | None = None) -> list[dict]:
        return self._search_collection(
            collection=self.IMAGE_COLLECTION,
            stream_name="image_semantic",
            query_vector=query_vector,
            top_k=top_k,
            filters=filters,
            modality="image",
            index_key="image_index",
        )

    def _search_collection(
        self,
        collection: str,
        stream_name: str,
        query_vector: Any,
        top_k: int,
        filters: dict | None,
        modality: str,
        index_key: str,
    ) -> list[dict]:
        vector = self._as_vector_list(query_vector)
        if not vector:
            return []

        request_limit = max(top_k * 5, top_k)
        query_filter = self._build_filter(filters)

        for attempt in range(2):
            try:
                client = self._with_client()
                if client is None:
                    return []
                with client as c:
                    self._ensure_collections(c)
                    results = c.points.search(
                        collection,
                        vector=vector,
                        limit=request_limit,
                        filter=query_filter,
                    )
                break
            except Exception as exc:
                if attempt == 0 and self._is_missing_collection_error(exc):
                    self._initialized_collections = False
                    logger.warning(
                        f"Collection '{collection}' missing on search, reinitializing and retrying: {exc}"
                    )
                    continue
                if self.strict:
                    raise
                logger.warning(f"Vector search failed for collection '{collection}': {exc}")
                return []

        rows: list[dict] = []
        for result in results or []:
            payload = _result_field(result, "payload", {}) or {}
            path = payload.get("path")
            if not path:
                continue

            score = _result_field(result, "score", 0.0)
            score = float(score) if score is not None else 0.0

            row = {
                "id": _result_field(result, "id"),
                "path": path,
                "score": score,
                "stream": stream_name,
                "source": "vectorai",
                "modality": modality,
                "content": payload.get("content"),
                "chunk_index": payload.get("chunk_index"),
                "image_index": payload.get("image_index"),
                "metadata": {
                    "file_type": payload.get("file_type"),
                    "created_at": payload.get("created_at"),
                    "tags": payload.get("tags") or [],
                    "model_name": payload.get("model_name"),
                },
            }

            if index_key in payload:
                row[index_key] = payload.get(index_key)

            rows.append(row)

        rows = self._post_filter(rows, filters)
        rows.sort(key=lambda item: item["score"], reverse=True)
        return rows[:top_k]

    def stats(self) -> dict[str, Any]:
        for attempt in range(2):
            try:
                client = self._with_client()
                if client is None:
                    return {"available": False, "text_vectors": 0, "image_vectors": 0}
                with client as c:
                    self._ensure_collections(c)
                    text_count = _coerce_count(c.points.count(self.TEXT_COLLECTION))
                    image_count = _coerce_count(c.points.count(self.IMAGE_COLLECTION))
                return {"available": True, "text_vectors": text_count, "image_vectors": image_count}
            except Exception as exc:
                if attempt == 0 and self._is_missing_collection_error(exc):
                    self._initialized_collections = False
                    logger.warning(
                        f"VectorAI stats encountered missing collection, reinitializing and retrying: {exc}"
                    )
                    continue
                logger.warning(f"Failed to fetch VectorAI stats: {exc}")
                return {"available": False, "text_vectors": 0, "image_vectors": 0}

        return {"available": False, "text_vectors": 0, "image_vectors": 0}


_store_lock = threading.Lock()
_store_instance: VectorStore | None = None


def get_vector_store(config: dict | None = None) -> VectorStore:
    global _store_instance
    if _store_instance is not None:
        return _store_instance
    with _store_lock:
        if _store_instance is None:
            _store_instance = VectorStore(config=config)
    return _store_instance
