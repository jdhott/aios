# AIOS Project Cognition D1.4 — Active-Task Affinity Preview

This package extends the D1 historical project affinity telemetry with a read-only preview of active/open tasks that appear to match historical project neighborhoods.

## What changes

- Keeps D1.3 project-name resolution for relation IDs.
- Adds active/open task affinity preview lines.
- Compares current active task title tokens against historical neighborhood term profiles.
- Emits candidate project/neighborhood matches with confidence, score, and overlap terms.

## What does not change

- No Notion writes.
- No task/project relation changes.
- No execution ranking changes.
- No BNA, Quick Win, Do = Today, Focus, or metadata governance impact.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_project_cognition_d1_4_active_task_affinity_preview.tar.gz
cd aios_project_cognition_d1_4_active_task_affinity_preview
bash install.sh ~/LocalProjects/aios
cd ~/LocalProjects/aios
bash smoke_test_project_cognition_d1_4.sh
./venv/bin/python scripts/aios_project_affinity_report.py
```

## Optional flags

```bash
./venv/bin/python scripts/aios_project_affinity_report.py --no-active-preview
./venv/bin/python scripts/aios_project_affinity_report.py --active-preview-min-score 5
./venv/bin/python scripts/aios_project_affinity_report.py --active-preview-limit 20
```

## Rollback

```bash
cd ~/LocalProjects/aios
bash aios_project_cognition_d1_4_active_task_affinity_preview/rollback.sh ~/LocalProjects/aios
```
