# Flamki Vector Search

Flamki Vector Search is a local-first multimodal search system built on **Actian VectorAI DB** for hackathon submission. It indexes documents, notes, images, and voice/audio files and serves hybrid retrieval through FastAPI + React PWA.

## Judge criteria coverage

- **Actian VectorAI DB image**: `williamimoh/actian-vectorai-db:latest` (organizer-confirmed)
- **Named vectors**: separate collections for text and image vectors
- **Hybrid fusion (RRF)**: lexical + semantic merged in `Stage_3/tools/tool_hybrid_search.py`
- **Filtered search**: `file_type`, `after_date`

## What is shipped

- VectorAI client module with collection lifecycle + upsert/search
- FastAPI endpoints:
  - `GET /health`
  - `GET /api/index/status`
  - `GET /api/search`
  - `POST /api/search/image`
- React PWA with:
  - offline badge
  - search bar
  - filter chips
  - result grid
- Docker stack:
  - `vectorai-db` on `50051`
  - `api` on `8000`
  - `pwa` on `5173`

## Latest verified run (April 19, 2026)

- `files_total=2781`
- Modalities:
  - `text=1045`
  - `image=1600`
  - `audio=80`
  - `tabular=56`
- VectorAI counts:
  - `text_vectors=38374`
  - `image_vectors=1923`
- Endpoint checks: passing (`health`, `status`, text search, image search POST, audio query)

## Quick start

```bash
docker compose up -d
```

- API docs: `http://localhost:8000/docs`
- PWA: `http://localhost:5173`

## Ingest large real local data

1. Pull real files from your laptop folders into `demo_data/*`:

```bash
python scripts/collect_large_demo_data.py --docs 300 --notes 800 --photos 1600 --audio 80 --max-file-mb 80
```

2. Run ingestion:

```bash
docker compose exec -e PYTHONPATH=/app -e INGEST_TIMEOUT_S=10800 api python /app/scripts/run_demo_ingest.py
```

3. If semantic vectors need a fresh mirror, rerun embed tasks only:

```bash
docker compose exec -e PYTHONPATH=/app -e INGEST_TIMEOUT_S=14400 -e RESET_TASKS=embed_text,embed_images api python /app/scripts/run_demo_ingest.py
```

## Endpoint smoke checks

```bash
python scripts/check_endpoints.py
```

## Demo recording guides

- Main script + timing: `DEMO_VIDEO_READY.md`
- Full technical handoff: `PROJECT_HANDOFF_REPORT.md`

## Notes

- OCR task is pending in Linux containers because OCR service in this codebase is Windows-only.
- `demo_data/**` is ignored in git by design (privacy-safe public repo publishing).

## License

Hackathon implementation with third-party dependencies under their respective licenses.
