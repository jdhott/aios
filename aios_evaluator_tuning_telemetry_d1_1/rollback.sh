#!/bin/bash
set -euo pipefail
ROOT="${AIOS_ROOT:-$HOME/LocalProjects/aios}"
cd "$ROOT"
LATEST="$(ls -dt .aios_evaluator_tuning_telemetry_d1_1_backup_* 2>/dev/null | head -1 || true)"
if [ -z "$LATEST" ]; then echo "ERROR: no D1.1 backup found"; exit 1; fi
cp "$LATEST/execution_engine_v2.py" execution_engine_v2.py
cp "$LATEST/run.sh" run.sh
cp "$LATEST/run_aios_inner.sh" run_aios_inner.sh
echo "Rolled back AIOS Evaluator Tuning Telemetry D1.1 from backup: $LATEST"
