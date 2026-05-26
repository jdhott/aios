#!/usr/bin/env bash
set -euo pipefail
TARGET_DIR="${1:-$PWD}"
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$TARGET_DIR/.governance_observation_baseline_phase8_2_backup_$STAMP"

cd "$TARGET_DIR"
mkdir -p "$BACKUP_DIR/core/metadata"
if [[ -f core/metadata/reconciliation.py ]]; then
  cp core/metadata/reconciliation.py "$BACKUP_DIR/core/metadata/reconciliation.py"
fi
mkdir -p core/metadata
cp "$PKG_DIR/core/metadata/reconciliation.py" core/metadata/reconciliation.py
printf '%s\n' "$BACKUP_DIR" > .last_governance_observation_baseline_phase8_2_backup

echo "Installed AIOS governance observation baseline phase 8.2"
echo "Backup: $BACKUP_DIR"
echo "Next: bash $PKG_DIR/smoke_test.sh $TARGET_DIR"
