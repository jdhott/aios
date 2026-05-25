# Patch Notes — Metadata Reconciliation Phase 1.9

## New
- Adds diagnostics-only detection for open-task `Best Next Action` / `Do = Today` surface mismatches.
- Separates open-task presentation mismatch visibility from mutation behavior.
- Excludes future-deferred tasks from the new open-surface mismatch diagnostics because those are already handled by the deferred-surface rule.

## Preserved
- Keeps Phase 1.4 safe mutation: clear `Quick Win` only for future-deferred tasks.
- Keeps Phase 1.8 safe mutation: clear meaningful `Execution Score` / `Execution Rank` only on closed/done tasks.
- No evaluator, ranking, Best Next Action, Do = Today, Focus, or task-content mutation added.
