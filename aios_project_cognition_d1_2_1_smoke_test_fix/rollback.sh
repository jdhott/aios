#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-$HOME/LocalProjects/aios}"
if [ ! -f "$TARGET/.last_project_cognition_d1_2_1_backup" ]; then
  echo "No D1.2.1 backup marker found."
  exit 1
fi
BACKUP_DIR="$(cat "$TARGET/.last_project_cognition_d1_2_1_backup")"
if [ ! -d "$BACKUP_DIR" ]; then
  echo "Backup directory not found: $BACKUP_DIR"
  exit 1
fi
for path in scripts/aios_project_affinity_report.py core/project_cognition/historical_affinity.py core/project_cognition/__init__.py smoke_test_project_cognition_d1_2_1.sh; do
  if [ -e "$BACKUP_DIR/$path" ]; then
    mkdir -p "$TARGET/$(dirname "$path")"
    cp "$BACKUP_DIR/$path" "$TARGET/$path"
  else
    rm -f "$TARGET/$path"
  fi
done
echo "Rolled back AIOS Project Cognition D1.2.1 package."
