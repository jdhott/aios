#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-$HOME/LocalProjects/aios}"
PKG_DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$TARGET/.aios_project_cognition_d1_2_backup_$STAMP"
mkdir -p "$BACKUP_DIR"
mkdir -p "$TARGET/scripts" "$TARGET/core/project_cognition"
for path in scripts/aios_project_affinity_report.py core/project_cognition/historical_affinity.py core/project_cognition/__init__.py; do
  if [ -e "$TARGET/$path" ]; then
    mkdir -p "$BACKUP_DIR/$(dirname "$path")"
    cp "$TARGET/$path" "$BACKUP_DIR/$path"
  fi
  mkdir -p "$TARGET/$(dirname "$path")"
  cp "$PKG_DIR/files/$path" "$TARGET/$path"
done
chmod +x "$TARGET/scripts/aios_project_affinity_report.py"
echo "$BACKUP_DIR" > "$TARGET/.last_project_cognition_d1_2_backup"
echo "Installed AIOS Project Cognition D1.2 task DB resolution package."
echo "Backup: $BACKUP_DIR"
