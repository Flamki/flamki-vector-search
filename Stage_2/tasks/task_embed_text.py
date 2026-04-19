"""
Embed Text task.

Reads chunks from the text_chunks table, pools them across all files in the
batch, and encodes them in one call to the text_embedder service. The embedder
handles sub-batching internally.

Depends on chunk_text. Requires the text_embedder service to be loaded.
"""

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from Stage_2.BaseTask import BaseTask, TaskResult
from vectorai import get_vector_store

logger = logging.getLogger("EmbedText")
vector_store = get_vector_store()


class EmbedText(BaseTask):
	name = "embed_text"
	modalities = ["text"]
	reads = ["text_chunks"]
	writes = ["text_embeddings"]
	requires_services = ["text_embedder"]
	output_schema = """
		CREATE TABLE IF NOT EXISTS text_embeddings (
			path TEXT,
			chunk_index INTEGER,
			embedding BLOB,
			model_name TEXT,
			embedded_at REAL,
			PRIMARY KEY (path, chunk_index)
		);
	"""
	batch_size = 4
	max_workers = 4
	timeout = 300

	def run(self, paths, context):
		embedder = context.services.get("text_embedder")
		if not embedder or not embedder.loaded:
			return [TaskResult.failed("text_embedder service not loaded") for _ in paths]

		now = time.time()

		# --- 1. Pool all chunks across all files ---
		pool_texts = []       # flat list of chunk strings
		pool_keys = []        # parallel list of (path, chunk_index)
		path_to_indices = {}  # path -> list of positions in pool

		for path in paths:
			try:
				rows = context.db.get_task_output("text_chunks", path)
				if not rows:
					path_to_indices[path] = []
					continue

				path_to_indices[path] = []
				for row in rows:
					idx = len(pool_texts)
					pool_texts.append(row["content"])
					pool_keys.append((path, row["chunk_index"]))
					path_to_indices[path].append(idx)
			except Exception as e:
				logger.error(f"Failed to read chunks for {Path(path).name}: {e}")
				path_to_indices[path] = None  # sentinel for failure

		# --- 2. Encode the entire pool at once ---
		# Pooling chunks across files into one encode() call is much faster
		# than encoding per-file, because the GPU can batch efficiently.
		embeddings = None
		if pool_texts:
			logger.debug(f"Encoding {len(pool_texts)} text chunks across {len(paths)} files...")
			try:
				embeddings = embedder.encode(pool_texts)
			except Exception as e:
				logger.error(f"Embedding encode failed: {e}")
				return [TaskResult.failed(f"Encode failed: {e}") for _ in paths]

			if embeddings is None:
				return [TaskResult.failed("Embedder returned None") for _ in paths]

		# --- 3. Map results back to per-file TaskResults ---
		results = []
		total_embedded = 0
		vector_rows = []

		for path in paths:
			indices = path_to_indices.get(path)

			if indices is None:
				results.append(TaskResult.failed("Failed to read chunks"))
				continue

			if not indices:
				results.append(TaskResult(success=True, data=[]))
				continue

			data = []
			path_obj = Path(path)
			file_type = path_obj.suffix.lower().lstrip(".") or "unknown"
			created_at = datetime.fromtimestamp(
				os.path.getmtime(path), tz=timezone.utc
			) if os.path.exists(path) else datetime.now(timezone.utc)

			for idx in indices:
				p, chunk_index = pool_keys[idx]
				embedding_vec = embeddings[idx]
				embedding_bytes = embedding_vec.tobytes()
				data.append({
					"path": p,
					"chunk_index": chunk_index,
					"embedding": embedding_bytes,
					"model_name": embedder.model_name,
					"embedded_at": now,
				})
				vector_rows.append({
					"id": f"{p}::text::{chunk_index}",
					"path": p,
					"file_type": file_type,
					"chunk_index": chunk_index,
					"content": pool_texts[idx],
					"created_at": created_at,
					"tags": [],
					"model_name": embedder.model_name,
					"embedding": embedding_vec,
				})

			total_embedded += len(data)
			results.append(TaskResult(success=True, data=data))

		if vector_rows:
			inserted = vector_store.upsert_text_vectors(vector_rows)
			if inserted:
				logger.info(f"Mirrored {inserted} text embeddings to VectorAI backend")

		logger.info(f"Embedded {total_embedded} chunks across {len(paths)} files")
		return results
