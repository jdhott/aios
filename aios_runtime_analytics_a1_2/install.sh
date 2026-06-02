#!/usr/bin/env bash
set -euo pipefail

PKG="AIOS Runtime Analytics A1.2"
ROOT="$(pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$ROOT/.aios_runtime_analytics_a1_2_backup_$STAMP"

if [[ ! -f "$ROOT/execution_engine_v2.py" ]]; then
  echo "ERROR: Run install.sh from the AIOS project root." >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR/core"
cp "$ROOT/execution_engine_v2.py" "$BACKUP_DIR/execution_engine_v2.py"
if [[ -f "$ROOT/core/runtime_analytics.py" ]]; then
  cp "$ROOT/core/runtime_analytics.py" "$BACKUP_DIR/core/runtime_analytics.py"
fi
if [[ -f "$ROOT/logs/runtime_analytics.csv" ]]; then
  mkdir -p "$BACKUP_DIR/logs"
  cp "$ROOT/logs/runtime_analytics.csv" "$BACKUP_DIR/logs/runtime_analytics.csv"
fi

mkdir -p "$ROOT/core"
cp "$(dirname "$0")/files/core/runtime_analytics.py" "$ROOT/core/runtime_analytics.py"
python3 "$(dirname "$0")/patch_runtime_analytics_a1_2.py"

python3 -m py_compile "$ROOT/execution_engine_v2.py" "$ROOT/core/runtime_analytics.py"

echo "Installed $PKG"
echo "Backup: $BACKUP_DIR"
echo "Next: bash aios_runtime_analytics_a1_2/smoke_test.sh"
