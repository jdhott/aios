#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-$PWD}"
BACKUP_DIR="$TARGET_DIR/.last_project_cognition_d1_1_database_discovery_backup"

if [[ ! -f "$BACKUP_DIR/latest" ]]; then
  echo "No D1.1 backup marker found at $BACKUP_DIR/latest" >&2
  exit 1
fi

STAMP="$(cat "$BACKUP_DIR/latest")"
SRC="$BACKUP_DIR/$STAMP"

if [[ ! -d "$SRC" ]]; then
  echo "Backup directory not found: $SRC" >&2
  exit 1
fi

restore_file() {
  local rel="$1"
  if [[ -f "$SRC/$rel" ]]; then
    mkdir -p "$TARGET_DIR/$(dirname "$rel")"
    cp "$SRC/$rel" "$TARGET_DIR/$rel"
  fi
}

restore_file "scripts/aios_project_affinity_report.py"
restore_file "core/project_cognition/historical_affinity.py"
restore_file "core/project_cognition/__init__.py"

echo "Rolled back AIOS Project Cognition D1.1 from backup $SRC"
