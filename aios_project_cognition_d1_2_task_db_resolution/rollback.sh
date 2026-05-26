#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-$HOME/LocalProjects/aios}"
BACKUP_DIR="${2:-}"
if [ -z "$BACKUP_DIR" ]; then
  if [ -f "$TARGET/.last_project_cognition_d1_2_backup" ]; then
    BACKUP_DIR="$(cat "$TARGET/.last_project_cognition_d1_2_backup")"
  else
    echo "No backup directory supplied and .last_project_cognition_d1_2_backup not found." >&2
    exit 1
  fi
fi
if [ ! -d "$BACKUP_DIR" ]; then
  echo "Backup directory not found: $BACKUP_DIR" >&2
  exit 1
fi
for path in scripts/aios_project_affinity_report.py core/project_cognition/historical_affinity.py core/project_cognition/__init__.py; do
  if [ -e "$BACKUP_DIR/$path" ]; then
    mkdir -p "$TARGET/$(dirname "$path")"
    cp "$BACKUP_DIR/$path" "$TARGET/$path"
  fi
done
echo "Rolled back AIOS Project Cognition D1.2 from: $BACKUP_DIR"
