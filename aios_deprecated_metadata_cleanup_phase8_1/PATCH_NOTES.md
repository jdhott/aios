# Patch Notes — Phase 8.1 Deprecated Metadata Cleanup

## Goal

Clear stale deprecated execution-era metadata that Phase 8 surfaced as a governance anomaly.

## Changes

- Bumps reconciliation version to `metadata-reconciliation-phase8-1-deprecated-metadata-cleanup-v0.8.1`.
- Adds `collect_deprecated_metadata_cleanup_actions()`.
- Adds `apply_deprecated_metadata_cleanup()`.
- Clears checked `Strong Candidate` and `Focus Now`/`Focus` fields only.
- Leaves anomaly diagnostics intact so the first run can show the detected stale value and then clear it.

## Mutation Boundary

Allowed mutation:

- `Strong Candidate=true` → `false`
- `Focus Now=true` / `Focus=true` → `false`

Not changed:

- `Execution Score`
- `Execution Rank`
- `Best Next Action`
- `Quick Win`
- `Do = Today`
- evaluator logic
- dashboard logic
- task titles/content
