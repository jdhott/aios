# AIOS Project Cognition D1.2.1 — Smoke Test Install Fix

This package corrects the D1.2 packaging issue where the smoke test remained inside the extracted package folder but was not copied to the AIOS project root.

It also reinstalls the D1.2 read-only project affinity files so the installed state is complete and consistent.

## Install

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_project_cognition_d1_2_1_smoke_test_fix.tar.gz
cd aios_project_cognition_d1_2_1_smoke_test_fix
bash install.sh ~/LocalProjects/aios
cd ~/LocalProjects/aios
bash smoke_test_project_cognition_d1_2_1.sh
./venv/bin/python scripts/aios_project_affinity_report.py
```

## Notes

- Read-only telemetry only.
- No Notion writes.
- No execution authority changes.
- No dashboard mutations.
