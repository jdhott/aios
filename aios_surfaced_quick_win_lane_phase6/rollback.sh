#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="${1:-$HOME/LocalProjects/aios}"
MARKER="$PROJECT_DIR/.surfaced_quick_win_lane_phase6_last_backup"

if [ ! -f "$MARKER" ]; then
  echo "ERROR: Backup marker not found: $MARKER" >&2
  exit 1
fi

BACKUP_DIR="$(cat "$MARKER")"
if [ ! -d "$BACKUP_DIR" ]; then
  echo "ERROR: Backup directory not found: $BACKUP_DIR" >&2
  exit 1
fi

for f in run_aios.py run_aios_PHASE2_FIXED.py; do
  if [ -f "$BACKUP_DIR/$f.bak" ]; then
    cp -p "$BACKUP_DIR/$f.bak" "$PROJECT_DIR/$f"
    echo "Restored $f"
  fi
done

echo "Rollback complete from: $BACKUP_DIR"
