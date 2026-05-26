#!/usr/bin/env bash
set -euo pipefail
TARGET_DIR="${1:-$(pwd)}"
BACKUP_FILE="$TARGET_DIR/.last_project_cognition_d1_6_backup"
if [ ! -f "$BACKUP_FILE" ]; then
  echo "No D1.6 backup marker found: $BACKUP_FILE" >&2
  exit 1
fi
BACKUP_DIR="$(cat "$BACKUP_FILE")"
if [ ! -d "$BACKUP_DIR" ]; then
  echo "Backup directory not found: $BACKUP_DIR" >&2
  exit 1
fi
restore_if_exists() {
  local rel="$1"
  if [ -e "$BACKUP_DIR/$rel" ]; then
    mkdir -p "$TARGET_DIR/$(dirname "$rel")"
    cp -p "$BACKUP_DIR/$rel" "$TARGET_DIR/$rel"
  fi
}
restore_if_exists "core/project_cognition/__init__.py"
restore_if_exists "core/project_cognition/historical_affinity.py"
restore_if_exists "scripts/aios_project_affinity_report.py"
restore_if_exists "smoke_test_project_cognition_d1_6.sh"
echo "Rolled back AIOS Project Cognition D1.6 from backup: $BACKUP_DIR"
