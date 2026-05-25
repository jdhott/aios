# AIOS Metadata Reconciliation Phase 2.1 — Execution Rank Canonicalization

## Purpose

Fix visible gaps in `Execution Rank` after final candidate pruning/filtering.

Observed issue:

```text
1, 2, 4, 5, 6...
```

This package adds a final-stage canonicalization pass that preserves the current runtime order but rewrites active ranked tasks as a contiguous sequence:

```text
1, 2, 3, 4, 5...
```

## Scope

Still retained from Phase 2.0:

- Deferred Quick Win cleanup
- Closed/done execution cleanup
- Closed/done execution persistence guard
- Open BNA / Do = Today diagnostics
- JDI stale metadata diagnostics
- Future-deferred surface diagnostics

New in Phase 2.1:

- Active ranked tasks with meaningful scores are sorted by current `Execution Rank`
- Ranks are compacted to a contiguous 1..N sequence
- No scoring logic is changed
- No evaluator weights are changed
- No task titles/content are changed

## Safety Boundary

The canonicalization pass only touches `Execution Rank` on tasks that are:

- open
- not closed/done
- not future-deferred
- not JDI
- already ranked
- already have meaningful `Execution Score > 0`

It does not create new ranked tasks.
