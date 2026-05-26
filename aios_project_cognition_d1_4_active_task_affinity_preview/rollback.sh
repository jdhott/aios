#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-$PWD}"
BACKUP_MARKER="$TARGET_DIR/.last_aios_project_cognition_d1_4_backup"

if [ ! -f "$BACKUP_MARKER" ]; then
  echo "No D1.4 backup marker found: $BACKUP_MARKER" >&2
  exit 1
fi

BACKUP_DIR="$(cat "$BACKUP_MARKER")"
if [ ! -d "$BACKUP_DIR" ]; then
  echo "Backup directory not found: $BACKUP_DIR" >&2
  exit 1
fi

restore_if_exists() {
  local rel="$1"
  if [ -e "$BACKUP_DIR/$rel" ]; then
    mkdir -p "$TARGET_DIR/$(dirname "$rel")"
    cp -p "$BACKUP_DIR/$rel" "$TARGET_DIR/$rel"
    echo "Restored $rel"
  fi
}

restore_if_exists "scripts/aios_project_affinity_report.py"
restore_if_exists "core/project_cognition/historical_affinity.py"
restore_if_exists "core/project_cognition/__init__.py"
restore_if_exists "smoke_test_project_cognition_d1_3.sh"
restore_if_exists "smoke_test_project_cognition_d1_4.sh"

echo "Rollback complete from $BACKUP_DIR"
