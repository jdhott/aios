# AIOS Project Cognition D1 — Historical Affinity Telemetry

## Purpose

First conservative step for Track D: Project Cognition Evolution.

This package adds a read-only historical affinity telemetry layer. It observes historical/completed task patterns and reports lightweight operational neighborhoods without writing to Notion or affecting execution authority.

## Installed files

- `core/project_cognition/__init__.py`
- `core/project_cognition/historical_affinity.py`
- `scripts/aios_project_affinity_report.py`

## Architecture guardrails

- No Notion writes
- No project mutation
- No task relation mutation
- No execution ranking changes
- No Best Next Action changes
- No Quick Win changes
- No governance reconciliation changes

## Run commands

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_project_cognition_d1_historical_affinity_package.tar.gz
cd aios_project_cognition_d1_historical_affinity_package
bash install.sh ~/LocalProjects/aios
cd ~/LocalProjects/aios
bash smoke_test.sh
./venv/bin/python scripts/aios_project_affinity_report.py
```

If your task database env var is not named `NOTION_TASKS_DATABASE_ID`, either add it to `.env` or pass:

```bash
./venv/bin/python scripts/aios_project_affinity_report.py --database-id YOUR_TASK_DATABASE_ID
```

## Rollback

```bash
cd ~/LocalProjects/aios/aios_project_cognition_d1_historical_affinity_package
bash rollback.sh ~/LocalProjects/aios
```
