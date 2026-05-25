#!/bin/bash
set -euo pipefail
PROJECT_DIR="${1:-$HOME/LocalProjects/aios}"
TARGET="$PROJECT_DIR/execution_engine_v2.py"

grep -q "def is_closed_or_done_task(task):" "$TARGET"
grep -q "Closed/done tasks excluded before ranking" "$TARGET"
grep -q "Closed/done tasks excluded from sparse reset" "$TARGET"
grep -q "closed/done task reached persistence" "$TARGET"

echo "Smoke test passed: Execution Engine closed/done guard installed."
