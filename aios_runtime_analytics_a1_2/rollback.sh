#!/usr/bin/env bash
set -euo pipefail
ROOT="$(pwd)"
LATEST="$(ls -td "$ROOT"/.aios_runtime_analytics_a1_2_backup_* 2>/dev/null | head -1 || true)"
if [[ -z "$LATEST" ]]; then
  echo "No A1.2 backup found." >&2
  exit 1
fi
cp "$LATEST/execution_engine_v2.py" "$ROOT/execution_engine_v2.py"
if [[ -f "$LATEST/core/runtime_analytics.py" ]]; then
  mkdir -p "$ROOT/core"
  cp "$LATEST/core/runtime_analytics.py" "$ROOT/core/runtime_analytics.py"
fi
if [[ -f "$LATEST/logs/runtime_analytics.csv" ]]; then
  mkdir -p "$ROOT/logs"
  cp "$LATEST/logs/runtime_analytics.csv" "$ROOT/logs/runtime_analytics.csv"
fi
python3 -m py_compile "$ROOT/execution_engine_v2.py"
if [[ -f "$ROOT/core/runtime_analytics.py" ]]; then
  python3 -m py_compile "$ROOT/core/runtime_analytics.py"
fi
echo "Rolled back AIOS Runtime Analytics A1.2 using $LATEST"
