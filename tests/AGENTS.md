# Test Suite

## Expectations

- Keep tests deterministic and independent of external network services.
- SQLite tests must enable foreign-key enforcement.
- Add PostgreSQL-focused coverage for migrations and dialect-specific behavior.
- Test tenant isolation at API, repository, and foreign-key boundaries.
- Name injected providers as test doubles and separately verify production adapter
  contracts.
- Regression tests should fail on the original bug and assert persisted state, not
  only return values.
