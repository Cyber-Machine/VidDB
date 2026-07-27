# Media Module

## Media processing

- FFmpeg/ffprobe commands must be argument arrays, checked for failure, and covered
  by adapter-level tests.
- Normalize all persisted timestamps to milliseconds relative to source start.
- Write derived objects before committing database references to them.
- Make every processing activity idempotent and safe to retry.
- Verify generated manifests using real segment durations and browser-reachable
  URLs.
- Never fabricate a derived object URI unless the corresponding object was
  successfully written.
