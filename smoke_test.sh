#!/bin/bash
set -euo pipefail

cd "${AIOS_ROOT:-$HOME/LocalProjects/aios}"

PY="./.venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "ERROR: expected executable Python at $PY"
  exit 1
fi

if ! grep -q "run_aios.py" run_aios_inner.sh; then
  echo "ERROR: run_aios_inner.sh does not target run_aios.py"
  exit 1
fi

"$PY" -m py_compile \
  run_aios.py \
  execution_engine_v2.py \
  core/evaluator.py \
  tools/aios_runtime_lock.py

echo "Smoke test passed: runtime launcher and core Python files are valid."
