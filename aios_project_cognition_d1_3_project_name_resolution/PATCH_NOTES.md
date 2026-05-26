# Patch Notes — D1.3 Project Name Resolution

## Added

- Human-readable Project relation labels for historical affinity neighborhoods.
- Best-effort read-only Notion page-title resolution for related Project pages.
- Resolution telemetry: `resolved=N; unresolved=M`.
- `--no-project-name-resolution` fallback flag.
- `--project-name-limit` safety cap.

## Preserved

- Read-only project cognition mode.
- Zero Notion writes.
- No execution-authority impact.
- Database validation/discovery diagnostics from D1.2.
- Rollback-safe installer behavior.
