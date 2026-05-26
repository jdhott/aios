#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$(pwd)}"
PATCH_NAME="governance_anomaly_diagnostics_phase8"
LAST_BACKUP_FILE="$PROJECT_ROOT/.last_${PATCH_NAME}_backup"

if [[ ! -f "$LAST_BACKUP_FILE" ]]; then
  echo "ERROR: No backup marker found: $LAST_BACKUP_FILE" >&2
  exit 1
fi
BACKUP_DIR="$(cat "$LAST_BACKUP_FILE")"
if [[ ! -f "$BACKUP_DIR/core/metadata/reconciliation.py" ]]; then
  echo "ERROR: Backup reconciliation.py not found in: $BACKUP_DIR" >&2
  exit 1
fi

cp "$BACKUP_DIR/core/metadata/reconciliation.py" "$PROJECT_ROOT/core/metadata/reconciliation.py"
python3 -m py_compile "$PROJECT_ROOT/core/metadata/reconciliation.py"
echo "Rolled back $PATCH_NAME"
echo "Restored: $PROJECT_ROOT/core/metadata/reconciliation.py"
echo "From: $BACKUP_DIR"
