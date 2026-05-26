# AIOS Project Cognition D1.6 — Strong-Domain Confidence Calibration

This package updates the read-only historical affinity telemetry introduced in D1.4/D1.5.

## Purpose

D1.6 improves active-task confidence calibration:

- strong operational anchor terms such as `pool`, `skimmer`, `workshop`, and `labels` can produce high-confidence previews when historical support is strong
- broad terms such as `bread`, generic verbs, and generic app/community terms remain suppressed
- project cognition remains strictly read-only

## Safety

- Notion writes: 0
- Execution authority impact: none
- BNA / Quick Win / ranking changes: none
- Rollback-safe backup included

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_project_cognition_d1_6_strong_domain_confidence.tar.gz
cd aios_project_cognition_d1_6_strong_domain_confidence
bash install.sh ~/LocalProjects/aios
cd ~/LocalProjects/aios
bash smoke_test_project_cognition_d1_6.sh
./venv/bin/python scripts/aios_project_affinity_report.py
```
