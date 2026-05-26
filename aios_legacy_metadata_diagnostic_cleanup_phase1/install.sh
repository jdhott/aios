#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$(pwd)}"
PATCH_NAME="legacy_metadata_diagnostic_cleanup_phase1"
BACKUP_DIR="$PROJECT_ROOT/.${PATCH_NAME}_backup_$(date +%Y%m%d_%H%M%S)"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_FILE="$PROJECT_ROOT/core/metadata/reconciliation.py"
SOURCE_FILE="$SOURCE_DIR/core/metadata/reconciliation.py"

if [[ ! -d "$PROJECT_ROOT" ]]; then
  echo "ERROR: Project root does not exist: $PROJECT_ROOT" >&2
  exit 1
fi

if [[ ! -f "$TARGET_FILE" ]]; then
  echo "ERROR: Target file not found: $TARGET_FILE" >&2
  exit 1
fi

if [[ ! -f "$SOURCE_FILE" ]]; then
  echo "ERROR: Package source file missing: $SOURCE_FILE" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR/core/metadata"
cp "$TARGET_FILE" "$BACKUP_DIR/core/metadata/reconciliation.py"
cp "$SOURCE_FILE" "$TARGET_FILE"

python3 -m py_compile "$TARGET_FILE"

echo "$BACKUP_DIR" > "$PROJECT_ROOT/.last_${PATCH_NAME}_backup"
echo "Installed $PATCH_NAME"
echo "Backup: $BACKUP_DIR"
echo "Updated: $TARGET_FILE"
