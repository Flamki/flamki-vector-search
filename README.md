# Flamki Vector Search

Flamki Vector Search is a local-first multimodal search platform built for the Actian VectorAI DB hackathon. It indexes documents, notes, images, and voice notes, then serves hybrid retrieval through a FastAPI backend and React PWA frontend.

## Project ownership

- Maintainer: **Flamki**
- GitHub owner: `Flamki`
- Public-facing project name: **Flamki Vector Search**

## Hackathon criteria coverage

- **Actian VectorAI DB usage**: `williamimoh/actian-vectorai-db:latest` (confirmed by organizer for judging)
- **Named vectors**: separate collections for `text_vectors` and `image_vectors_l14_768`
- **Hybrid fusion (RRF)**: lexical BM25 + semantic vectors fused in `Stage_3/tools/tool_hybrid_search.py`
- **Filtered search**: `file_type` and `after_date` filters supported across search paths

## What is implemented

- VectorAI integration module with collection lifecycle + upsert/search
- Stage-2 ingestion pipeline with audio transcription task (`task_transcribe_audio.py`)
- FastAPI endpoints:
  - `GET /health`
  - `GET /api/index/status`
  - `GET /api/search`
  - `POST /api/search/image`
- React PWA:
  - offline badge
  - search bar
  - filter chips
  - result grid
- Docker stack:
  - `vectorai-db` on `50051`
  - `api` on `8000`
  - `pwa` on `5173`

## Quick start

```bash
docker compose up -d
```

API docs: `http://localhost:8000/docs`  
PWA: `http://localhost:5173`

## Demo data ingestion

1. Put your local files in these folders:
   - `demo_data/docs`
   - `demo_data/notes`
   - `demo_data/photos`
   - `demo_data/audio`
2. Run ingest:

```bash
docker compose exec api python scripts/run_demo_ingest.py
```

3. Re-run selective tasks after new files:

```bash
docker compose exec api sh -lc "RESET_TASKS=transcribe_audio,embed_images python scripts/run_demo_ingest.py"
```

## Endpoint smoke checks

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/api/index/status"
curl "http://localhost:8000/api/search?q=hackathon%20plan&top_k=5"
```

Image search test:

```bash
curl -X POST "http://localhost:8000/api/search/image?top_k=5" \
  -F "file=@demo_data/photos/photo_001.png"
```

## Demo notes

- Linux containers may keep `ocr_images` pending because OCR service is Windows-native.
- Text, image, and audio transcript search are fully demo-safe.
- Keep demo queries focused on indexed files for consistent live results.

## Key files

- API: `api/`
- PWA: `frontend/pwa/`
- Ingestion orchestration: `Stage_2/orchestrator.py`
- Audio transcription task: `Stage_2/tasks/task_transcribe_audio.py`
- Search tools: `Stage_3/tools/`
- VectorAI client layer: `vectorai/`

## License

This repository contains hackathon implementation code and references third-party dependencies per their respective licenses.
