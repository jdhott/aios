#!/bin/bash
set -euo pipefail

ROOT="$(pwd)"

if [ ! -f "$ROOT/execution_engine_v2.py" ]; then
  echo "ERROR: Run smoke_test.sh from AIOS project root."
  exit 1
fi

./venv/bin/python -m py_compile "$ROOT/execution_engine_v2.py" "$ROOT/core/runtime_analytics.py"

if ! grep -q "AIOS Runtime Analytics A1.0" "$ROOT/execution_engine_v2.py"; then
  echo "Smoke test failed: execution_engine_v2.py missing A1.0 hook marker"
  exit 1
fi

if ! grep -q "AIOS RUNTIME ANALYTICS SUMMARY A1.0" "$ROOT/core/runtime_analytics.py"; then
  echo "Smoke test failed: runtime_analytics.py missing summary marker"
  exit 1
fi

echo "Smoke test passed for AIOS Runtime Analytics A1.0"
echo "After a run, check:"
echo "  grep -A40 'AIOS RUNTIME ANALYTICS SUMMARY' test_run.log"
echo "  tail -n 5 logs/runtime_analytics.csv"
echo "  cat logs/runtime_analytics_latest.json"
