#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-$PWD}"
PACKAGE_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$TARGET_DIR/.aios_project_cognition_d1_4_backup_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"
mkdir -p "$TARGET_DIR/scripts" "$TARGET_DIR/core/project_cognition"

backup_if_exists() {
  local rel="$1"
  if [ -e "$TARGET_DIR/$rel" ]; then
    mkdir -p "$BACKUP_DIR/$(dirname "$rel")"
    cp -p "$TARGET_DIR/$rel" "$BACKUP_DIR/$rel"
  fi
}

backup_if_exists "scripts/aios_project_affinity_report.py"
backup_if_exists "core/project_cognition/historical_affinity.py"
backup_if_exists "core/project_cognition/__init__.py"
backup_if_exists "smoke_test_project_cognition_d1_3.sh"
backup_if_exists "smoke_test_project_cognition_d1_4.sh"

cp "$PACKAGE_DIR/files/scripts/aios_project_affinity_report.py" "$TARGET_DIR/scripts/aios_project_affinity_report.py"
cp "$PACKAGE_DIR/files/core/project_cognition/historical_affinity.py" "$TARGET_DIR/core/project_cognition/historical_affinity.py"
cp "$PACKAGE_DIR/files/core/project_cognition/__init__.py" "$TARGET_DIR/core/project_cognition/__init__.py"
cp "$PACKAGE_DIR/smoke_test_project_cognition_d1_4.sh" "$TARGET_DIR/smoke_test_project_cognition_d1_4.sh"
chmod +x "$TARGET_DIR/scripts/aios_project_affinity_report.py" "$TARGET_DIR/smoke_test_project_cognition_d1_4.sh"

echo "$BACKUP_DIR" > "$TARGET_DIR/.last_aios_project_cognition_d1_4_backup"

echo "Installed AIOS Project Cognition D1.4 active-task affinity preview package."
echo "Backup: $BACKUP_DIR"
