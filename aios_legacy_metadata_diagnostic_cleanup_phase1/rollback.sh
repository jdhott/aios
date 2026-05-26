#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$(pwd)}"
PATCH_NAME="legacy_metadata_diagnostic_cleanup_phase1"
LAST_BACKUP_FILE="$PROJECT_ROOT/.last_${PATCH_NAME}_backup"

if [[ ! -f "$LAST_BACKUP_FILE" ]]; then
  echo "ERROR: No backup marker found: $LAST_BACKUP_FILE" >&2
  exit 1
fi

BACKUP_DIR="$(cat "$LAST_BACKUP_FILE")"
BACKUP_FILE="$BACKUP_DIR/core/metadata/reconciliation.py"
TARGET_FILE="$PROJECT_ROOT/core/metadata/reconciliation.py"

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "ERROR: Backup file not found: $BACKUP_FILE" >&2
  exit 1
fi

cp "$BACKUP_FILE" "$TARGET_FILE"
python3 -m py_compile "$TARGET_FILE"

echo "Rolled back $PATCH_NAME"
echo "Restored: $TARGET_FILE"
echo "From: $BACKUP_FILE"
