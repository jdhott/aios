#!/usr/bin/env bash
set -euo pipefail
cd "${1:-$HOME/LocalProjects/aios}"
PY="./venv/bin/python"
if [ ! -x "$PY" ]; then PY="python3"; fi
$PY -m py_compile scripts/aios_project_affinity_report.py core/project_cognition/historical_affinity.py
$PY scripts/aios_project_affinity_report.py --help >/dev/null
echo "Smoke test passed: Project Cognition D1.2 script compiles and CLI loads."
