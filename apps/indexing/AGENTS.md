# Indexing Module

## Invariants

- Production embeddings must come from the configured semantic model.
- Store the embedding model ID and immutable index configuration with each record.
- Never mix embedding models inside one promoted index version.
- Build replacements separately and promote atomically; a failed rebuild must
  preserve the previous searchable index.
- Query and document encoders must be used according to provider semantics.
- Validate vector dimensions before similarity calculations.

Tests may inject small deterministic providers, but their names and fixtures must
make clear that they are not production embeddings.
