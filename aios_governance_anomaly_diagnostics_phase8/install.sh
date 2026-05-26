#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$(pwd)}"
PATCH_NAME="governance_anomaly_diagnostics_phase8"
BACKUP_DIR="$PROJECT_ROOT/.${PATCH_NAME}_backup_$(date +%Y%m%d_%H%M%S)"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET_RECON="$PROJECT_ROOT/core/metadata/reconciliation.py"
SOURCE_RECON="$SOURCE_DIR/core/metadata/reconciliation.py"

if [[ ! -d "$PROJECT_ROOT" ]]; then
  echo "ERROR: Project root does not exist: $PROJECT_ROOT" >&2
  exit 1
fi
if [[ ! -d "$PROJECT_ROOT/core/metadata" ]]; then
  echo "ERROR: Expected metadata package not found: $PROJECT_ROOT/core/metadata" >&2
  exit 1
fi
if [[ ! -f "$TARGET_RECON" ]]; then
  echo "ERROR: Target reconciliation file not found: $TARGET_RECON" >&2
  exit 1
fi
if [[ ! -f "$SOURCE_RECON" ]]; then
  echo "ERROR: Package source file missing: $SOURCE_RECON" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR/core/metadata"
cp "$TARGET_RECON" "$BACKUP_DIR/core/metadata/reconciliation.py"

cp "$SOURCE_RECON" "$TARGET_RECON"
python3 -m py_compile "$TARGET_RECON"

echo "$BACKUP_DIR" > "$PROJECT_ROOT/.last_${PATCH_NAME}_backup"
echo "Installed $PATCH_NAME"
echo "Backup: $BACKUP_DIR"
echo "Updated: $TARGET_RECON"
echo ""
echo "Recommended commands:"
echo "cd $PROJECT_ROOT"
echo "bash $SOURCE_DIR/smoke_test.sh $PROJECT_ROOT"
echo "python3 run_aios.py 2>&1 | tee test_run.log"
echo "grep -E 'GOVERNANCE ANOMALY|Anomaly health|Metadata Governance|Errors:' test_run.log"
