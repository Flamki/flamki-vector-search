from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config_manager  # noqa: E402
from vectorai import get_vector_store  # noqa: E402


def main():
    config = config_manager.load()
    store = get_vector_store(config)
    if not store.available():
        print("VectorAI backend unavailable. Start docker compose first.")
        return

    dim = 384
    chunks = [
        ("demo_0", "invoice march 2026"),
        ("demo_1", "sunset beach photo"),
        ("demo_2", "machine learning meeting notes"),
    ]

    rng = np.random.default_rng(42)
    rows = []
    for idx, (doc_id, text) in enumerate(chunks):
        vec = rng.normal(size=dim).astype(np.float32)
        vec /= np.linalg.norm(vec)
        rows.append({
            "id": doc_id,
            "path": f"C:/demo/{doc_id}.txt",
            "file_type": "txt",
            "chunk_index": idx,
            "content": text,
            "created_at": "2026-04-16",
            "tags": ["demo"],
            "model_name": "debug",
            "embedding": vec,
        })

    store.upsert_text_vectors(rows)

    query = rows[1]["embedding"]
    results = store.search_text(query, top_k=3, filters={"file_type": "txt"})
    print("Top results:")
    for item in results:
        print(f"- {item['id']} score={item['score']:.4f} path={item['path']}")


if __name__ == "__main__":
    main()
