# demo_data

This folder is intentionally excluded from git for privacy.

Place your own files in these subfolders before running ingestion:

- `demo_data/docs`
- `demo_data/notes`
- `demo_data/photos`
- `demo_data/audio`

Then run:

```bash
docker compose exec api python scripts/run_demo_ingest.py
```

Do not commit personal PDFs, photos, voice notes, or manifests with absolute local paths.
