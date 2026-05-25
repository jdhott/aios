# Patch Notes — Metadata Reconciliation Phase 1.4

Version:

```text
metadata-reconciliation-phase1-quick-win-deferred-cleanup-v0.1.4
```

## Changes

- Adds the first live metadata reconciliation mutation.
- Clears `Quick Win` for tasks deferred to a future date.
- Keeps all other reconciliation findings diagnostics-only.
- Logs each targeted task before mutation.
- Logs mutation success count and any mutation errors.
- Preserves existing bootstrap hook if already installed.

## Safety constraints

Only this mutation is allowed:

```text
Quick Win=true → Quick Win=false
```

Only when:

```text
Defer Until > today
```

No evaluator, ranking, BNA, Do = Today, Focus, or task-content changes are included.
