#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$PWD}"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$ROOT/backups/aios_project_cognition_d1_$STAMP"

echo "Installing AIOS Project Cognition D1 package into: $ROOT"
mkdir -p "$BACKUP_DIR"

backup_if_exists() {
  local path="$1"
  if [ -e "$ROOT/$path" ]; then
    mkdir -p "$BACKUP_DIR/$(dirname "$path")"
    cp -R "$ROOT/$path" "$BACKUP_DIR/$path"
  fi
}

backup_if_exists "core/project_cognition"
backup_if_exists "scripts/aios_project_affinity_report.py"

mkdir -p "$ROOT/core/project_cognition" "$ROOT/scripts"
cp -R "$(dirname "$0")/core/project_cognition/"* "$ROOT/core/project_cognition/"
cp "$(dirname "$0")/scripts/aios_project_affinity_report.py" "$ROOT/scripts/aios_project_affinity_report.py"
chmod +x "$ROOT/scripts/aios_project_affinity_report.py"

cat > "$ROOT/.aios_project_cognition_d1_install" <<EOF
backup_dir=$BACKUP_DIR
installed_at=$STAMP
EOF

echo "Installed read-only historical affinity telemetry."
echo "Backup directory: $BACKUP_DIR"
echo "Run smoke test: bash smoke_test.sh $ROOT"
echo "Run report: ./venv/bin/python scripts/aios_project_affinity_report.py"
