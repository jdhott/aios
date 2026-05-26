# AIOS Project Cognition D1.3 — Project Name Resolution

This package updates the read-only Project Cognition D1 telemetry script so historical affinity neighborhoods display human-readable Project names instead of raw Notion relation page IDs.

## What changes

- Keeps D1 historical affinity telemetry read-only.
- Keeps D1.2 database validation/discovery behavior.
- Loads the project-root `.env` with override behavior to avoid stale shell variables.
- Resolves Project relation page IDs via read-only Notion page retrieval.
- Emits telemetry such as:

```text
[Project Cognition] Neighborhood Project: Pool Maintenance and Operations — tasks=5; terms=pool:5, skimmer:2
```

instead of:

```text
[Project Cognition] Neighborhood relation:35e1facc...
```

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_project_cognition_d1_3_project_name_resolution.tar.gz
cd aios_project_cognition_d1_3_project_name_resolution
bash install.sh ~/LocalProjects/aios
cd ~/LocalProjects/aios
bash smoke_test_project_cognition_d1_3.sh
./venv/bin/python scripts/aios_project_affinity_report.py
```

## Safety

This package performs no writes to Notion and does not touch execution ranking, Best Next Actions, Quick Wins, reconciliation, or dashboard generation.

## Useful options

```bash
./venv/bin/python scripts/aios_project_affinity_report.py --json
./venv/bin/python scripts/aios_project_affinity_report.py --no-project-name-resolution
./venv/bin/python scripts/aios_project_affinity_report.py --list-databases
```
