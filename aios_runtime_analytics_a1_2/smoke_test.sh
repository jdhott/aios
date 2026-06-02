#!/usr/bin/env bash
set -euo pipefail
ROOT="$(pwd)"
python3 -m py_compile "$ROOT/execution_engine_v2.py" "$ROOT/core/runtime_analytics.py"
grep -q "AIOS Runtime Analytics A1.2" "$ROOT/execution_engine_v2.py"
grep -q "aios-runtime-analytics-a1.2" "$ROOT/core/runtime_analytics.py"
grep -q "runtime_analytics_details.ndjson" "$ROOT/core/runtime_analytics.py"
grep -q "consecutive_bna_runs" "$ROOT/core/runtime_analytics.py"
if grep -q '"bna_provenance_json"' "$ROOT/core/runtime_analytics.py"; then
  echo "Smoke test failed: CSV still contains bna_provenance_json." >&2
  exit 1
fi
echo "Smoke test passed for AIOS Runtime Analytics A1.2"
