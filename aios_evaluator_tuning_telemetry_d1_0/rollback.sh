#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"
MARKER="$ROOT/.last_evaluator_tuning_telemetry_d1_0_backup"

if [[ ! -f "$MARKER" ]]; then
  echo "ERROR: no backup marker found: $MARKER"
  exit 1
fi

BACKUP_DIR="$(cat "$MARKER")"

if [[ ! -f "$BACKUP_DIR/execution_engine_v2.py" ]]; then
  echo "ERROR: backup file not found: $BACKUP_DIR/execution_engine_v2.py"
  exit 1
fi

cp "$BACKUP_DIR/execution_engine_v2.py" "$ROOT/execution_engine_v2.py"
rm -f "$ROOT/smoke_test_evaluator_tuning_telemetry.py"
python3 -m py_compile "$ROOT/execution_engine_v2.py"

echo "Rolled back AIOS Evaluator Tuning Telemetry D1.0"
echo "Restored: $BACKUP_DIR/execution_engine_v2.py"
