#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$ROOT/.aios_evaluator_tuning_telemetry_d1_0_backup_$STAMP"

if [[ ! -f "$ROOT/execution_engine_v2.py" ]]; then
  echo "ERROR: execution_engine_v2.py not found in $ROOT"
  echo "Run from the AIOS project root, or pass the project root as the first argument."
  exit 1
fi

mkdir -p "$BACKUP_DIR"
cp "$ROOT/execution_engine_v2.py" "$BACKUP_DIR/execution_engine_v2.py"

cp "$PKG_DIR/files/execution_engine_v2.py" "$ROOT/execution_engine_v2.py"
cp "$PKG_DIR/tools/smoke_test_evaluator_tuning_telemetry.py" "$ROOT/smoke_test_evaluator_tuning_telemetry.py"
chmod +x "$ROOT/smoke_test_evaluator_tuning_telemetry.py"

echo "$BACKUP_DIR" > "$ROOT/.last_evaluator_tuning_telemetry_d1_0_backup"

python3 -m py_compile "$ROOT/execution_engine_v2.py"

echo "Installed AIOS Evaluator Tuning Telemetry D1.0"
echo "Backup: $BACKUP_DIR"
echo "Next: bash smoke_test.sh"
