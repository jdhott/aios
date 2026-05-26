# AIOS Canonical Metadata Reconciliation — Phase 7 Compact Governance Logging

This package reduces older verbose diagnostic logging while preserving the compact governance telemetry summary introduced in Phase 6.

## What changes

- Keeps the governance telemetry summary as the normal run-review surface.
- Suppresses detailed execution-rank row previews by default.
- Suppresses per-task Ranking Shadow V3 divergence lines by default.
- Suppresses per-task baseline executable fallback lines by default.
- Adds opt-in debug flags:
  - `AIOS_VERBOSE_RANK_DIAGNOSTICS=true`
  - `AIOS_VERBOSE_EXECUTION_DIAGNOSTICS=true`

## What does not change

- No evaluator scoring changes.
- No ranking selection changes.
- No dashboard changes.
- No Quick Win selection changes.
- No reconciliation mutation scope changes.
- Do = Today remains manual-only.
