# Patch Notes — Metadata Reconciliation Phase 1.8

## New
- Applies the first closed/done task execution cleanup mutation.
- Clears only meaningful stale execution fields on closed/done tasks:
  - `Execution Rank`
  - `Execution Score` when non-zero
- Continues to ignore `Execution Score=0` as default/noise.

## Preserved
- Keeps Phase 1.4 safe mutation: clear `Quick Win` only for future-deferred tasks.
- No evaluator, ranking, Best Next Action, Do = Today, Focus, or task-content changes.
- Rollback-safe installer with backup snapshot.
