#!/bin/bash
set -euo pipefail

ROOT="$(pwd)"
MARKER="$ROOT/.last_aios_runtime_analytics_a1_1_backup"
if [ ! -f "$MARKER" ]; then
  echo "ERROR: No .last_aios_runtime_analytics_a1_1_backup file found."
  exit 1
fi

BACKUP_DIR="$(cat "$MARKER")"
if [ ! -d "$BACKUP_DIR" ]; then
  echo "ERROR: Backup directory not found: $BACKUP_DIR"
  exit 1
fi

cp "$BACKUP_DIR/execution_engine_v2.py" "$ROOT/execution_engine_v2.py"
if [ -f "$BACKUP_DIR/core/runtime_analytics.py" ]; then
  mkdir -p "$ROOT/core"
  cp "$BACKUP_DIR/core/runtime_analytics.py" "$ROOT/core/runtime_analytics.py"
else
  rm -f "$ROOT/core/runtime_analytics.py"
fi

./venv/bin/python -m py_compile "$ROOT/execution_engine_v2.py"
if [ -f "$ROOT/core/runtime_analytics.py" ]; then
  ./venv/bin/python -m py_compile "$ROOT/core/runtime_analytics.py"
fi

echo "Rolled back AIOS Runtime Analytics A1.1"
