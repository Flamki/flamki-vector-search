# Demo Video Ready - Winning Version (April 19, 2026)

## 0) What judges should feel in 10 seconds

"This solves a real pain, works live, and is technically strong on Actian VectorAI DB."

Your video must prove three things clearly:

- Real problem with real user pain
- Real product running live
- Real Actian VectorAI DB usage with measurable retrieval quality

## 1) Recording setup (main screen only)

- Record only your primary monitor.
- Close private apps/tabs before recording.
- Keep one browser window + one terminal window.
- Keep text readable at 100% to 110% zoom.
- Use your natural voice, slightly slower than normal speaking.

## 2) 4-minute winning script (exact words + actions)

### 0:00-0:25 - Problem (pain first)

Say:

"Today our files are scattered across photos, PDFs, notes, and voice memos. Keyword search breaks because we forget exact names. In real life, people remember meaning, not filenames."

Show:

- Open PWA home page
- Search bar + offline badge visible

### 0:25-0:45 - Why existing search fails

Say:

"Traditional search only matches words. If I type a natural description, it usually misses the right file. That is the gap we solved."

Show:

- Quick example query in PWA
- Briefly show mixed file types in results area

### 0:45-1:15 - Solution and architecture

Say:

"We built Flamki Vector Search, a local-first multimodal search system powered by Actian VectorAI DB. We index text, images, and audio transcripts, then fuse lexical and semantic retrieval for robust results."

Show:

- Terminal: `docker compose ps`
- Highlight `vectorai-db` container

### 1:15-1:40 - Proof of data scale

Say:

"This is not toy data. We indexed a large real dataset from the local machine for submission-grade evaluation."

Show:

- `http://localhost:8000/api/index/status`
- Keep these numbers visible:
  - `files_total=2781`
  - `text_vectors=38374`
  - `image_vectors=1923`

### 1:40-2:20 - Text search demo (hybrid + filters)

Say:

"Now I run a semantic document query. Results are fused from lexical and vector signals, and filters keep retrieval controllable."

Show:

- Query: `hackathon battle plan`
- Apply a filter chip (`pdf` or `txt`)
- Open one strong result snippet

### 2:20-2:55 - Image similarity demo (wow moment)

Say:

"Now image-to-image retrieval. I upload one image, and the system returns visually similar local images immediately."

Show:

- Use `/api/search/image` flow
- Show top 5 matched image results

### 2:55-3:25 - Audio/voice-note demo

Say:

"Voice notes are transcribed and searchable as text, so spoken content becomes discoverable."

Show:

- Query: `be decent in my eyes`
- Filter: `mp3`
- Show returned audio chunks

### 3:25-3:45 - Why this is technically strong

Say:

"Our implementation uses Actian VectorAI DB with named vectors, hybrid fusion using RRF, and filtered search. This is an end-to-end production-style retrieval pipeline, not a mock."

Show:

- `vectorai/client.py`
- `Stage_3/tools/tool_hybrid_search.py`

### 3:45-4:00 - Strong close

Say:

"Flamki Vector Search turns messy local files into searchable knowledge by meaning. It is local-first, multimodal, and fully powered by Actian VectorAI DB."

Show:

- Final clean result screen

## 3) Voice delivery guide (human, confident)

- Pace: 135 to 150 words per minute
- Tone: calm, practical, confident
- Pause 0.5 seconds after every key claim
- Stress these words: "local-first", "Actian VectorAI DB", "real data", "hybrid fusion", "multimodal"
- Avoid sounding memorized: keep sentence endings natural, not robotic

## 4) If something fails live (safe fallback lines)

If image upload is slow:

"The image endpoint is live; to save time I will continue with text and audio proof."

If one query is weak:

"Let me run a second query from the same indexed set."

If UI lags:

"Backend is still running live; I will validate directly on the API endpoint."

## 5) Final pre-record checklist

Run these before pressing Record:

```bash
python scripts/check_endpoints.py
```

Expected: "All endpoint checks passed."

Then confirm:

- `docker compose ps` shows all 3 services up
- PWA is open on one main screen only
- microphone level is clear (no clipping)

## 6) Submission-safe claims you can make

- "Organizer-confirmed Actian image in Docker Compose"
- "Named vectors for text and image collections"
- "Hybrid fusion (RRF) implemented"
- "Filtered search available (`file_type`, `after_date`)"
- "Live endpoints validated on local stack"
