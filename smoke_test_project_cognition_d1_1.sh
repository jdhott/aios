#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-$PWD}"
cd "$TARGET_DIR"

PYTHON="./venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

$PYTHON -m py_compile scripts/aios_project_affinity_report.py core/project_cognition/historical_affinity.py
$PYTHON scripts/aios_project_affinity_report.py --help >/tmp/aios_project_affinity_help.txt

grep -q -- "--no-discover" /tmp/aios_project_affinity_help.txt
grep -q "D1 historical project affinity" /tmp/aios_project_affinity_help.txt

echo "Smoke test passed: D1.1 script compiles and discovery flag is available."
