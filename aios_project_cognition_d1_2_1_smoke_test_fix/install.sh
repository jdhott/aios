#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-$HOME/LocalProjects/aios}"
PKG_DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$TARGET/.aios_project_cognition_d1_2_1_backup_$STAMP"
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
# Install smoke test at project root so it matches the documented command.
if [ -e "$TARGET/smoke_test_project_cognition_d1_2_1.sh" ]; then
  cp "$TARGET/smoke_test_project_cognition_d1_2_1.sh" "$BACKUP_DIR/smoke_test_project_cognition_d1_2_1.sh"
fi
cp "$PKG_DIR/smoke_test_project_cognition_d1_2_1.sh" "$TARGET/smoke_test_project_cognition_d1_2_1.sh"
chmod +x "$TARGET/scripts/aios_project_affinity_report.py" "$TARGET/smoke_test_project_cognition_d1_2_1.sh"
echo "$BACKUP_DIR" > "$TARGET/.last_project_cognition_d1_2_1_backup"
echo "Installed AIOS Project Cognition D1.2.1 smoke test fix package."
echo "Backup: $BACKUP_DIR"
