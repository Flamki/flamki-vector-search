# Demo Video Readiness (April 19, 2026)

## Current verified state

- Actian image: `williamimoh/actian-vectorai-db:latest`
- Containers:
  - `vectorai-db` on `50051`
  - `api` on `8000`
  - `pwa` on `5173`
- Ingested data:
  - `151` files total
  - `18` text docs/notes
  - `130` images
  - `3` audio files
- Task status:
  - `transcribe_audio`: `DONE=3`
  - `embed_images`: `DONE=133`
  - `embed_text`: `DONE=21`
  - `index_lexical`: `DONE=21`
  - `ocr_images`: `PENDING` in Linux container (expected for Windows OCR-only service)
- VectorAI stats:
  - `text_vectors=453`
  - `image_vectors=133`

## Demo-safe query sequence (use this on camera)

1. Health + index status
   - `GET /health`
   - `GET /api/index/status`
2. Document search
   - Query: `hackathon battle plan`
   - Endpoint: `GET /api/search?q=hackathon%20battle%20plan&top_k=5`
3. Photo semantic search (text query)
   - Query: `photo of person`
   - Apply filter chip: `png`
   - Endpoint: `GET /api/search?q=photo%20of%20person&file_type=png&top_k=5`
4. Image-to-image search
   - Upload: `demo_data/photos/photo_001.png`
   - Endpoint: `POST /api/search/image?top_k=5`
5. Audio transcript search
   - Query: `hope` (or `late night` / `speaker` / `flow`)
   - Apply filter chip: `mp3` (or `wav`)
   - Endpoint examples:
     - `GET /api/search?q=hope&file_type=mp3&top_k=3`
     - `GET /api/search?q=speaker&file_type=wav&top_k=3`

## Notes for judges

- Named vectors are used with separate collections:
  - `text_vectors`
  - `image_vectors_l14_768`
- Hybrid retrieval uses lexical + semantic fusion (RRF).
- Filtered search is active (`file_type`, `after_date`).
- OCR is intentionally not shown in this containerized Linux demo because OCR service in this stack is Windows-native.

