#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="${1:-$HOME/LocalProjects/aios}"
cd "$PROJECT_DIR"

PYTHON_BIN="python3"
if [ -x "./venv/bin/python" ]; then
  PYTHON_BIN="./venv/bin/python"
elif [ -x "./.venv/bin/python" ]; then
  PYTHON_BIN="./.venv/bin/python"
fi

"$PYTHON_BIN" -m py_compile run_aios.py run_aios_PHASE2_FIXED.py

grep -q "SURFACED_QUICK_WIN_PROPERTY" run_aios.py
grep -q "def refresh_surfaced_quick_wins" run_aios.py
grep -q "refresh_surfaced_quick_wins(all_open_tasks, EXECUTION_ENGINE_WINNERS)" run_aios.py
grep -q "def select_surfaced_quick_wins" run_aios.py

echo "Smoke test passed: surfaced Quick Win lane code is installed and compiles."
