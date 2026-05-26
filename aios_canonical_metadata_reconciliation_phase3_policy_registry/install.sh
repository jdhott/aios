#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$(pwd)}"
PATCH_NAME="canonical_metadata_reconciliation_phase3_policy_registry"
BACKUP_DIR="$PROJECT_ROOT/.${PATCH_NAME}_backup_$(date +%Y%m%d_%H%M%S)"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET_RECON="$PROJECT_ROOT/core/metadata/reconciliation.py"
TARGET_POLICY="$PROJECT_ROOT/core/metadata/policy.py"
SOURCE_RECON="$SOURCE_DIR/core/metadata/reconciliation.py"
SOURCE_POLICY="$SOURCE_DIR/core/metadata/policy.py"

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
if [[ ! -f "$SOURCE_RECON" || ! -f "$SOURCE_POLICY" ]]; then
  echo "ERROR: Package source files missing" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR/core/metadata"
cp "$TARGET_RECON" "$BACKUP_DIR/core/metadata/reconciliation.py"
if [[ -f "$TARGET_POLICY" ]]; then
  cp "$TARGET_POLICY" "$BACKUP_DIR/core/metadata/policy.py"
else
  touch "$BACKUP_DIR/core/metadata/policy.py.__MISSING__"
fi

cp "$SOURCE_RECON" "$TARGET_RECON"
cp "$SOURCE_POLICY" "$TARGET_POLICY"

python3 -m py_compile "$TARGET_POLICY" "$TARGET_RECON"

echo "$BACKUP_DIR" > "$PROJECT_ROOT/.last_${PATCH_NAME}_backup"
echo "Installed $PATCH_NAME"
echo "Backup: $BACKUP_DIR"
echo "Updated: $TARGET_RECON"
echo "Added/updated: $TARGET_POLICY"
