#!/bin/bash
set -euo pipefail
PROJECT_DIR="${1:-$HOME/LocalProjects/aios}"
MARKER="$PROJECT_DIR/.execution_engine_closed_task_guard_phase2_7_last_backup"

if [ ! -f "$MARKER" ]; then
  echo "No Phase 2.7 backup marker found."
  exit 1
fi

BACKUP_DIR="$(cat "$MARKER")"
cp "$BACKUP_DIR/execution_engine_v2.py.bak" "$PROJECT_DIR/execution_engine_v2.py"
echo "Rollback complete from $BACKUP_DIR"
