# Patch Notes — AIOS Project Cognition D1.4

## Summary

Adds read-only active-task affinity preview telemetry to the historical project affinity report.

## Behavior

The report now prints:

```text
[Project Cognition] Active affinity preview: candidates=N; read_only=true
[Project Cognition] Active candidate: <task> → <project/neighborhood> (confidence=...; score=...; overlap=...)
```

## Safety

- Read-only telemetry only.
- Writes remain zero.
- Execution authority remains untouched.
- Project relation mutation is not introduced.

## Files changed

- `scripts/aios_project_affinity_report.py`
- `core/project_cognition/historical_affinity.py`
- `core/project_cognition/__init__.py`
- `smoke_test_project_cognition_d1_4.sh`
