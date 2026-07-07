# VideoDB Implementation Plan

## 1. Objective

Build a multi-tenant, multimodal, time-indexed media database that can:

- ingest uploaded or URL-imported video;
- normalize it into streamable media;
- generate timestamped transcript and visual indexes;
- search within an asset or collection;
- return grounded, playable evidence;
- compile results into virtual HLS clips;
- later extend to live streams, alerts, and temporal queries.

The core invariant is:

> Media bytes live in object storage. Every derived interpretation is versioned, time-addressable, and traceable to its source.

## 2. Delivery Strategy

Implement the system in four phases. Each phase must be usable independently and leave the system in a deployable state.

1. Archive ingestion and search MVP
2. Domain-specific and custom indexes
3. Live-stream indexing and alerts
4. Temporal query engine

Do not introduce separate Kafka, OpenSearch, ClickHouse, or vector-database clusters until measured load requires them.

## 3. Initial Technical Stack

| Area | Initial choice |
| --- | --- |
| API | Python, FastAPI, Pydantic |
| Metadata | PostgreSQL |
| Vector search | pgvector |
| Object storage | S3-compatible storage; MinIO locally |
| Workflow execution | Temporal |
| Cache and rate limits | Redis |
| Media processing | FFmpeg and ffprobe |
| Playback | CMAF/HLS manifests |
| Local orchestration | Docker Compose |
| Observability | OpenTelemetry, Prometheus-compatible metrics, structured logs |

Model providers must sit behind internal interfaces so ASR, embedding, OCR, and visual-language models can be replaced without changing API or storage contracts.

## 4. Proposed Repository Structure

```text
.
├── apps/
│   ├── api/                  # REST API, authentication, request validation
│   └── worker/               # Temporal worker entry point
├── packages/
│   ├── domain/               # Entities, states, temporal primitives
│   ├── db/                   # SQL models, migrations, repositories
│   ├── storage/              # Object-store abstraction
│   ├── media/                # ffprobe, FFmpeg, HLS/CMAF utilities
│   ├── workflows/            # Durable ingestion/indexing workflows
│   ├── models/               # ASR/VLM/OCR/embedding provider interfaces
│   ├── indexing/             # Index builders and versioning
│   ├── search/               # Retrieval, fusion, reranking
│   └── playback/             # Virtual clips and manifest generation
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── infra/
│   ├── docker/
│   └── compose.yaml
├── docs/
└── plan.md
```

## 5. Core Domain Model

Create these first-class entities:

- `Tenant`
- `Collection`
- `MediaAsset`
- `Rendition`
- `MediaSegment`
- `Index`
- `TemporalRecord`
- `SearchResult`
- `VirtualClip`
- `Job`

Add `RTStream`, `LiveSegment`, `Event`, and `Alert` in Phase 3.

### Temporal record contract

Every transcript, scene description, OCR result, object, action, or audio event must reduce to the same logical record:

```json
{
  "tenant_id": "tenant_1",
  "asset_id": "asset_1",
  "index_id": "scene_index_v1",
  "start_ms": 125000,
  "end_ms": 131500,
  "modality": "visual",
  "text": "A player scores and the crowd celebrates",
  "confidence": 0.91,
  "metadata": {},
  "source_refs": {},
  "model_version": "model_a",
  "processing_config": {}
}
```

Required invariants:

- `start_ms >= 0`
- `end_ms > start_ms`
- records cannot cross tenant or asset boundaries;
- model version and processing configuration are immutable;
- source references point to the frames, transcript, or media segments used;
- all times use normalized presentation timestamps relative to asset start.

## 6. Phase 1 — Archive Ingestion and Search MVP

### 6.1 Foundation

- Initialize the Python workspace and service packages.
- Add linting, type checking, tests, and CI.
- Add Docker Compose services for PostgreSQL/pgvector, MinIO, Redis, and Temporal.
- Add configuration loading with local, test, and production profiles.
- Add structured logs, request IDs, workflow IDs, and basic metrics.
- Create database migrations for tenants, collections, assets, jobs, indexes, temporal records, and virtual clips.

Acceptance criteria:

- A clean checkout starts all dependencies with one documented command.
- Database migrations apply and roll back in CI.
- Health and readiness endpoints report dependency state.
- Tenant ID is present in every persistent and searchable record.

### 6.2 Asset and Upload API

Implement:

- create/list/get collections;
- create/get/delete media assets;
- multipart presigned upload flow;
- URL import request;
- asset processing-status endpoint;
- idempotency keys for mutating API requests.

Asset states:

```text
CREATED → UPLOADING → INGESTED → TRANSCODING → INDEXING
        → READY | PARTIALLY_READY | FAILED | DELETED
```

Acceptance criteria:

- Large files upload directly to object storage rather than through the API.
- Retrying asset creation or upload completion does not duplicate the asset.
- API access is tenant-scoped.
- Invalid, missing, or corrupt uploads transition to a diagnosable failed state.

### 6.3 Media Normalization Workflow

Create an idempotent Temporal workflow:

1. Validate the source object.
2. Run `ffprobe` and persist media metadata.
3. Normalize timestamps.
4. Extract audio.
5. Generate a proxy rendition.
6. Generate keyframe-aligned CMAF/HLS fragments.
7. Generate thumbnails.
8. Persist segment and timestamp mappings.
9. Start the indexing workflow.

Store original and derived objects under separate immutable prefixes.

Acceptance criteria:

- Workflow resumes safely after worker restart or transient failure.
- The same workflow input cannot create duplicate renditions or segments.
- Generated HLS plays and seeks correctly in a standard player.
- Timestamp mappings remain within an agreed tolerance of source time.

### 6.4 Transcript Index

Build the spoken-word pipeline:

```text
audio → voice activity detection → ASR → alignment → embeddings
```

Persist:

- word timestamps where supported;
- utterance boundaries;
- language and confidence;
- speaker labels when enabled;
- normalized transcript text;
- embeddings per utterance or sentence.

Acceptance criteria:

- Transcript search returns asset ID, start/end time, score, and evidence text.
- Failed transcript processing does not remove usable visual results.
- Re-running with a new model creates a new index version.

### 6.5 Visual Index

Build the visual pipeline:

```text
video → shot boundaries → representative frames → description → embeddings
```

Start with scene-change extraction and a configurable maximum sampling interval. Cache decoded frames so later custom indexes can reuse them.

Acceptance criteria:

- Visual results link to their source shot and representative frames.
- Sampling configuration and model version are queryable.
- A failed visual branch leaves the asset `PARTIALLY_READY` when transcript search works.

### 6.6 Hybrid Search

Implement collection- and asset-level search with:

- tenant, collection, asset, time, modality, language, and index-version filters;
- vector similarity;
- PostgreSQL full-text retrieval;
- score normalization;
- overlap merging and deduplication;
- configurable pre-roll and post-roll;
- cursor-based pagination.

Use a weighted scoring policy stored as configuration, not hard-coded business logic.

Acceptance criteria:

- Every result contains exact timestamps, modality, score, index version, and source evidence.
- Filters are applied before or during retrieval, not only after ranking.
- No result can cross a tenant boundary.
- Warm search p95 is measured against the target of 300 ms on the agreed benchmark corpus.

### 6.7 Virtual Clips and Playback

Represent search results as virtual clips. For codec-compatible sources, generate HLS manifests that reference existing CMAF fragments. Defer re-encoding unless frame-accurate cuts, overlays, transitions, transforms, or mixed codecs require it.

Acceptance criteria:

- A search result can be opened as a playable HLS URL.
- Multiple results can be compiled into a single ordered manifest.
- Clip creation is fast and does not copy source video bytes.
- Signed URLs expire and remain tenant-authorized.

### Phase 1 Exit Criteria

An authenticated client can:

1. create a collection;
2. upload an MP4;
3. observe durable processing progress;
4. search transcript and visual content;
5. receive timestamped, grounded results;
6. play a result or compilation through HLS;
7. delete the asset and all derived data.

## 7. Phase 2 — Custom and Domain-Specific Indexes

### 7.1 First-Class Index Definitions

Add versioned index definitions containing:

- index type;
- prompt and prompt hash;
- model provider and version;
- frame/window sampling policy;
- preprocessing configuration;
- schema for structured output;
- status and production alias.

Two different prompts over the same asset create separate logical indexes while sharing decoded media artifacts.

### 7.2 Domain Pipelines

Prioritize:

- scoreboard changes;
- replay detection;
- speaker/person tracking;
- news topic boundaries;
- active-speaker intervals.

Use a two-stage pattern where useful:

```text
cheap candidate detector → expensive model verification
```

Acceptance criteria:

- Users can create, rebuild, promote, and query an index version.
- Existing production indexes remain available during rebuilds.
- Provider outputs are validated against a stored schema.
- Offline evaluation reports precision, recall, temporal IoU, latency, and cost.

## 8. Phase 3 — Live Streams and Alerts

### 8.1 Live Ingest

Add RTSP/RTMP first; add SRT and WebRTC only after the initial path is stable.

Pipeline:

```text
input → jitter buffer → timestamp normalization → CMAF segmenter
      → rolling buffer + playback origin + inference windows
```

Persist:

- event-time watermark;
- last committed timestamp;
- reconnect generation;
- retention policy;
- model state;
- discontinuities and dropped-packet metadata.

### 8.2 Live Indexing

- Publish configurable inference windows.
- Run ASR, visual, and audio processing independently.
- Write live temporal records incrementally.
- Make latency/quality settings explicit per index.
- Convert retained live segments to archive assets without rewriting media.

### 8.3 Events and Delivery

- Add reusable event rules.
- Evaluate rules against committed temporal records.
- Assign stable event IDs.
- Deliver best-effort UI updates over WebSocket.
- Deliver durable alerts by retried webhook or event queue.
- Create virtual clips around detected events.

Acceptance criteria:

- Stream reconnects do not duplicate committed segments or events.
- Webhook consumers can deduplicate by event ID.
- End-to-end event latency is measured per index configuration.
- Target latency is 2–10 seconds, subject to the configured inference window.

## 9. Phase 4 — Temporal Query Engine

Introduce a typed internal algebra:

```text
INTERSECT(a, b)
UNION(a, b)
BEFORE(a, b, max_gap)
AFTER(a, b, max_gap)
WITHIN(a, duration_of=b)
SEQUENCE(a, b, c)
DURATION(a, min_ms)
```

The query planner should:

1. parse a user query into modality-specific retrieval requests;
2. apply metadata and permission filters;
3. retrieve candidates in parallel;
4. apply temporal joins;
5. rerank fused intervals;
6. merge overlaps and attach evidence;
7. return an explainable query plan with results.

Target use cases:

- goals followed by a replay;
- pricing discussion while a chart is visible;
- a speaker talking continuously for more than 30 seconds;
- scoreboard changes without nearby commentary.

Acceptance criteria:

- Temporal operations have deterministic interval semantics.
- Plans can be inspected and replayed.
- Results identify the records and operations that produced them.
- Evaluation includes boundary accuracy as well as retrieval relevance.

## 10. Cross-Cutting Requirements

### Reliability

- Use at-least-once execution with idempotent activities.
- Derive a unique job key from tenant, asset, operation, model version, and configuration.
- Use database uniqueness constraints as the final duplicate guard.
- Retry transient errors with bounded exponential backoff.
- Route permanent failures to explicit failed states with operator-visible causes.

### Security and Isolation

- Enforce tenant scope in repository/query APIs and database policies where practical.
- Use short-lived signed object and playback URLs.
- Encrypt data in transit and at rest.
- Store secrets outside repository configuration.
- Audit upload, search, export, index change, and deletion operations.
- Define retention and legal-delete behavior before production use.

### Deletion

Asset deletion must orchestrate:

1. metadata tombstone;
2. search and vector record removal;
3. derived-object removal;
4. source-object removal;
5. CDN invalidation when applicable;
6. immutable audit entry.

Deletion must be retryable and expose completion status.

### Observability

Track:

- ingest throughput and failure rate;
- queue and workflow latency;
- processing time by model and media minute;
- search p50/p95/p99;
- live event end-to-end latency;
- vector and lexical candidate counts;
- model token/GPU cost per asset;
- clip startup time;
- orphaned objects and index records.

### Testing

- Unit-test temporal math, score fusion, state transitions, and job keys.
- Integration-test PostgreSQL, object storage, Temporal, and FFmpeg adapters.
- Maintain small deterministic audio/video fixtures.
- End-to-end test upload through playback.
- Add failure-injection tests for retries, worker restarts, partial indexes, and stream reconnects.
- Add tenant-isolation tests to every query surface.
- Build an offline relevance benchmark before tuning ranking weights.

## 11. API Surface for the MVP

```text
POST   /v1/collections
GET    /v1/collections
POST   /v1/assets
GET    /v1/assets/{asset_id}
DELETE /v1/assets/{asset_id}
POST   /v1/assets/{asset_id}/uploads
POST   /v1/assets/{asset_id}/uploads/complete
GET    /v1/assets/{asset_id}/status
POST   /v1/indexes
GET    /v1/indexes/{index_id}
POST   /v1/search
POST   /v1/clips
GET    /v1/clips/{clip_id}/manifest.m3u8
```

All mutation endpoints accept an idempotency key. Long-running operations return resource and workflow identifiers rather than holding an HTTP connection open.

## 12. TODOs

Complete these in order. Each checkbox should produce one small, reviewable change.

### Project foundation

- [x] Initialize the Python 3.12 project.
- [x] Add Ruff configuration.
- [x] Add ty configuration.
- [x] Add pytest configuration.
- [x] Add the `apps/api` package.
- [x] Add the `apps/worker` package.
- [x] Add a Docker Compose PostgreSQL service with pgvector.
- [x] Add a Docker Compose MinIO service.
- [x] Add a Docker Compose Redis service.
- [x] Add Docker Compose Temporal services.
- [x] Add API health and readiness endpoints.
- [x] Add CI checks for Ruff, ty, and pytest.

### Domain and persistence

- [x] Add the database connection module.
- [x] Add the migration runner.
- [x] Add the `Tenant` table.
- [x] Add the `Collection` table.
- [x] Add the `MediaAsset` table and processing state.
- [x] Add the `Rendition` table.
- [x] Add the `MediaSegment` table.
- [x] Add the `Index` table.
- [x] Add the `TemporalRecord` table.
- [x] Add the `VirtualClip` table.
- [x] Add the `Job` table with a unique idempotency key.
- [x] Add tenant-scoped repositories for each table.
- [x] Test tenant isolation in repository queries.

### Asset ingestion

- [x] Add the create-collection endpoint.
- [x] Add the list-collections endpoint.
- [x] Add the create-asset endpoint.
- [x] Add the get-asset endpoint.
- [x] Add the asset-status endpoint.
- [x] Add the presigned multipart-upload endpoint.
- [x] Add the upload-completion endpoint.
- [x] Add idempotency-key handling to asset mutations.
- [x] Add source-object validation.
- [x] Add URL import as a separate ingestion source.

### Media normalization

- [x] Add an `ffprobe` adapter.
- [x] Persist probed media metadata.
- [x] Add the Temporal asset-ingestion workflow.
- [x] Add an activity to extract audio.
- [x] Add an activity to create a proxy rendition.
- [x] Add an activity to generate CMAF/HLS fragments.
- [x] Add an activity to generate thumbnails.
- [x] Persist segment timestamp mappings.
- [x] Make every media activity idempotent.
- [x] Test workflow recovery after an activity retry.
- [x] Verify generated HLS playback and seeking.

### Transcript index

- [x] Define the ASR provider interface.
- [x] Add one ASR provider implementation.
- [x] Persist transcript utterances as temporal records.
- [x] Persist transcript embeddings.
- [x] Add transcript index version metadata.
- [x] Add transcript vector search.
- [x] Add transcript full-text search.
- [x] Return transcript timestamps and evidence text.
- [x] Test rebuilding a transcript index with a new version.

### Visual index

- [x] Define the visual-model provider interface.
- [x] Add shot-boundary extraction.
- [x] Add representative-frame extraction.
- [x] Add one visual-model provider implementation.
- [x] Persist visual descriptions as temporal records.
- [x] Persist visual embeddings.
- [x] Add visual index version metadata.
- [x] Add visual vector search.
- [x] Return visual timestamps and source-frame references.
- [x] Test `PARTIALLY_READY` when one index branch fails.

### Hybrid search

- [ ] Add the search request schema.
- [ ] Add tenant and collection filters.
- [ ] Add asset and time-range filters.
- [ ] Add modality and index-version filters.
- [ ] Retrieve vector and full-text candidates in parallel.
- [ ] Normalize candidate scores.
- [ ] Apply the configured score weights.
- [ ] Merge overlapping temporal results.
- [ ] Apply configurable pre-roll and post-roll.
- [ ] Add cursor-based pagination.
- [ ] Add the search endpoint.
- [ ] Benchmark warm search p95.

### Clips and playback

- [ ] Add virtual-clip creation.
- [ ] Select source fragments for a virtual clip.
- [ ] Generate an HLS manifest for one clip.
- [ ] Generate an ordered HLS compilation manifest.
- [ ] Add signed playback URLs.
- [ ] Add the clip-creation endpoint.
- [ ] Add the clip-manifest endpoint.
- [ ] Test clip creation without copying media bytes.

### Deletion and production hardening

- [ ] Add the asset metadata tombstone.
- [ ] Delete asset temporal records.
- [ ] Delete asset-derived objects.
- [ ] Delete the source object.
- [ ] Record asset deletion in the audit trail.
- [ ] Expose deletion completion status.
- [ ] Test retrying a partially completed deletion.
- [ ] Add request authentication.
- [ ] Add tenant quotas and rate limits.
- [ ] Add critical-path metrics and dashboards.

### Custom indexes

- [ ] Add the custom-index request schema.
- [ ] Persist prompt and prompt hash.
- [ ] Persist model and sampling configuration.
- [ ] Validate structured model output.
- [ ] Reuse existing decoded frames.
- [ ] Add index aliases such as `production`.
- [ ] Add index rebuild and promotion operations.
- [ ] Add the offline evaluation harness.
- [ ] Implement scoreboard-change indexing.
- [ ] Implement replay-detection indexing.
- [ ] Implement speaker/person tracking.
- [ ] Implement news-topic boundaries.

### Live streams

- [ ] Add the `RTStream` table.
- [ ] Add the `LiveSegment` table.
- [ ] Add the `Event` table.
- [ ] Add the `Alert` table.
- [ ] Add RTSP ingest.
- [ ] Add RTMP ingest.
- [ ] Normalize live-stream timestamps.
- [ ] Write live CMAF segments to a rolling buffer.
- [ ] Publish inference windows.
- [ ] Write live temporal records incrementally.
- [ ] Persist stream watermarks and reconnect generations.
- [ ] Test reconnect without duplicate segments.

### Events and alerts

- [ ] Add reusable event-rule storage.
- [ ] Evaluate one event rule against committed records.
- [ ] Assign stable event IDs.
- [ ] Deliver live UI events over WebSocket.
- [ ] Deliver durable alerts by webhook.
- [ ] Retry failed webhook delivery.
- [ ] Create a virtual clip for an event.
- [ ] Measure end-to-end event latency.

### Temporal queries

- [ ] Define the interval data type.
- [ ] Implement `INTERSECT`.
- [ ] Implement `UNION`.
- [ ] Implement `BEFORE`.
- [ ] Implement `AFTER`.
- [ ] Implement `WITHIN`.
- [ ] Implement `SEQUENCE`.
- [ ] Implement `DURATION`.
- [ ] Add deterministic tests for every temporal operator.
- [ ] Add modality-specific query planning.
- [ ] Apply temporal operators to retrieved candidates.
- [ ] Return the query plan with result evidence.
- [ ] Add boundary-accuracy evaluation.

Each TODO must include focused tests and documentation when its behavior requires them.

## 13. Decisions to Validate Early

Run short technical spikes before locking these choices:

- timestamp accuracy across variable-frame-rate inputs;
- zero-copy HLS compilation across fragment boundaries;
- pgvector performance under tenant and metadata filters;
- ASR alignment quality for target languages and noisy audio;
- visual sampling quality versus model cost;
- workflow history size for long assets and live streams;
- deletion completeness across metadata and object storage.

Record outcomes as architecture decision records under `docs/adr/`.

## 14. Definition of Done

The project is production-ready for a phase only when:

- its acceptance and exit criteria pass in automated tests;
- database and object-store migrations are documented;
- tenant isolation and deletion have been verified;
- latency, quality, and cost have measured baselines;
- failure recovery has been tested;
- dashboards and alerts exist for its critical path;
- API contracts and operational procedures are documented.
