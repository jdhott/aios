#!/usr/bin/env bash
set -euo pipefail
TARGET_DIR="${1:-$(pwd)}"
BACKUP_FILE="$TARGET_DIR/.last_project_cognition_d1_7_backup"
if [ ! -f "$BACKUP_FILE" ]; then
  echo "No D1.7 backup marker found: $BACKUP_FILE" >&2
  exit 1
fi
BACKUP_DIR="$(cat "$BACKUP_FILE")"
if [ ! -d "$BACKUP_DIR" ]; then
  echo "Backup directory not found: $BACKUP_DIR" >&2
  exit 1
fi
for rel in core/project_cognition/__init__.py core/project_cognition/historical_affinity.py scripts/aios_project_affinity_report.py smoke_test_project_cognition_d1_7.sh; do
  if [ -e "$BACKUP_DIR/$rel" ]; then
    mkdir -p "$TARGET_DIR/$(dirname "$rel")"
    cp -p "$BACKUP_DIR/$rel" "$TARGET_DIR/$rel"
  fi
done
echo "Rolled back AIOS Project Cognition D1.7 from $BACKUP_DIR"
