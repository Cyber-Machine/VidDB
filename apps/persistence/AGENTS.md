# Persistence Module

## Schema invariants

- Every tenant-owned row carries `tenant_id`; cross-tenant references must be
  impossible at both repository and database levels.
- A `TemporalRecord` belongs to exactly one source: `asset_id` XOR `stream_id`.
- `asset_id` references `media_assets.id`; `stream_id` references `rt_streams.id`.
- Temporal ranges satisfy `start_ms >= 0` and `end_ms > start_ms`.
- Index name/version/model configuration is immutable once records exist.

## Migrations

- `create_all` supports fresh databases only; every schema change also needs an
  idempotent PostgreSQL migration for existing databases.
- Backfill before adding constraints, name constraints explicitly, and test the
  upgrade path where practical.
- Do not weaken foreign-key enforcement in tests.
