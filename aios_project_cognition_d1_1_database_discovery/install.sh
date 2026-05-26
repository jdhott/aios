#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-$PWD}"
PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$TARGET_DIR/.last_project_cognition_d1_1_database_discovery_backup"
STAMP="$(date +%Y%m%d_%H%M%S)"

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "Target directory does not exist: $TARGET_DIR" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR/$STAMP/scripts" "$BACKUP_DIR/$STAMP/core/project_cognition"

backup_file() {
  local rel="$1"
  if [[ -f "$TARGET_DIR/$rel" ]]; then
    mkdir -p "$BACKUP_DIR/$STAMP/$(dirname "$rel")"
    cp "$TARGET_DIR/$rel" "$BACKUP_DIR/$STAMP/$rel"
  fi
}

install_file() {
  local rel="$1"
  mkdir -p "$TARGET_DIR/$(dirname "$rel")"
  cp "$PACKAGE_DIR/$rel" "$TARGET_DIR/$rel"
}

backup_file "scripts/aios_project_affinity_report.py"
backup_file "core/project_cognition/historical_affinity.py"
backup_file "core/project_cognition/__init__.py"

install_file "scripts/aios_project_affinity_report.py"
install_file "core/project_cognition/historical_affinity.py"
install_file "core/project_cognition/__init__.py"
cp "$PACKAGE_DIR/smoke_test.sh" "$TARGET_DIR/smoke_test_project_cognition_d1_1.sh"
cp "$PACKAGE_DIR/rollback.sh" "$TARGET_DIR/rollback_project_cognition_d1_1.sh"
chmod +x "$TARGET_DIR/scripts/aios_project_affinity_report.py" "$TARGET_DIR/smoke_test_project_cognition_d1_1.sh" "$TARGET_DIR/rollback_project_cognition_d1_1.sh"

cat > "$BACKUP_DIR/latest" <<EOF
$STAMP
EOF

echo "Installed AIOS Project Cognition D1.1 database discovery hardening."
echo "Backup: $BACKUP_DIR/$STAMP"
echo "Run: cd $TARGET_DIR && bash smoke_test_project_cognition_d1_1.sh"
