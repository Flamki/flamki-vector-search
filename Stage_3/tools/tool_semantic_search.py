"""
Semantic Search tool.

Vector similarity search across embedding streams. Uses the external
VectorAI/Postgres backend when available, and falls back to local
SQLite embedding tables when needed.
"""

import logging
import os
import time
from datetime import date, datetime, timezone

import numpy as np

from Stage_3.BaseTool import BaseTool, ToolResult
from Stage_3.SearchResult import SearchResult
from Stage_3.tools.tool_lexical_search import _search_summary
from vectorai import get_vector_store

logger = logging.getLogger("SemanticSearch")


EMBEDDING_STREAMS = {
    "text": {
        "table": "text_embeddings",
        "index_col": "chunk_index",
        "service": "text_embedder",
        "source": "text_embedding",
        "content_table": "text_chunks",
        "content_join_col": "chunk_index",
    },
    "image": {
        "table": "image_embeddings",
        "index_col": "image_index",
        "service": "image_embedder",
        "source": "image_embedding",
        "content_table": "ocr_text",
        "content_join_col": None,
    },
}

INDEX_FIELD_MAP = {
    "chunk_index": "chunk_index",
    "image_index": "image_index",
}


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
        d = date.fromisoformat(value)
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    except ValueError:
        pass

    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _after_date_timestamp(after_date: str | None) -> float | None:
    dt = _parse_after_date(after_date)
    if dt is None:
        return None
    return dt.timestamp()


class SemanticSearch(BaseTool):
    name = "semantic_search"
    agent_enabled = False
    description = (
        "Search for files by meaning using vector similarity. Embeds your "
        "query and compares it against stored embeddings (text, image, and "
        "any future modalities). Returns the most semantically similar results."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query to search for.",
            },
            "top_k": {
                "type": "integer",
                "description": "Maximum results per stream. Default 5.",
                "default": 5,
            },
            "streams": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Which embedding streams to search. Omit to search all available.",
            },
            "folder": {
                "type": "string",
                "description": "Filter results to files under this folder path.",
            },
            "file_type": {
                "type": "string",
                "description": "Filter by extension without dot (pdf, txt, jpg, etc). Use all for no filter.",
            },
            "after_date": {
                "type": "string",
                "description": "Filter by file modified date on/after YYYY-MM-DD.",
            },
        },
        "required": ["query"],
    }
    requires_services = []

    def __init__(self):
        super().__init__()
        self.vector_store = get_vector_store()

    def run(self, context, **kwargs):
        query = kwargs.get("query", "").strip()
        top_k = kwargs.get("top_k", 5)
        requested_streams = kwargs.get("streams", None)
        folder = kwargs.get("folder", None)
        file_type = _normalize_file_type(kwargs.get("file_type", None))
        after_date = kwargs.get("after_date", None)

        if not query:
            return ToolResult.failed("No query provided.")

        if requested_streams:
            stream_names = [s for s in requested_streams if s in EMBEDDING_STREAMS]
            if not stream_names:
                available = list(EMBEDDING_STREAMS.keys())
                return ToolResult.failed(f"No valid streams requested. Available: {available}")
        else:
            stream_names = list(EMBEDDING_STREAMS.keys())

        all_results = []
        for stream_name in stream_names:
            stream_results = self._search_stream(
                context=context,
                stream_name=stream_name,
                query=query,
                top_k=top_k,
                folder=folder,
                file_type=file_type,
                after_date=after_date,
            )
            all_results.extend(stream_results)

        paths = list({r["path"] for r in all_results})
        return ToolResult(
            data=all_results,
            llm_summary=_search_summary(query, all_results),
            gui_display_paths=paths,
        )

    def _search_stream(self, context, stream_name, query, top_k, folder, file_type, after_date):
        config = EMBEDDING_STREAMS[stream_name]
        service_name = config["service"]
        embedder = context.services.get(service_name)

        if not embedder or not embedder.loaded:
            logger.info(f"Skipping {stream_name} stream: {service_name} not loaded")
            return []

        try:
            query_vec = embedder.encode(query)
        except Exception as exc:
            logger.error(f"Failed to encode query for {stream_name}: {exc}")
            return []

        if query_vec is None:
            return []
        if query_vec.ndim == 2:
            query_vec = query_vec[0]

        vector_results = self._search_stream_vectorai(
            context=context,
            stream_name=stream_name,
            config=config,
            query_vec=query_vec,
            top_k=top_k,
            folder=folder,
            file_type=file_type,
            after_date=after_date,
        )
        if vector_results is not None:
            return vector_results

        # Fallback path
        return self._search_stream_sqlite(
            context=context,
            stream_name=stream_name,
            config=config,
            query_vec=query_vec,
            top_k=top_k,
            folder=folder,
            file_type=file_type,
            after_date=after_date,
        )

    def _search_stream_vectorai(self, context, stream_name, config, query_vec, top_k, folder, file_type, after_date):
        if not self.vector_store.available():
            return None

        filters = {
            "folder": folder,
            "file_type": file_type,
            "after_date": after_date,
        }

        if stream_name == "text":
            raw = self.vector_store.search_text(query_vec, top_k=top_k, filters=filters)
        else:
            raw = self.vector_store.search_images(query_vec, top_k=top_k, filters=filters)

        if raw is None:
            return None
        if not raw:
            return []

        modality_map = self._get_modalities(context.db, list({item["path"] for item in raw}))
        index_col = config["index_col"]
        index_field = INDEX_FIELD_MAP.get(index_col, index_col)

        missing_pairs = []
        for item in raw:
            if item.get("content"):
                continue
            idx_value = item.get(index_col)
            if idx_value is not None:
                missing_pairs.append((item["path"], idx_value))

        content_map = {}
        if missing_pairs:
            top_paths = [p for p, _ in missing_pairs]
            top_indices = [i for _, i in missing_pairs]
            content_map = self._fetch_content(context.db, config, top_paths, top_indices)

        results = []
        stream_tag = f"{stream_name}_semantic"
        for item in raw:
            idx_value = item.get(index_col)
            result_kwargs = {
                "path": item["path"],
                "score": float(item["score"]),
                "source": f"vectorai_{stream_name}",
                "stream": stream_tag,
                "modality": modality_map.get(item["path"], stream_name),
                "content": item.get("content") or content_map.get((item["path"], idx_value)),
                index_field: int(idx_value) if idx_value is not None else None,
            }
            results.append(SearchResult(**result_kwargs).to_dict())

        return results

    def _search_stream_sqlite(self, context, stream_name, config, query_vec, top_k, folder, file_type, after_date):
        table = config["table"]
        index_col = config["index_col"]
        source = config["source"]
        stream_tag = f"{stream_name}_semantic"
        service_name = config["service"]

        embedder = context.services.get(service_name)
        if not embedder:
            return []

        sql_parts = [
            f"SELECT e.path, e.{index_col}, e.embedding",
            f"FROM {table} e",
            "JOIN files f ON f.path = e.path",
            "WHERE e.model_name = ?",
        ]
        params = [embedder.model_name]

        if folder:
            normalized_folder = os.path.normpath(folder)
            sql_parts.append("AND e.path LIKE ? || '%'")
            params.append(normalized_folder)

        if file_type:
            sql_parts.append("AND f.extension = ?")
            params.append(f".{file_type}")

        after_ts = _after_date_timestamp(after_date)
        if after_ts is not None:
            sql_parts.append("AND f.mtime >= ?")
            params.append(after_ts)

        sql = "\n".join(sql_parts)

        try:
            with context.db.lock:
                cur = context.db.conn.execute(sql, params)
                rows = cur.fetchall()
        except Exception as exc:
            logger.error(f"Failed to load embeddings from {table}: {exc}")
            return []

        if not rows:
            return []

        paths = []
        indices = []
        valid_vecs = []

        for row in rows:
            path, idx, blob = row[0], row[1], row[2]
            if not blob:
                continue
            vec = np.frombuffer(blob, dtype=np.float32)
            if vec.shape[0] != query_vec.shape[0]:
                continue
            paths.append(path)
            indices.append(idx)
            valid_vecs.append(vec)

        if not valid_vecs:
            return []

        emb_matrix = np.vstack(valid_vecs)
        t_sim = time.time()
        scores = np.dot(emb_matrix, query_vec)
        logger.debug(
            f"SQLite semantic search over {len(valid_vecs)} vectors in {time.time() - t_sim:.3f}s"
        )

        k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[-k:][::-1]

        top_paths = [paths[i] for i in top_indices]
        top_idx_values = [indices[i] for i in top_indices]
        content_map = self._fetch_content(context.db, config, top_paths, top_idx_values)
        modality_map = self._get_modalities(context.db, list(set(top_paths)))

        index_field = INDEX_FIELD_MAP.get(index_col, index_col)
        results = []
        for i in top_indices:
            path = paths[i]
            idx_value = indices[i]
            result_kwargs = {
                "path": path,
                "score": float(scores[i]),
                "source": source,
                "stream": stream_tag,
                "modality": modality_map.get(path, "unknown"),
                "content": content_map.get((path, idx_value)),
                index_field: int(idx_value),
            }
            results.append(SearchResult(**result_kwargs).to_dict())

        return results

    def _fetch_content(self, db, stream_config, paths, indices):
        content_table = stream_config.get("content_table")
        if not content_table or not paths:
            return {}

        join_col = stream_config.get("content_join_col")

        try:
            with db.lock:
                if join_col:
                    placeholders = " OR ".join(
                        f"(path = ? AND {join_col} = ?)" for _ in paths
                    )
                    params = []
                    for p, idx in zip(paths, indices):
                        params.extend([p, idx])

                    sql = f"SELECT path, {join_col}, content FROM {content_table} WHERE {placeholders}"
                    cur = db.conn.execute(sql, params)
                    return {(row[0], row[1]): row[2] for row in cur.fetchall()}

                unique_paths = list(set(paths))
                placeholders = ", ".join("?" for _ in unique_paths)
                sql = f"SELECT path, content FROM {content_table} WHERE path IN ({placeholders})"
                cur = db.conn.execute(sql, unique_paths)
                path_content = {row[0]: row[1] for row in cur.fetchall()}
                result = {}
                for p, idx in zip(paths, indices):
                    if p in path_content:
                        result[(p, idx)] = path_content[p]
                return result

        except Exception as exc:
            logger.error(f"Content fetch from {content_table} failed: {exc}")
            return {}

    def _get_modalities(self, db, paths: list) -> dict:
        if not paths:
            return {}

        placeholders = ", ".join("?" for _ in paths)
        sql = f"SELECT path, modality FROM files WHERE path IN ({placeholders})"

        try:
            with db.lock:
                cur = db.conn.execute(sql, paths)
                return {row[0]: row[1] for row in cur.fetchall()}
        except Exception as exc:
            logger.error(f"Modality lookup failed: {exc}")
            return {}
