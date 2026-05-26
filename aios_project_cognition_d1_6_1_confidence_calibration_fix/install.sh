#!/usr/bin/env bash
set -euo pipefail
TARGET_DIR="${1:-$(pwd)}"
PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$TARGET_DIR/.aios_project_cognition_d1_6_1_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

backup_if_exists() {
  local rel="$1"
  if [ -e "$TARGET_DIR/$rel" ]; then
    mkdir -p "$BACKUP_DIR/$(dirname "$rel")"
    cp -p "$TARGET_DIR/$rel" "$BACKUP_DIR/$rel"
  fi
}

backup_if_exists "core/project_cognition/__init__.py"
backup_if_exists "core/project_cognition/historical_affinity.py"
backup_if_exists "scripts/aios_project_affinity_report.py"
backup_if_exists "smoke_test_project_cognition_d1_6_1.sh"

mkdir -p "$TARGET_DIR/core/project_cognition" "$TARGET_DIR/scripts"
cp -p "$PACKAGE_DIR/files/core/project_cognition/__init__.py" "$TARGET_DIR/core/project_cognition/__init__.py"
cp -p "$PACKAGE_DIR/files/core/project_cognition/historical_affinity.py" "$TARGET_DIR/core/project_cognition/historical_affinity.py"
cp -p "$PACKAGE_DIR/files/scripts/aios_project_affinity_report.py" "$TARGET_DIR/scripts/aios_project_affinity_report.py"
cp -p "$PACKAGE_DIR/smoke_test_project_cognition_d1_6_1.sh" "$TARGET_DIR/smoke_test_project_cognition_d1_6_1.sh"
chmod +x "$TARGET_DIR/scripts/aios_project_affinity_report.py" "$TARGET_DIR/smoke_test_project_cognition_d1_6_1.sh"

echo "$BACKUP_DIR" > "$TARGET_DIR/.last_project_cognition_d1_6_1_backup"
echo "Installed AIOS Project Cognition D1.6.1 confidence calibration fix package."
echo "Backup: $BACKUP_DIR"
