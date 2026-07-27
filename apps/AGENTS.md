# Application Modules

## Scope

This file governs standalone modules directly under `apps/` and supplies defaults
for nested application packages.

## Rules

- Keep business logic independent of FastAPI request objects.
- Require `tenant_id` for every persistent read or mutation.
- Validate referenced entities through tenant-scoped repositories before writing.
- Do not commit partial derived state after provider, storage, or media failures.
- Keep external providers behind protocols and make retry/idempotency behavior
  explicit.
- A function named `deliver`, `ingest`, `delete`, or `write` must perform that
  operation or be clearly named as a simulation/test helper.
