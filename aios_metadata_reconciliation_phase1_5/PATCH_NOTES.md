# Patch Notes — Metadata Reconciliation Phase 1.5

## New
- Adds diagnostics-only rule for closed/done tasks with active presentation metadata.
- Adds diagnostics-only rule for closed/done tasks with execution metadata.
- Emits `Closed/done tasks observed` in the reconciliation summary.

## Preserved
- Keeps Phase 1.4 safe mutation: clear `Quick Win` only for future-deferred tasks.
- No mutation for closed/done task findings.
- No evaluator, ranking, BNA, Do = Today, or task-content changes.
