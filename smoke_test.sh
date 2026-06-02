#!/bin/bash
set -euo pipefail
cd "${AIOS_ROOT:-$HOME/LocalProjects/aios}"
PY="./venv/bin/python"
if [ ! -x "$PY" ]; then echo "ERROR: expected executable venv python at $PY"; exit 1; fi
if ! grep -q "run_aios.py" run_aios_inner.sh; then echo "ERROR: run_aios_inner.sh does not target run_aios.py"; exit 1; fi
"$PY" -m py_compile run_aios.py execution_engine_v2.py core/evaluator.py tools/aios_runtime_lock.py
if ! grep -q "Evaluator Tuning Telemetry D1.1" execution_engine_v2.py; then echo "ERROR: evaluator tuning telemetry marker missing"; exit 1; fi
if ! grep -q "emit_evaluator_tuning_telemetry(ranked, winners)" execution_engine_v2.py; then echo "ERROR: evaluator tuning telemetry call missing"; exit 1; fi
echo "Smoke test passed: active runtime is run_aios.py and evaluator telemetry D1.1 is installed."
