# AIOS Project Cognition D1.5 — Affinity Weak-Term Weighting

This package tunes the read-only historical project affinity preview introduced in D1.4.

## What changes

- Discounts broad/generic active-affinity terms such as `bread`, `app`, `message`, `put`, and similar low-specificity tokens.
- Requires stronger evidence before an active task receives medium/high affinity confidence.
- Suppresses one-word broad matches from becoming high-confidence project suggestions.
- Keeps project-name resolution and database discovery from D1.3/D1.4.

## Safety

- Read-only telemetry only.
- No Notion writes.
- No execution ranking changes.
- No BNA, Quick Win, or reconciliation authority impact.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_project_cognition_d1_5_affinity_weighting.tar.gz
cd aios_project_cognition_d1_5_affinity_weighting
bash install.sh ~/LocalProjects/aios
cd ~/LocalProjects/aios
bash smoke_test_project_cognition_d1_5.sh
./venv/bin/python scripts/aios_project_affinity_report.py
```
