# AIOS Project Cognition D1.2 — Task DB Resolution Hotfix

This package patches the read-only D1 historical project affinity report.

## What changed

- Validates configured `TASKS_DATABASE_ID` before querying.
- Normalizes hyphenated/unhyphenated Notion IDs.
- Falls back to Notion database search when the configured ID is stale or inaccessible.
- Scores accessible databases by AIOS Tasks schema signals.
- Adds `--list-databases` diagnostic mode.
- Still performs **no Notion writes** and has **no execution-authority impact**.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_project_cognition_d1_2_task_db_resolution.tar.gz
cd aios_project_cognition_d1_2_task_db_resolution
bash install.sh ~/LocalProjects/aios
cd ~/LocalProjects/aios
bash smoke_test_project_cognition_d1_2.sh
./venv/bin/python scripts/aios_project_affinity_report.py
```

## If the report still cannot find the Tasks database

Run:

```bash
./venv/bin/python scripts/aios_project_affinity_report.py --list-databases
```

If the real Tasks database does not appear in that list, Notion is not exposing it to the integration currently in `NOTION_TOKEN`. Share the Tasks database with that integration, or update `.env` with the current database ID.

You can also pass the database directly:

```bash
./venv/bin/python scripts/aios_project_affinity_report.py --database-id <current_tasks_database_id>
```
