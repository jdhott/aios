#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-$PWD}"
PACKAGE_DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$TARGET/.aios_project_cognition_d1_5_backup_$STAMP"
mkdir -p "$BACKUP"

cd "$TARGET"
mkdir -p scripts core/project_cognition

for path in scripts/aios_project_affinity_report.py core/project_cognition/__init__.py core/project_cognition/historical_affinity.py; do
  if [ -e "$path" ]; then
    mkdir -p "$BACKUP/$(dirname "$path")"
    cp "$path" "$BACKUP/$path"
  fi
done

cp "$PACKAGE_DIR/files/scripts/aios_project_affinity_report.py" "$TARGET/scripts/aios_project_affinity_report.py"
cp "$PACKAGE_DIR/files/core/project_cognition/__init__.py" "$TARGET/core/project_cognition/__init__.py"
cp "$PACKAGE_DIR/files/core/project_cognition/historical_affinity.py" "$TARGET/core/project_cognition/historical_affinity.py"
cp "$PACKAGE_DIR/smoke_test_project_cognition_d1_5.sh" "$TARGET/smoke_test_project_cognition_d1_5.sh"
chmod +x "$TARGET/scripts/aios_project_affinity_report.py" "$TARGET/smoke_test_project_cognition_d1_5.sh"

cat > "$TARGET/.last_project_cognition_d1_5_backup" <<EOF
$BACKUP
EOF

echo "Installed AIOS Project Cognition D1.5 affinity weighting package."
echo "Backup: $BACKUP"
