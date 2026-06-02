#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"
MARKER="$ROOT/.last_canonical_execution_metadata_fix_backup"

if [[ ! -f "$MARKER" ]]; then
  echo "ERROR: No backup marker found at $MARKER" >&2
  exit 1
fi

BACKUP_DIR="$(cat "$MARKER")"
if [[ ! -d "$BACKUP_DIR" ]]; then
  echo "ERROR: Backup directory not found: $BACKUP_DIR" >&2
  exit 1
fi

cp "$BACKUP_DIR/execution_engine_v2.py" "$ROOT/execution_engine_v2.py"
cp "$BACKUP_DIR/run_aios.py" "$ROOT/run_aios.py"
cp "$BACKUP_DIR/core/evaluator.py" "$ROOT/core/evaluator.py"
cp "$BACKUP_DIR/aios/clarification.py" "$ROOT/aios/clarification.py"

python3 -m py_compile \
  "$ROOT/execution_engine_v2.py" \
  "$ROOT/run_aios.py" \
  "$ROOT/core/evaluator.py" \
  "$ROOT/aios/clarification.py"

echo "Rollback complete from: $BACKUP_DIR"
