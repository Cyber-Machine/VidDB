# Frontend Module

## Constraints

- Keep the current dependency-free browser client unless the task explicitly
  introduces a framework.
- Render API data safely; do not interpolate untrusted values with `innerHTML`.
- Show real API failures distinctly from demo data.
- Keep player timestamps in sync with backend millisecond ranges.
- Browser requests must include the configured authentication and tenant context.
- Test ingestion, polling, search, evidence inspection, and playback URL handling
  in `smoke_test.mjs`.
