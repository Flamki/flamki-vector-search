# Demo Video Ready (April 19, 2026)

## Final verified platform state

- Actian image: `williamimoh/actian-vectorai-db:latest`
- Containers:
  - `vectorai-db` -> `50051`
  - `api` -> `8000`
  - `pwa` -> `5173`
- Indexed real local data:
  - `files_total=2781`
  - `text_vectors=38374`
  - `image_vectors=1923`
- Endpoints validated live:
  - `GET /health`
  - `GET /api/index/status`
  - `GET /api/search`
  - `POST /api/search/image`

## Recording rules (important)

- Record **only one main screen** (do not record full multi-monitor desktop).
- Use your **natural human voice** (no AI voiceover).
- Keep total video near **4 minutes**.
- Keep narration focused on problem -> solution -> proof.

## 4-minute on-camera script (time-boxed)

### 0:00 - 0:30 Problem statement

Say:

"People keep thousands of local files and cannot find anything later. Keyword search fails for photos, PDFs, and voice notes. We built a local-first second brain that searches by meaning, not just filename."

Show:

- PWA home screen
- search bar + offline badge visible

### 0:30 - 1:00 Actian proof + architecture

Say:

"Our retrieval backend uses Actian VectorAI DB in Docker, with separate vector collections for text and images, plus hybrid fusion and filters."

Show:

- `docker compose ps` with `vectorai-db`
- `/api/index/status` with vector counts

### 1:00 - 1:45 Text/doc search demo

Say:

"Now I search docs semantically with hybrid lexical + vector fusion."

Show:

- query: `hackathon battle plan`
- results list with file paths and snippets
- apply filter chip (`pdf` or `txt`)

### 1:45 - 2:30 Image search demo (key wow moment)

Say:

"Now image-to-image retrieval: upload one photo and get similar photos instantly from local indexed data."

Show:

- upload one photo in UI or call `POST /api/search/image`
- top image matches returned

### 2:30 - 3:10 Audio/voice note search demo

Say:

"Voice notes are transcribed and searchable like text."

Show:

- query: `be decent in my eyes`
- filter `mp3`
- returned audio chunks

### 3:10 - 3:45 Why this is technically strong

Say:

"This solution is fully local-first, uses Actian VectorAI DB as the core vector engine, supports named vectors, hybrid fusion, and filtered retrieval across modalities."

Show:

- endpoint checks passing (`python scripts/check_endpoints.py`)
- brief code glimpse: `vectorai/client.py` and `Stage_3/tools/tool_hybrid_search.py`

### 3:45 - 4:00 Close

Say:

"This is production-style multimodal retrieval with real local data at submission scale, running end-to-end in Docker."

Show:

- final UI result screen (clean)

## Safety checklist before recording

- Run `python scripts/check_endpoints.py` and confirm all pass.
- Keep browser zoom readable (100% or 110%).
- Close unrelated apps/tabs with sensitive content.
- Test microphone once before final take.
