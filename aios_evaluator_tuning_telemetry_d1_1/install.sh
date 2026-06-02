#!/bin/bash
set -euo pipefail
ROOT="${AIOS_ROOT:-$HOME/LocalProjects/aios}"
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$ROOT/.aios_evaluator_tuning_telemetry_d1_1_backup_$STAMP"
cd "$ROOT"
if [ ! -f "run_aios.py" ]; then echo "ERROR: run_aios.py not found in $ROOT"; exit 1; fi
if [ ! -f "run.sh" ]; then echo "ERROR: run.sh not found in $ROOT"; exit 1; fi
if ! grep -q "run_aios.py" "run_aios_inner.sh" 2>/dev/null; then echo "ERROR: run_aios_inner.sh does not appear to target run_aios.py"; exit 1; fi
mkdir -p "$BACKUP"
cp execution_engine_v2.py "$BACKUP/execution_engine_v2.py"
cp run.sh "$BACKUP/run.sh"
cp run_aios_inner.sh "$BACKUP/run_aios_inner.sh"
cp "$PKG_DIR/files/execution_engine_v2.py" "$ROOT/execution_engine_v2.py"
"$ROOT/venv/bin/python" -m py_compile "$ROOT/run_aios.py" "$ROOT/execution_engine_v2.py" "$ROOT/core/evaluator.py" "$ROOT/tools/aios_runtime_lock.py"
cat > "$ROOT/smoke_test.sh" <<'SMOKE'
#!/bin/bash
set -euo pipefail
cd "${AIOS_ROOT:-$HOME/LocalProjects/aios}"
PY="./venv/bin/python"
if [ ! -x "$PY" ]; then echo "ERROR: expected executable venv python at $PY"; exit 1; fi
if ! grep -q "run_aios.py" run_aios_inner.sh; then echo "ERROR: run_aios_inner.sh does not target run_aios.py"; exit 1; fi
"$PY" -m py_compile run_aios.py execution_engine_v2.py core/evaluator.py tools/aios_runtime_lock.py
if ! grep -q "Evaluator Tuning Telemetry D1.1" execution_engine_v2.py; then echo "ERROR: evaluator tuning telemetry marker missing"; exit 1; fi
if ! grep -q "emit_evaluator_tuning_telemetry(ranked, winners)" execution_engine_v2.py; then echo "ERROR: evaluator tuning telemetry call missing"; exit 1; fi
echo "Smoke test passed: active runtime is run_aios.py and evaluator telemetry D1.1 is installed."
SMOKE
chmod +x "$ROOT/smoke_test.sh"
cat > "$ROOT/rollback_evaluator_tuning_telemetry_d1_1.sh" <<ROLLBACK
#!/bin/bash
set -euo pipefail
cd "$ROOT"
cp "$BACKUP/execution_engine_v2.py" "$ROOT/execution_engine_v2.py"
cp "$BACKUP/run.sh" "$ROOT/run.sh"
cp "$BACKUP/run_aios_inner.sh" "$ROOT/run_aios_inner.sh"
echo "Rolled back AIOS Evaluator Tuning Telemetry D1.1 from backup: $BACKUP"
ROLLBACK
chmod +x "$ROOT/rollback_evaluator_tuning_telemetry_d1_1.sh"
echo "Installed AIOS Evaluator Tuning Telemetry D1.1"
echo "Backup: $BACKUP"
echo "Smoke test: bash smoke_test.sh"
echo "Rollback: bash rollback_evaluator_tuning_telemetry_d1_1.sh"
