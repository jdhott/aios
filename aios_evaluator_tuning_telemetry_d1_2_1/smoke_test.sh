#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="./venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi
"$PYTHON" -m py_compile run_aios.py execution_engine_v2.py core/evaluator.py tools/aios_runtime_lock.py
"$PYTHON" - <<'PY'
from pathlib import Path
text = Path('execution_engine_v2.py').read_text()
checks = [
    'Evaluator Tuning Telemetry D1.2.1',
    'def format_bna_component_breakdown',
    '"evaluator_components": orchestration.evaluator_components',
    'format_bna_component_breakdown(item)',
]
missing = [c for c in checks if c not in text]
if missing:
    raise SystemExit('Smoke test failed; missing: ' + ', '.join(missing))
print('Smoke test passed: D1.2.1 BNA component telemetry is installed.')
PY
