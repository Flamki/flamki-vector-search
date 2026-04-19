from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from PIL import Image

from api.runtime import get_runtime

router = APIRouter(prefix="/api", tags=["search"])


def _normalize_file_type(file_type: Optional[str]) -> Optional[str]:
    if not file_type:
        return None
    value = file_type.strip().lower()
    if not value or value == "all":
        return None
    return value[1:] if value.startswith(".") else value


def _result_to_api_item(item: dict) -> dict:
    path = item.get("path", "")
    path_obj = Path(path)
    chunk_index = item.get("chunk_index")
    image_index = item.get("image_index")

    stable_suffix = (
        f"chunk:{chunk_index}" if chunk_index is not None
        else f"image:{image_index}" if image_index is not None
        else "doc"
    )
    stable_id = f"{path}:{stable_suffix}"

    meta = {
        "id": stable_id,
        "path": path,
        "file_name": path_obj.name,
        "file_type": path_obj.suffix.lower().lstrip("."),
        "modality": item.get("modality"),
        "source": item.get("source"),
        "stream": item.get("stream"),
        "chunk_index": chunk_index,
        "image_index": image_index,
        "content": item.get("content"),
    }
    return {
        "id": stable_id,
        "score": float(item.get("score", 0.0)),
        "meta": meta,
    }


@router.get("/search")
async def search(
    q: str = Query(..., description="Search query"),
    file_type: Optional[str] = Query(None, description="pdf/image/audio/txt/all"),
    after_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    top_k: int = Query(10, ge=1, le=100, description="Number of results"),
):
    runtime = get_runtime()
    try:
        raw = runtime.search(
            query=q,
            top_k=top_k,
            file_type=_normalize_file_type(file_type),
            after_date=after_date,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    items = [_result_to_api_item(item) for item in raw]
    return {
        "query": q,
        "file_type": file_type or "all",
        "after_date": after_date,
        "count": len(items),
        "results": items,
    }


@router.post("/search/image")
async def search_by_image(
    file: UploadFile = File(...),
    top_k: int = Query(10, ge=1, le=100),
    file_type: Optional[str] = Query(None, description="Filter result extension"),
    after_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
):
    runtime = get_runtime()
    vector_store = runtime.vector_store
    if not vector_store.available():
        raise HTTPException(
            status_code=503,
            detail="VectorAI backend not available for image similarity search.",
        )

    image_embedder = runtime.image_embedder()
    if image_embedder is None or not image_embedder.loaded:
        raise HTTPException(status_code=503, detail="Image embedder is not loaded.")

    suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        pil_img = Image.open(tmp_path).convert("RGB")
        emb = None
        try:
            emb = image_embedder.encode([pil_img])
        except Exception:
            # Fallback for CLIP-style models that expect paths
            emb = image_embedder.encode([tmp_path])

        emb = np.asarray(emb, dtype=np.float32)
        if emb.ndim == 2:
            emb = emb[0]

        raw = vector_store.search_images(
            emb,
            top_k=top_k,
            filters={
                "file_type": _normalize_file_type(file_type),
                "after_date": after_date,
            },
        )
        items = [_result_to_api_item(item) for item in raw]
        return {"count": len(items), "results": items}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Image search failed: {exc}") from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
