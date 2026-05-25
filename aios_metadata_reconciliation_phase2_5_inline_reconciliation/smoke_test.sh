#!/bin/bash
set -euo pipefail

PROJECT_DIR="${1:-$HOME/LocalProjects/aios}"

grep -q "PHASE 2.5: INLINE PRE-SUMMARY PASS" "$PROJECT_DIR/run_aios.py"
grep -q "atexit hook disabled" "$PROJECT_DIR/run_aios.py"
grep -q "Execution rank rewrite skipped: canonical ranks already current" "$PROJECT_DIR/core/metadata/reconciliation.py"

echo "Smoke test passed: Phase 2.5 inline reconciliation installed."
