#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-$PWD}"
LATEST_FILE="$TARGET/.last_aios_clarification_analytical_mode_a1_1_backup"

if [ ! -f "$LATEST_FILE" ]; then
  echo "ERROR: no A1.1 backup marker found: $LATEST_FILE"
  exit 1
fi

BACKUP_DIR="$(cat "$LATEST_FILE")"
if [ ! -f "$BACKUP_DIR/run_aios.py" ] || [ ! -f "$BACKUP_DIR/aios/clarification.py" ]; then
  echo "ERROR: backup files missing in $BACKUP_DIR"
  exit 1
fi

cp "$BACKUP_DIR/run_aios.py" "$TARGET/run_aios.py"
cp "$BACKUP_DIR/aios/clarification.py" "$TARGET/aios/clarification.py"
python3 -m py_compile "$TARGET/run_aios.py" "$TARGET/aios/clarification.py"

echo "Rollback complete from $BACKUP_DIR"
