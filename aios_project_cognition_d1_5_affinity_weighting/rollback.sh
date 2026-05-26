#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-$PWD}"
BACKUP_FILE="$TARGET/.last_project_cognition_d1_5_backup"
if [ ! -f "$BACKUP_FILE" ]; then
  echo "No D1.5 backup marker found: $BACKUP_FILE" >&2
  exit 1
fi
BACKUP="$(cat "$BACKUP_FILE")"
if [ ! -d "$BACKUP" ]; then
  echo "Backup directory not found: $BACKUP" >&2
  exit 1
fi
cd "$TARGET"
for path in scripts/aios_project_affinity_report.py core/project_cognition/__init__.py core/project_cognition/historical_affinity.py; do
  if [ -e "$BACKUP/$path" ]; then
    cp "$BACKUP/$path" "$TARGET/$path"
  fi
done
echo "Rolled back AIOS Project Cognition D1.5 package from $BACKUP"
