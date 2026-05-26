#!/usr/bin/env bash
set -euo pipefail
TARGET_DIR="${1:-$PWD}"
cd "$TARGET_DIR"
if [[ ! -f .last_governance_observation_baseline_phase8_2_backup ]]; then
  echo "No phase 8.2 backup marker found" >&2
  exit 1
fi
BACKUP_DIR="$(cat .last_governance_observation_baseline_phase8_2_backup)"
if [[ ! -f "$BACKUP_DIR/core/metadata/reconciliation.py" ]]; then
  echo "Backup reconciliation.py not found: $BACKUP_DIR" >&2
  exit 1
fi
cp "$BACKUP_DIR/core/metadata/reconciliation.py" core/metadata/reconciliation.py
echo "Rolled back AIOS governance observation baseline phase 8.2"
echo "Restored from: $BACKUP_DIR"
