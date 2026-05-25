#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$PWD}"
cd "$PROJECT_ROOT"

if [[ ! -f ".metadata_reconciliation_phase1_last_backup" ]]; then
  echo "ERROR: .metadata_reconciliation_phase1_last_backup not found."
  echo "Pass the project root where install.sh was run, or restore manually from backups/."
  exit 1
fi

BACKUP_DIR="$(cat .metadata_reconciliation_phase1_last_backup)"
if [[ ! -f "$BACKUP_DIR/run_aios.py.bak" ]]; then
  echo "ERROR: backup run_aios.py not found at $BACKUP_DIR"
  exit 1
fi

cp "$BACKUP_DIR/run_aios.py.bak" "$PROJECT_ROOT/run_aios.py"
if [[ -d "$BACKUP_DIR/core.bak" ]]; then
  rm -rf "$PROJECT_ROOT/core"
  cp -R "$BACKUP_DIR/core.bak" "$PROJECT_ROOT/core"
else
  rm -f "$PROJECT_ROOT/core/metadata/reconciliation.py"
fi

echo "Rollback complete from $BACKUP_DIR"
