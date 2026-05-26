# AIOS Project Cognition D1.1 — Database Discovery Hardening

## Purpose

Fixes the first D1 historical affinity report failure where the script exited on a stale or inaccessible configured Notion Tasks database ID.

## What Changed

- `scripts/aios_project_affinity_report.py`
  - Validates the configured task database before querying it.
  - Falls back to read-only Notion database discovery if the configured ID returns 404.
  - Selects the likely AIOS Tasks database by schema signals:
    - `Task Name` title property
    - `Done` checkbox property
    - task metadata fields such as Project, Parent Task, Execution Rank, Execution Score, Best Next Action, Quick Win
  - Emits database-resolution telemetry before the historical affinity summary.
  - Adds `--no-discover` for strict configured-ID mode.
  - Preserves read-only behavior.

## What Did Not Change

- No Notion writes.
- No project relation mutation.
- No execution ranking changes.
- No Quick Win or BNA changes.
- No governance reconciliation changes.

## Test Command

```bash
cd ~/LocalProjects/aios
bash smoke_test_project_cognition_d1_1.sh
./venv/bin/python scripts/aios_project_affinity_report.py
```

## Rollback

```bash
cd ~/LocalProjects/aios
bash rollback_project_cognition_d1_1.sh
```
