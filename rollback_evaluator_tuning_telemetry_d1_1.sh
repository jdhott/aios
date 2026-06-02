#!/bin/bash
set -euo pipefail
cd "/Users/John/LocalProjects/aios"
cp "/Users/John/LocalProjects/aios/.aios_evaluator_tuning_telemetry_d1_1_backup_20260529_055046/execution_engine_v2.py" "/Users/John/LocalProjects/aios/execution_engine_v2.py"
cp "/Users/John/LocalProjects/aios/.aios_evaluator_tuning_telemetry_d1_1_backup_20260529_055046/run.sh" "/Users/John/LocalProjects/aios/run.sh"
cp "/Users/John/LocalProjects/aios/.aios_evaluator_tuning_telemetry_d1_1_backup_20260529_055046/run_aios_inner.sh" "/Users/John/LocalProjects/aios/run_aios_inner.sh"
echo "Rolled back AIOS Evaluator Tuning Telemetry D1.1 from backup: /Users/John/LocalProjects/aios/.aios_evaluator_tuning_telemetry_d1_1_backup_20260529_055046"
