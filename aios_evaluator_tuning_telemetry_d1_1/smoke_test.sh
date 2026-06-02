#!/bin/bash
set -euo pipefail
ROOT="${AIOS_ROOT:-$HOME/LocalProjects/aios}"
cd "$ROOT"
./venv/bin/python -m py_compile run_aios.py execution_engine_v2.py core/evaluator.py tools/aios_runtime_lock.py
grep -q "Evaluator Tuning Telemetry D1.1" execution_engine_v2.py
grep -q "run_aios.py" run_aios_inner.sh
echo "Package smoke test passed."
