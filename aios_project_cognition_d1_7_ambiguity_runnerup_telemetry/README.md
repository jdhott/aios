# AIOS Project Cognition D1.7 — Ambiguity / Runner-Up Telemetry

This package extends the read-only project cognition report with runner-up and ambiguity telemetry for active-task affinity previews.

## Scope

- Keeps historical project affinity telemetry read-only.
- Keeps project name resolution from D1.3.
- Keeps active-task preview from D1.4.
- Keeps weak-term weighting from D1.5.
- Keeps strong-domain confidence calibration from D1.6.1.
- Adds nearest runner-up project/neighborhood for each active-task preview when available.
- Adds an ambiguity level so future write-back risks are visible before any mutation phase.

## Safety

- No Notion writes.
- No task/project relation changes.
- No execution ranking changes.
- No Best Next Action, Quick Win, or governance reconciliation changes.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_project_cognition_d1_7_ambiguity_runnerup_telemetry.tar.gz
cd aios_project_cognition_d1_7_ambiguity_runnerup_telemetry
bash install.sh ~/LocalProjects/aios
cd ~/LocalProjects/aios
bash smoke_test_project_cognition_d1_7.sh
./venv/bin/python scripts/aios_project_affinity_report.py
```
