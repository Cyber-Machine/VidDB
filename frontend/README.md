# VideoDB explainability frontend

This is a deliberately small, dependency-free client for the existing FastAPI API. It provides the first Pegasus-like workspace slice: ingest/register a video, search temporal evidence, jump the player to a result, inspect Visual or JSON evidence, and see the query-to-clip explanation.

Run it locally:

```bash
python -m http.server 4173 --directory frontend
```

Open `http://localhost:4173`. Configure the API origin with the **Configure** link. When the API is unavailable, the page stays usable with the football demo records so the explainability interaction can still be reviewed.

Run the focused contract smoke test with `node --test frontend/smoke_test.mjs`.

The backend currently requires `X-Tenant-ID: demo`. Multipart mode displays the presigned-upload request; actual object storage upload remains the next integration step because the current API returns contract URLs rather than accepting browser bytes directly.
