#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$(pwd)}"
PATCH_NAME="canonical_metadata_reconciliation_phase7_compact_governance_logging"
LAST_FILE="$PROJECT_ROOT/.last_${PATCH_NAME}_backup"

if [[ ! -f "$LAST_FILE" ]]; then
  echo "ERROR: No backup marker found: $LAST_FILE" >&2
  exit 1
fi
BACKUP_DIR="$(cat "$LAST_FILE")"
if [[ ! -d "$BACKUP_DIR" ]]; then
  echo "ERROR: Backup directory not found: $BACKUP_DIR" >&2
  exit 1
fi

cp "$BACKUP_DIR/core/metadata/reconciliation.py" "$PROJECT_ROOT/core/metadata/reconciliation.py"
cp "$BACKUP_DIR/execution_engine_v2.py" "$PROJECT_ROOT/execution_engine_v2.py"
if [[ -f "$BACKUP_DIR/core/metadata/policy.py.__MISSING__" ]]; then
  rm -f "$PROJECT_ROOT/core/metadata/policy.py"
else
  cp "$BACKUP_DIR/core/metadata/policy.py" "$PROJECT_ROOT/core/metadata/policy.py"
fi
python3 -m py_compile "$PROJECT_ROOT/core/metadata/reconciliation.py" "$PROJECT_ROOT/execution_engine_v2.py"
if [[ -f "$PROJECT_ROOT/core/metadata/policy.py" ]]; then
  python3 -m py_compile "$PROJECT_ROOT/core/metadata/policy.py"
fi

echo "Rolled back $PATCH_NAME from $BACKUP_DIR"
