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

- [ ] Add the create-collection endpoint.
- [ ] Add the list-collections endpoint.
- [ ] Add the create-asset endpoint.
- [ ] Add the get-asset endpoint.
- [ ] Add the asset-status endpoint.
- [ ] Add the presigned multipart-upload endpoint.
- [ ] Add the upload-completion endpoint.
- [ ] Add idempotency-key handling to asset mutations.
- [ ] Add source-object validation.
- [ ] Add URL import as a separate ingestion source.

## Media normalization

- [ ] Add an `ffprobe` adapter.
- [ ] Persist probed media metadata.
- [ ] Add the Temporal asset-ingestion workflow.
- [ ] Add an activity to extract audio.
- [ ] Add an activity to create a proxy rendition.
- [ ] Add an activity to generate CMAF/HLS fragments.
- [ ] Add an activity to generate thumbnails.
- [ ] Persist segment timestamp mappings.
- [ ] Make every media activity idempotent.
- [ ] Test workflow recovery after an activity retry.
- [ ] Verify generated HLS playback and seeking.

## Transcript index

- [ ] Define the ASR provider interface.
- [ ] Add one ASR provider implementation.
- [ ] Persist transcript utterances as temporal records.
- [ ] Persist transcript embeddings.
- [ ] Add transcript index version metadata.
- [ ] Add transcript vector search.
- [ ] Add transcript full-text search.
- [ ] Return transcript timestamps and evidence text.
- [ ] Test rebuilding a transcript index with a new version.

## Visual index

- [ ] Define the visual-model provider interface.
- [ ] Add shot-boundary extraction.
- [ ] Add representative-frame extraction.
- [ ] Add one visual-model provider implementation.
- [ ] Persist visual descriptions as temporal records.
- [ ] Persist visual embeddings.
- [ ] Add visual index version metadata.
- [ ] Add visual vector search.
- [ ] Return visual timestamps and source-frame references.
- [ ] Test `PARTIALLY_READY` when one index branch fails.

## Hybrid search

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

## Clips and playback

- [ ] Add virtual-clip creation.
- [ ] Select source fragments for a virtual clip.
- [ ] Generate an HLS manifest for one clip.
- [ ] Generate an ordered HLS compilation manifest.
- [ ] Add signed playback URLs.
- [ ] Add the clip-creation endpoint.
- [ ] Add the clip-manifest endpoint.
- [ ] Test clip creation without copying media bytes.

## Deletion and production hardening

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
