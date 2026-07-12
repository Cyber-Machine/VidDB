# VideoDB TODOs

Complete these in order. Each checkbox should produce one small, reviewable change.

## Project foundation

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

## Domain and persistence

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

## Asset ingestion

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

## Media normalization

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

## Transcript index

- [x] Define the ASR provider interface.
- [x] Add one ASR provider implementation.
- [x] Persist transcript utterances as temporal records.
- [x] Persist transcript embeddings.
- [x] Add transcript index version metadata.
- [x] Add transcript vector search.
- [x] Add transcript full-text search.
- [x] Return transcript timestamps and evidence text.
- [x] Test rebuilding a transcript index with a new version.

## Visual index

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

## Hybrid search

- [x] Add the search request schema.
- [x] Add tenant and collection filters.
- [x] Add asset and time-range filters.
- [x] Add modality and index-version filters.
- [x] Retrieve vector and full-text candidates in parallel.
- [x] Normalize candidate scores.
- [x] Apply the configured score weights.
- [x] Merge overlapping temporal results.
- [x] Apply configurable pre-roll and post-roll.
- [x] Add cursor-based pagination.
- [x] Add the search endpoint.
- [x] Benchmark warm search p95.

## Clips and playback

- [x] Add virtual-clip creation.
- [x] Select source fragments for a virtual clip.
- [x] Generate an HLS manifest for one clip.
- [x] Generate an ordered HLS compilation manifest.
- [x] Add signed playback URLs.
- [x] Add the clip-creation endpoint.
- [x] Add the clip-manifest endpoint.
- [x] Test clip creation without copying media bytes.

## Deletion and production hardening

- [x] Add the asset metadata tombstone.
- [x] Delete asset temporal records.
- [x] Delete asset-derived objects.
- [x] Delete the source object.
- [x] Record asset deletion in the audit trail.
- [x] Expose deletion completion status.
- [x] Test retrying a partially completed deletion.
- [x] Add request authentication.
- [x] Add tenant quotas and rate limits.
- [x] Add critical-path metrics and dashboards.

## Custom indexes

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

## Live streams

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

## Events and alerts

- [ ] Add reusable event-rule storage.
- [ ] Evaluate one event rule against committed records.
- [ ] Assign stable event IDs.
- [ ] Deliver live UI events over WebSocket.
- [ ] Deliver durable alerts by webhook.
- [ ] Retry failed webhook delivery.
- [ ] Create a virtual clip for an event.
- [ ] Measure end-to-end event latency.

## Temporal queries

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
