# VidDB

VidDB is a multi-tenant, time-addressable database for video and other continuous media. It keeps media in object storage and turns transcripts, visual descriptions, events, and custom model output into searchable records tied to exact time ranges.

The project is an early-stage reference implementation built around FastAPI, PostgreSQL with pgvector, MinIO, Redis, and Temporal.

## What it does

- Registers uploaded files, object-store assets, and URLs
- Builds versioned transcript, visual, and custom indexes
- Detects coherent episodes from temporal gaps and semantic embedding changes
- Combines vector and full-text search across temporal evidence
- Filters results by tenant, collection, asset, time range, modality, and index version
- Creates virtual clips and HLS manifests without copying source media
- Supports live streams, event rules, alerts, and temporal operators
- Exposes the model configuration and evidence behind each result

## Architecture

```text
Client / Frontend
       │
   FastAPI API
       │
       ├── PostgreSQL + pgvector  metadata, time ranges, embeddings
       ├── MinIO                 source and derived media
       ├── Temporal              durable processing workflows
       └── Redis                 coordination and live workloads
```

Every derived record remains associated with its tenant, source asset or stream, time range, index version, and processing configuration.

## Quick start

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), and Docker.

```bash
uv sync
docker compose -f infra/compose.yaml up -d
uv run python -c "from apps.persistence.database import create_database_engine; from apps.persistence.migrations import run_migrations; run_migrations(create_database_engine())"
uv run uvicorn apps.api.main:app --reload
```

Open the API dashboard at [http://localhost:8000](http://localhost:8000) or the interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs).

API requests are tenant-scoped with the `X-Tenant-ID` header:

```bash
curl -X POST http://localhost:8000/collections \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-ID: demo' \
  -d '{"name":"Highlights"}'
```

Build a searchable episode-memory index from an existing transcript or visual
index. Reuse the version only with the same immutable segmentation settings:

```bash
curl -X POST http://localhost:8000/assets/ASSET_ID/episodes \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-ID: demo' \
  -d '{"source_index_id":"INDEX_ID","version":"transcript-v1"}'
```

Set `VIDEODB_API_KEY` to require an additional `X-API-Key` header. The default database connection can be overridden with `VIDEODB_DATABASE_URL`.

## Frontend

The lightweight explainability workspace can be served separately:

```bash
python -m http.server 4173 --directory frontend
```

Then open [http://localhost:4173](http://localhost:4173). It supports asset registration, temporal search, result playback, and evidence inspection. Browser multipart uploads currently show the upload contract but do not yet transfer the selected bytes.

## Development

```bash
uv run ruff check .
uv run ty check
uv run pytest -q
node --test frontend/smoke_test.mjs
```

The main packages live under `apps/`: API routes, persistence, ingestion, media workflows, indexing, search, clips, live streams, events, and temporal queries.
