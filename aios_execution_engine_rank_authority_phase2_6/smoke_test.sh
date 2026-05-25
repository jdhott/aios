#!/bin/bash
set -euo pipefail
PROJECT_DIR="${1:-$HOME/LocalProjects/aios}"
TARGET="$PROJECT_DIR/execution_engine_v2.py"

grep -q "Canonical rank ordering active: score desc, title asc, page_id asc" "$TARGET"
grep -q "Canonical persistence row:" "$TARGET"
grep -q "\[Execution Engine V2\] Write payload:" "$TARGET"

echo "Smoke test passed: Execution Engine deterministic rank authority installed."
