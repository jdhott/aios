# AIOS Metadata Reconciliation Phase 1.11

## Purpose

Adds explicit open-surface mismatch diagnostic counts, including zero-count lines when the system is clean.

## Behavior

Validated mutations retained:
- Clear Quick Win only for future-deferred tasks.
- Clear meaningful Execution Score / Execution Rank only for closed/done tasks.

New diagnostics-only visibility:
- Open tasks with Do = Today but not Best Next Action.
- Open Best Next Action tasks not surfaced in Do = Today.
- Open Best Next Action tasks without Execution Rank.
- Open Best Next Action tasks without meaningful Execution Score.

No new mutation class is added in this package.
