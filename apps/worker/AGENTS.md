# Worker Module

## Workflow behavior

- Workers own long-running ingestion, indexing, storage, and notification work.
- API handlers should enqueue work and return durable job identifiers.
- Activities must be idempotent, retry-safe, and observable by tenant, asset or
  stream, workflow, and attempt.
- Persist failure diagnostics and use explicit terminal states.
- Do not keep a database transaction open across network calls or model inference.
