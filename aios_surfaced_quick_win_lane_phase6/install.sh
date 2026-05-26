#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="${1:-$HOME/LocalProjects/aios}"
PKG_DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$PROJECT_DIR/backups/surfaced_quick_win_lane_phase6_$STAMP"

if [ ! -d "$PROJECT_DIR" ]; then
  echo "ERROR: Project directory not found: $PROJECT_DIR" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

for f in run_aios.py run_aios_PHASE2_FIXED.py; do
  if [ -f "$PROJECT_DIR/$f" ]; then
    cp -p "$PROJECT_DIR/$f" "$BACKUP_DIR/$f.bak"
  fi
  cp -p "$PKG_DIR/files/$f" "$PROJECT_DIR/$f"
done

echo "$BACKUP_DIR" > "$PROJECT_DIR/.surfaced_quick_win_lane_phase6_last_backup"

echo "Installed AIOS surfaced Quick Win lane Phase 6."
echo "Backup directory: $BACKUP_DIR"
echo
echo "IMPORTANT: Ensure your Tasks database has a checkbox property named: Surfaced Quick Win"
echo "Then set the Quick Wins view filter to:"
echo "  Surfaced Quick Win is checked"
echo "  Done is unchecked"
echo
echo "Run smoke test: bash $PKG_DIR/smoke_test.sh $PROJECT_DIR"
