#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$ROOT/.canonical_execution_metadata_fix_backup_$STAMP"

if [[ ! -f "$ROOT/run_aios.py" || ! -f "$ROOT/execution_engine_v2.py" ]]; then
  echo "ERROR: Run from the AIOS project root, or pass the AIOS project root as the first argument." >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR/core" "$BACKUP_DIR/aios"
cp "$ROOT/execution_engine_v2.py" "$BACKUP_DIR/execution_engine_v2.py"
cp "$ROOT/run_aios.py" "$BACKUP_DIR/run_aios.py"
cp "$ROOT/core/evaluator.py" "$BACKUP_DIR/core/evaluator.py"
cp "$ROOT/aios/clarification.py" "$BACKUP_DIR/aios/clarification.py"

cp "$(dirname "$0")/files/execution_engine_v2.py" "$ROOT/execution_engine_v2.py"
cp "$(dirname "$0")/files/run_aios.py" "$ROOT/run_aios.py"
cp "$(dirname "$0")/files/core/evaluator.py" "$ROOT/core/evaluator.py"
cp "$(dirname "$0")/files/aios/clarification.py" "$ROOT/aios/clarification.py"

echo "$BACKUP_DIR" > "$ROOT/.last_canonical_execution_metadata_fix_backup"

python3 -m py_compile \
  "$ROOT/execution_engine_v2.py" \
  "$ROOT/run_aios.py" \
  "$ROOT/core/evaluator.py" \
  "$ROOT/aios/clarification.py"

echo "Installed canonical execution metadata fix."
echo "Backup: $BACKUP_DIR"
echo "Next: bash $(dirname "$0")/smoke_test.sh $ROOT"
