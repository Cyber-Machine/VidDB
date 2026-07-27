# API Module

## Contract

- Derive tenant identity from authenticated credentials; never trust an unrelated
  tenant header as authorization.
- Convert domain errors into stable HTTP status codes and response schemas.
- Bound list sizes, time ranges, pagination cursors, and user-controlled weights.
- Do not run CPU-heavy model inference or blocking media work on the async event
  loop.
- Keep CORS headers aligned with every supported authentication header.
- API responses must return usable HTTP(S) playback/upload URLs, not internal
  object-store URIs.

Add focused API tests for success, validation, authorization, and tenant isolation.
