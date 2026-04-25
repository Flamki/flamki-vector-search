# Flamki Vector Search

**A local-first, multimodal semantic search system powered by [Actian VectorAI DB](https://www.actian.com/vectorai/).**

Flamki Vector Search turns scattered local files — documents, photos, and voice memos — into searchable knowledge by meaning, not filenames.

---

## 🎯 Problem

Every day we create dozens of files: PDFs, screenshots, photos, voice notes. Within weeks, they become digital clutter. When we urgently need something, **keyword search fails** because we don't remember exact file names — we remember *meaning* and *context*. Photos have no useful keywords. Voice notes are unsearchable. Our most valuable information becomes invisible.

## 💡 Solution

Flamki Vector Search solves this with **semantic retrieval**:

- **Search by meaning** — query with natural language, not exact filenames
- **Multimodal** — indexes text documents, images (CLIP embeddings), and audio (Whisper transcription)
- **Hybrid fusion** — combines lexical + semantic ranking via Reciprocal Rank Fusion (RRF)
- **Filtered search** — narrow by `file_type`, `after_date`, and more
- **Local-first** — your files never leave your machine. No cloud dependency
- **Offline-capable** — React PWA works without internet

---

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────────┐
│  React PWA  │────▶│   FastAPI     │────▶│  Actian VectorAI DB  │
│  (port 5173)│     │  (port 8000)  │     │  (gRPC port 50051)   │
└─────────────┘     └──────────────┘     └──────────────────────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         Text Embed  Image Embed  Audio Transcribe
        (all-MiniLM) (CLIP ViT-L) (Whisper)
```

**Three Docker containers** run the full pipeline:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `vectorai-db` | `williamimoh/actian-vectorai-db:latest` | 50051 | Vector storage + nearest-neighbor search |
| `api` | Custom FastAPI | 8000 | Ingestion, embedding, search endpoints |
| `pwa` | React + Vite | 5173 | Offline-capable search UI |

---

## ✅ Hackathon Judge Criteria

| Requirement | Implementation |
|-------------|---------------|
| **Actian VectorAI DB** | `williamimoh/actian-vectorai-db:latest` (organizer-confirmed image) |
| **Named vectors** | Separate collections: `text_vectors` (384-D) and `image_vectors_l14_768` (768-D) |
| **Hybrid fusion (RRF)** | Lexical + semantic merged in `Stage_3/tools/tool_hybrid_search.py` |
| **Filtered search** | `file_type`, `after_date` filters via VectorAI FilterBuilder |
| **Live endpoints** | `/health`, `/api/index/status`, `/api/search`, `/api/search/image` |

---

## 📊 Verified Dataset Scale

| Metric | Count |
|--------|-------|
| Total files indexed | **2,781** |
| Text vectors | **38,374** |
| Image vectors | **1,923** |
| Text files | 1,045 |
| Images | 1,600 |
| Audio files | 80 |
| Tabular files | 56 |

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/Flamki/flamki-vector-search.git
cd flamki-vector-search

# 2. Start the stack
docker compose up -d

# 3. Verify
python scripts/check_endpoints.py
```

- **PWA**: http://localhost:5173
- **API docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

---

## 🔍 API Endpoints

### `GET /health`
Returns system health status.

### `GET /api/index/status`
Returns indexed file counts, vector counts, and task progress.

### `GET /api/search?q=<query>&top_k=5&file_type=pdf`
Hybrid text search with optional filters.

**Example:**
```bash
curl "http://localhost:8000/api/search?q=hackathon%20battle%20plan&file_type=pdf&top_k=5"
```

### `POST /api/search/image?top_k=5`
Image-to-image similarity search. Upload an image file to find visually similar indexed images.

**Example:**
```bash
curl -X POST "http://localhost:8000/api/search/image?top_k=5" -F "file=@photo.png"
```

---

## 📂 Project Structure

```
├── api/                    # FastAPI search & index endpoints
├── vectorai/               # Actian VectorAI DB client wrapper
│   ├── client.py           # VectorStore: upsert, search, stats
│   └── hybrid.py           # RRF fusion logic
├── Stage_2/                # Ingestion pipeline (tasks, embeddings)
├── Stage_3/tools/          # Hybrid search tool with RRF
├── frontend/pwa/           # React PWA (offline-capable)
├── scripts/
│   ├── check_endpoints.py          # Endpoint smoke tests
│   ├── collect_large_demo_data.py  # Real data collector
│   ├── run_demo_ingest.py          # Batch ingestion runner
│   ├── demo_showcase/index.html    # Auto-advancing demo page
│   └── render_final_submission.ps1 # One-command video render
├── docker-compose.yml      # Full stack definition
├── Dockerfile.api          # API container build
└── requirements.txt        # Python dependencies
```

---

## 🎬 Demo Video

The demo video showcases:

1. **Problem statement** (0:00–0:30) — why keyword search fails for real workflows
2. **Solution + architecture** — Docker stack with Actian VectorAI DB
3. **Data scale proof** — 2,781 files, 38K+ vectors indexed
4. **Text search** — semantic document retrieval with hybrid fusion
5. **Photo search** — natural language image retrieval via CLIP
6. **Audio search** — voice note transcript retrieval
7. **Image-to-image** — visual similarity search
8. **Technical proof** — all judge criteria satisfied

---

## 🔧 Data Ingestion

```bash
# Collect real files from local machine
python scripts/collect_large_demo_data.py \
  --docs 300 --notes 800 --photos 1600 --audio 80

# Run ingestion pipeline
docker compose exec \
  -e PYTHONPATH=/app \
  -e INGEST_TIMEOUT_S=10800 \
  api python /app/scripts/run_demo_ingest.py
```

---

## ⚠️ Known Limitations

- OCR task pending in Linux containers (OCR service is Windows-native in this codebase)
- Some tabular/audio files fail parsing due to source format; core demo paths remain healthy
- `demo_data/` is git-ignored to protect personal file privacy

---

## 📄 License

Hackathon implementation. Third-party dependencies under their respective licenses.
