# AIOS Project Cognition D1.8 — Overlapping Project Neighborhood Detection

Read-only telemetry package for AIOS project cognition.

## What this adds

- Keeps D1.7 active-task affinity and runner-up ambiguity telemetry.
- Adds duplicate/overlapping project-neighborhood detection.
- Compares historical project term profiles using weighted overlap.
- Flags likely overlapping project concepts before any write-back phase.
- Performs no Notion writes.
- Does not affect execution ranking, BNA, Quick Wins, or governance reconciliation.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_project_cognition_d1_8_overlap_detection.tar.gz
cd aios_project_cognition_d1_8_overlap_detection
bash install.sh ~/LocalProjects/aios
cd ~/LocalProjects/aios
bash smoke_test_project_cognition_d1_8.sh
./venv/bin/python scripts/aios_project_affinity_report.py
```

## Expected telemetry

Look for lines like:

```text
[Project Cognition] Overlapping project neighborhoods: candidates=N; read_only=true
[Project Cognition] Overlap candidate: Project A ↔ Project B (... risk=medium/high)
[Project Cognition] Project overlap detection: enabled=true; overlap_candidates=N; writeback_guard=active
[Project Cognition] D1 mode: read_only=true; writes=0; execution_authority_impact=none
```
