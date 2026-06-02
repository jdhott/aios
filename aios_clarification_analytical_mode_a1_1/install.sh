#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-$PWD}"
PKG_DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$TARGET/.aios_clarification_analytical_mode_a1_1_backup_$STAMP"
LATEST_FILE="$TARGET/.last_aios_clarification_analytical_mode_a1_1_backup"

if [ ! -f "$PKG_DIR/files/run_aios.py" ] || [ ! -f "$PKG_DIR/files/aios/clarification.py" ]; then
  echo "ERROR: package files missing. Run install.sh from the extracted package folder."
  exit 1
fi

if [ ! -f "$TARGET/run_aios.py" ] || [ ! -d "$TARGET/aios" ]; then
  echo "ERROR: target does not look like the AIOS repo: $TARGET"
  exit 1
fi

echo "=== Installing AIOS Clarification Analytical Mode A1.1 ==="
echo "Target: $TARGET"
echo "Package: $PKG_DIR"

if command -v git >/dev/null 2>&1 && git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$TARGET" add -A || true
  git -C "$TARGET" commit -m "pre clarification analytical mode a1.1 install" || true
fi

mkdir -p "$BACKUP_DIR/aios"
cp "$TARGET/run_aios.py" "$BACKUP_DIR/run_aios.py"
cp "$TARGET/aios/clarification.py" "$BACKUP_DIR/aios/clarification.py"
echo "$BACKUP_DIR" > "$LATEST_FILE"

cp "$PKG_DIR/files/run_aios.py" "$TARGET/run_aios.py"
cp "$PKG_DIR/files/aios/clarification.py" "$TARGET/aios/clarification.py"

python3 -m py_compile "$TARGET/run_aios.py" "$TARGET/aios/clarification.py"

if ! grep -q "CLARIFICATION ANALYTICAL MODE A1.1 ACTIVE" "$TARGET/run_aios.py"; then
  echo "ERROR: startup marker missing after install"
  exit 1
fi

if ! grep -q "clarification-analytical-mode-a1.1" "$TARGET/run_aios.py"; then
  echo "ERROR: version marker missing after install"
  exit 1
fi

echo "Install complete. Backup: $BACKUP_DIR"
echo "Next: bash smoke_test.sh $TARGET"
