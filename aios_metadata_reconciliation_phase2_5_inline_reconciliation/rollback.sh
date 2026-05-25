#!/bin/bash
set -euo pipefail

PROJECT_DIR="${1:-$HOME/LocalProjects/aios}"
MARKER="$PROJECT_DIR/.metadata_reconciliation_phase2_5_last_backup"

if [ ! -f "$MARKER" ]; then
  echo "No Phase 2.5 backup marker found: $MARKER"
  exit 1
fi

BACKUP_DIR="$(cat "$MARKER")"

cp "$BACKUP_DIR/run_aios.py.bak" "$PROJECT_DIR/run_aios.py"
cp "$BACKUP_DIR/reconciliation.py.bak" "$PROJECT_DIR/core/metadata/reconciliation.py"

echo "Rollback complete from $BACKUP_DIR"
