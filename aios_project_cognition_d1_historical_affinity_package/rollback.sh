#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$PWD}"
MARKER="$ROOT/.aios_project_cognition_d1_install"
if [ ! -f "$MARKER" ]; then
  echo "No install marker found at $MARKER"
  exit 1
fi
BACKUP_DIR="$(grep '^backup_dir=' "$MARKER" | cut -d= -f2-)"
if [ -z "$BACKUP_DIR" ] || [ ! -d "$BACKUP_DIR" ]; then
  echo "Backup directory missing: $BACKUP_DIR"
  exit 1
fi
rm -rf "$ROOT/core/project_cognition" "$ROOT/scripts/aios_project_affinity_report.py"
if [ -e "$BACKUP_DIR/core/project_cognition" ]; then
  mkdir -p "$ROOT/core"
  cp -R "$BACKUP_DIR/core/project_cognition" "$ROOT/core/project_cognition"
fi
if [ -e "$BACKUP_DIR/scripts/aios_project_affinity_report.py" ]; then
  mkdir -p "$ROOT/scripts"
  cp "$BACKUP_DIR/scripts/aios_project_affinity_report.py" "$ROOT/scripts/aios_project_affinity_report.py"
fi
rm -f "$MARKER"
echo "Rollback complete."
