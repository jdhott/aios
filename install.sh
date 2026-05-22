#!/bin/bash
set -e

PATCH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
AIOS_PATH="$HOME/LocalProjects/aios"

echo "=== Installing AIOS Temporal Authority Package ==="

cd "$AIOS_PATH"

git add . || true
git commit -m "pre temporal authority install" || true

rsync -av "$PATCH_DIR/" "$AIOS_PATH/"   --exclude '.git'   --exclude 'venv'   --exclude '__pycache__'

source venv/bin/activate

python -m tests.test_temporal_extraction
python -m py_compile run_aios_PHASE2_FIXED.py

echo ""
echo "✅ Install complete"
