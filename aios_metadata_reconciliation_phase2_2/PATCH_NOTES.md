# Patch Notes — Metadata Reconciliation Phase 2.2

## Added

- Detailed execution-rank pipeline diagnostics.
- Logs current persisted-rank order.
- Logs deterministic score/title/page-id order for comparison.
- Logs missing and duplicate persisted ranks.
- Logs skipped candidate counts by exclusion reason.

## Preserved

- Closed-task persistence guard.
- Deferred Quick Win cleanup.
- Closed/done execution metadata cleanup.
- Execution rank canonicalization from Phase 2.1.

## Safety

This package adds diagnostics only for the new rank-ordering question. It does not change evaluator scoring logic.
