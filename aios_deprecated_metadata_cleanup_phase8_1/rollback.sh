#!/usr/bin/env bash
set -euo pipefail
TARGET_DIR="${1:-$PWD}"
cd "$TARGET_DIR"
if [[ ! -f .last_deprecated_metadata_cleanup_phase8_1_backup ]]; then
  echo "No phase 8.1 backup marker found" >&2
  exit 1
fi
BACKUP_DIR="$(cat .last_deprecated_metadata_cleanup_phase8_1_backup)"
if [[ ! -f "$BACKUP_DIR/core/metadata/reconciliation.py" ]]; then
  echo "Backup reconciliation.py not found: $BACKUP_DIR" >&2
  exit 1
fi
cp "$BACKUP_DIR/core/metadata/reconciliation.py" core/metadata/reconciliation.py
echo "Rolled back AIOS deprecated metadata cleanup phase 8.1"
echo "Restored from: $BACKUP_DIR"
