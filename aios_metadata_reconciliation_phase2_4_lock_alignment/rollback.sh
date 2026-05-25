#!/bin/bash
set -euo pipefail
PROJECT_DIR="${1:-$HOME/LocalProjects/aios}"
cd "$PROJECT_DIR"

LATEST="$(ls -td backups/metadata_reconciliation_phase2_4_* 2>/dev/null | head -1 || true)"
if [ -z "$LATEST" ]; then
  echo "No Phase 2.4 backup found."
  exit 1
fi

if [ -f "$LATEST/run.sh.bak" ]; then
  cp "$LATEST/run.sh.bak" run.sh
  chmod +x run.sh
  echo "Restored run.sh from $LATEST"
fi
