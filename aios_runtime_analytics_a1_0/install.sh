#!/bin/bash
set -euo pipefail

ROOT="$(pwd)"
PKG_DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$ROOT/.aios_runtime_analytics_a1_0_backup_$STAMP"

if [ ! -f "$ROOT/execution_engine_v2.py" ]; then
  echo "ERROR: Run this installer from the AIOS project root."
  exit 1
fi

mkdir -p "$BACKUP_DIR"
cp "$ROOT/execution_engine_v2.py" "$BACKUP_DIR/execution_engine_v2.py"
if [ -f "$ROOT/core/runtime_analytics.py" ]; then
  mkdir -p "$BACKUP_DIR/core"
  cp "$ROOT/core/runtime_analytics.py" "$BACKUP_DIR/core/runtime_analytics.py"
fi
echo "$BACKUP_DIR" > "$ROOT/.last_aios_runtime_analytics_a1_0_backup"

mkdir -p "$ROOT/core"
cp "$PKG_DIR/files/core/runtime_analytics.py" "$ROOT/core/runtime_analytics.py"

python3 "$PKG_DIR/patch_runtime_analytics.py"

./venv/bin/python -m py_compile "$ROOT/execution_engine_v2.py" "$ROOT/core/runtime_analytics.py"

echo "Installed AIOS Runtime Analytics A1.0"
echo "Backup: $BACKUP_DIR"
echo "Next: bash aios_runtime_analytics_a1_0/smoke_test.sh"
