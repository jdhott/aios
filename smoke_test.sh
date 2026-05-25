#!/bin/bash
set -euo pipefail

AIOS_PATH="${AIOS_PATH:-$HOME/LocalProjects/aios}"
cd "$AIOS_PATH"

if [ -d "$AIOS_PATH/venv" ]; then
  # shellcheck disable=SC1091
  source "$AIOS_PATH/venv/bin/activate"
fi

python -m py_compile run_aios_PHASE2_FIXED.py execution_engine_v2.py production/run_aios_PHASE2_FIXED.py aios/projects.py
TEST_ONLY=true python run_aios_PHASE2_FIXED.py --test-only

echo "✅ Smoke test complete"
