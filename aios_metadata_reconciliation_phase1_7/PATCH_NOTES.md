# Patch Notes — Metadata Reconciliation Phase 1.7

## New
- Reduces closed/done task diagnostic noise.
- Treats `Execution Score=0` alone as default/non-meaningful metadata.
- Only flags closed/done execution metadata when meaningful stale fields are present:
  - `Execution Rank`
  - `Best Next Action`
  - `Focus Now`
  - `Execution Score > 0`

## Preserved
- Keeps Phase 1.4 safe mutation: clear `Quick Win` only for future-deferred tasks.
- Closed/done task cleanup remains diagnostics/preview only.
- No evaluator, ranking, BNA, Do = Today, or task-content changes.
