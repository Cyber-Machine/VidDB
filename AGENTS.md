# VideoDB Agent Guide

## Purpose

This repository implements a multi-tenant, time-addressable media database. Keep
media bytes in object storage and keep every derived record traceable to a tenant,
source, time range, index version, and model configuration.

## Working agreements

- Read the nearest `AGENTS.md`; deeper files override this guide.
- Preserve tenant isolation in application queries and database constraints.
- Treat index versions and processing configuration as immutable.
- Prefer real integrations or clearly named test doubles; do not present metadata
  placeholders as completed media processing.
- Use `apply_patch` for edits and preserve unrelated working-tree changes.

## Verification

Run these before handing off code changes:

```sh
uv run ruff check .
uv run ty check
uv run pytest -q
```

For schema work, test with foreign-key enforcement and provide an idempotent
PostgreSQL migration path for existing databases.
