#!/bin/bash
set -euo pipefail

ROOT="$(pwd)"

if [ ! -f "$ROOT/execution_engine_v2.py" ]; then
  echo "ERROR: Run smoke_test.sh from AIOS project root."
  exit 1
fi

./venv/bin/python -m py_compile "$ROOT/execution_engine_v2.py" "$ROOT/core/runtime_analytics.py"

grep -q "AIOS Runtime Analytics A1.1" "$ROOT/execution_engine_v2.py"
grep -q "AIOS RUNTIME ANALYTICS SUMMARY A1.1" "$ROOT/core/runtime_analytics.py"
grep -q "bna_provenance_mix" "$ROOT/core/runtime_analytics.py"
grep -q "bna_explicit_marker_count" "$ROOT/core/runtime_analytics.py"

echo "Smoke test passed for AIOS Runtime Analytics A1.1"
echo "After a run, check:"
echo "  grep -A50 'AIOS RUNTIME ANALYTICS SUMMARY' test_run.log"
echo "  tail -n 5 logs/runtime_analytics.csv"
echo "  cat logs/runtime_analytics_latest.json"
