#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"
LAST_FILE="$ROOT/.last_aios_clarification_analytical_mode_a1_0_backup"

if [[ ! -f "$LAST_FILE" ]]; then
  echo "ERROR: No backup marker found: $LAST_FILE" >&2
  exit 1
fi

BACKUP_DIR="$(cat "$LAST_FILE")"
if [[ ! -d "$BACKUP_DIR" ]]; then
  echo "ERROR: Backup directory missing: $BACKUP_DIR" >&2
  exit 1
fi

cp "$BACKUP_DIR/run_aios.py" "$ROOT/run_aios.py"
cp "$BACKUP_DIR/aios/clarification.py" "$ROOT/aios/clarification.py"
python3 -m py_compile "$ROOT/run_aios.py" "$ROOT/aios/clarification.py"

echo "Rollback complete from: $BACKUP_DIR"
