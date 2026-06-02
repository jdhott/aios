#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
STAMP=".last_evaluator_tuning_telemetry_d1_2_backup"
if [[ ! -f "$STAMP" ]]; then
  echo "No D1.2 backup stamp found; nothing to rollback."
  exit 1
fi
BACKUP_DIR="$(cat "$STAMP")"
if [[ ! -f "$BACKUP_DIR/execution_engine_v2.py" ]]; then
  echo "Backup file not found: $BACKUP_DIR/execution_engine_v2.py"
  exit 1
fi
cp "$BACKUP_DIR/execution_engine_v2.py" execution_engine_v2.py
echo "Rolled back AIOS Evaluator Tuning Telemetry D1.2"
echo "Restored: $BACKUP_DIR/execution_engine_v2.py"
