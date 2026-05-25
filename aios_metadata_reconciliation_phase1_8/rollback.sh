#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$PWD}"
BACKUP_MARKER="$PROJECT_ROOT/.metadata_reconciliation_phase1_8_last_backup"

if [[ ! -f "$BACKUP_MARKER" ]]; then
  echo "ERROR: No Phase 1.8 backup marker found at $BACKUP_MARKER"
  exit 1
fi

BACKUP_DIR="$(cat "$BACKUP_MARKER")"
if [[ ! -d "$BACKUP_DIR" ]]; then
  echo "ERROR: Backup directory not found: $BACKUP_DIR"
  exit 1
fi

cp "$BACKUP_DIR/run_aios.py.bak" "$PROJECT_ROOT/run_aios.py"
if [[ -d "$BACKUP_DIR/core.bak" ]]; then
  rm -rf "$PROJECT_ROOT/core"
  cp -R "$BACKUP_DIR/core.bak" "$PROJECT_ROOT/core"
fi

echo "Rolled back Metadata Reconciliation Phase 1.8 from $BACKUP_DIR"
