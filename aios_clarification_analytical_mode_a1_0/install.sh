#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$ROOT/.aios_clarification_analytical_mode_a1_0_backup_$STAMP"
LAST_FILE="$ROOT/.last_aios_clarification_analytical_mode_a1_0_backup"

echo "=== Installing AIOS Clarification Analytical Mode A1.0 ==="
echo "Root: $ROOT"

mkdir -p "$BACKUP_DIR/aios"

for f in run_aios.py aios/clarification.py; do
  if [[ ! -f "$ROOT/$f" ]]; then
    echo "ERROR: Expected file missing: $ROOT/$f" >&2
    exit 1
  fi
done

cp "$ROOT/run_aios.py" "$BACKUP_DIR/run_aios.py"
cp "$ROOT/aios/clarification.py" "$BACKUP_DIR/aios/clarification.py"
echo "$BACKUP_DIR" > "$LAST_FILE"

cp "$PKG_DIR/files/run_aios.py" "$ROOT/run_aios.py"
mkdir -p "$ROOT/aios"
cp "$PKG_DIR/files/aios/clarification.py" "$ROOT/aios/clarification.py"

python3 -m py_compile "$ROOT/run_aios.py" "$ROOT/aios/clarification.py"

echo "Installed successfully."
echo "Backup: $BACKUP_DIR"
echo "Run: bash $PKG_DIR/smoke_test.sh $ROOT"
