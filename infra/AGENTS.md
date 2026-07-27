# Infrastructure Module

## Local and production parity

- Pin service images to explicit versions; avoid floating `latest` tags.
- Keep secrets outside committed compose files for non-development deployments.
- Add health checks for every dependency used by readiness.
- Preserve PostgreSQL/pgvector, object storage, Redis, and workflow data in named
  volumes.
- Document port changes and avoid silently reusing ports owned by other projects.
