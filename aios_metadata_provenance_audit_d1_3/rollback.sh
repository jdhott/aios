#!/usr/bin/env bash
set -euo pipefail
cd "$(pwd)"
MARKER=".last_metadata_provenance_audit_d1_3_backup"
if [[ ! -f "$MARKER" ]]; then
  echo "No D1.3 backup marker found"
  exit 1
fi
BACKUP_DIR="$(cat "$MARKER")"
if [[ ! -f "$BACKUP_DIR/execution_engine_v2.py" ]]; then
  echo "Backup file not found: $BACKUP_DIR/execution_engine_v2.py"
  exit 1
fi
cp "$BACKUP_DIR/execution_engine_v2.py" execution_engine_v2.py
python3 -m py_compile execution_engine_v2.py
echo "Rolled back AIOS Metadata Provenance Audit D1.3"
