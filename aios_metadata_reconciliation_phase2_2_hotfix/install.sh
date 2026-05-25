#!/bin/bash
set -e

PROJECT_DIR="${1:-$HOME/LocalProjects/aios}"
TARGET="$PROJECT_DIR/tools/smoke_test_metadata_reconciliation.py"

if [ ! -f "$TARGET" ]; then
  echo "Target file not found: $TARGET"
  exit 1
fi

python3 - <<'PY'
from pathlib import Path

target = Path.home() / "LocalProjects/aios/tools/smoke_test_metadata_reconciliation.py"
text = target.read_text()

old = 'assert "PHASE 2.1" in formatted'
new = 'assert "PHASE 2.2" in formatted'

if old in text:
    text = text.replace(old, new)
    target.write_text(text)
    print("Updated smoke test assertion to PHASE 2.2")
else:
    print("PHASE 2.1 assertion not found; nothing changed.")
PY

echo "Hotfix install complete."
