#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$(pwd)}"
PATCH_NAME="canonical_metadata_reconciliation_phase7_compact_governance_logging"
BACKUP_DIR="$PROJECT_ROOT/.${PATCH_NAME}_backup_$(date +%Y%m%d_%H%M%S)"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET_RECON="$PROJECT_ROOT/core/metadata/reconciliation.py"
TARGET_POLICY="$PROJECT_ROOT/core/metadata/policy.py"
TARGET_ENGINE="$PROJECT_ROOT/execution_engine_v2.py"
SOURCE_RECON="$SOURCE_DIR/core/metadata/reconciliation.py"
SOURCE_POLICY="$SOURCE_DIR/core/metadata/policy.py"
SOURCE_ENGINE="$SOURCE_DIR/execution_engine_v2.py"

if [[ ! -d "$PROJECT_ROOT" ]]; then
  echo "ERROR: Project root does not exist: $PROJECT_ROOT" >&2
  exit 1
fi
if [[ ! -d "$PROJECT_ROOT/core/metadata" ]]; then
  echo "ERROR: Expected metadata package not found: $PROJECT_ROOT/core/metadata" >&2
  exit 1
fi
for f in "$TARGET_RECON" "$TARGET_ENGINE"; do
  if [[ ! -f "$f" ]]; then
    echo "ERROR: Target file not found: $f" >&2
    exit 1
  fi
done
for f in "$SOURCE_RECON" "$SOURCE_POLICY" "$SOURCE_ENGINE"; do
  if [[ ! -f "$f" ]]; then
    echo "ERROR: Package source file missing: $f" >&2
    exit 1
  fi
done

mkdir -p "$BACKUP_DIR/core/metadata"
cp "$TARGET_RECON" "$BACKUP_DIR/core/metadata/reconciliation.py"
cp "$TARGET_ENGINE" "$BACKUP_DIR/execution_engine_v2.py"
if [[ -f "$TARGET_POLICY" ]]; then
  cp "$TARGET_POLICY" "$BACKUP_DIR/core/metadata/policy.py"
else
  touch "$BACKUP_DIR/core/metadata/policy.py.__MISSING__"
fi

cp "$SOURCE_RECON" "$TARGET_RECON"
cp "$SOURCE_POLICY" "$TARGET_POLICY"
cp "$SOURCE_ENGINE" "$TARGET_ENGINE"

python3 -m py_compile "$TARGET_POLICY" "$TARGET_RECON" "$TARGET_ENGINE"

echo "$BACKUP_DIR" > "$PROJECT_ROOT/.last_${PATCH_NAME}_backup"
echo "Installed $PATCH_NAME"
echo "Backup: $BACKUP_DIR"
echo "Updated: $TARGET_RECON"
echo "Updated: $TARGET_POLICY"
echo "Updated: $TARGET_ENGINE"
