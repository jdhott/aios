#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${1:-$PWD}"
cd "$PROJECT_ROOT"
"${PYTHON:-python3}" tools/smoke_test_metadata_reconciliation.py
