#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$(pwd)}"
TARGET_FILE="$PROJECT_ROOT/core/metadata/reconciliation.py"

if [[ ! -f "$TARGET_FILE" ]]; then
  echo "ERROR: Target file not found: $TARGET_FILE" >&2
  exit 1
fi

python3 -m py_compile "$TARGET_FILE"

grep -q "metadata-reconciliation-phase2-legacy-diagnostic-cleanup-v0.2.4" "$TARGET_FILE"

echo "Smoke test passed: reconciliation.py compiles and version marker is present."

if grep -Eq "Open tasks with Do = Today but not Best Next Action|Open Best Next Action tasks not surfaced in Do = Today|Legacy Focus/Focus Now metadata still present|strong_candidate|do_today|focus_now" "$TARGET_FILE"; then
  echo "ERROR: Legacy diagnostic authority remnants found in reconciliation.py" >&2
  exit 1
fi

echo "Smoke test passed: stale Do/Focus/Strong diagnostic references removed."
