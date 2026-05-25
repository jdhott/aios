#!/bin/bash
set -euo pipefail
PROJECT_DIR="${1:-$HOME/LocalProjects/aios}"
cd "$PROJECT_DIR"
test -f tools/aios_runtime_lock.py
grep -q "aios_runtime_lock.py" run.sh
echo "Smoke test passed: runtime lock wrapper installed."
