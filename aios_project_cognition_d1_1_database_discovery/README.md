# AIOS Project Cognition D1.1 Package

This package hardens the D1 historical affinity telemetry script so it can recover from a stale or inaccessible configured Tasks database ID.

Install from project root:

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_project_cognition_d1_1_database_discovery.tar.gz
cd aios_project_cognition_d1_1_database_discovery
bash install.sh ~/LocalProjects/aios
cd ~/LocalProjects/aios
bash smoke_test_project_cognition_d1_1.sh
./venv/bin/python scripts/aios_project_affinity_report.py
```

The report remains read-only.
