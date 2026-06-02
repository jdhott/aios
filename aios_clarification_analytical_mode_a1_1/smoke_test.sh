#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-$PWD}"

echo "=== Smoke testing AIOS Clarification Analytical Mode A1.1 ==="
python3 -m py_compile "$TARGET/run_aios.py" "$TARGET/aios/clarification.py"

grep -q "CLARIFICATION ANALYTICAL MODE A1.1 ACTIVE" "$TARGET/run_aios.py"
grep -q "clarification-analytical-mode-a1.1" "$TARGET/run_aios.py"
grep -q "def clean_clarification_suggestions" "$TARGET/run_aios.py"
grep -q "dropped_non_outcome_step" "$TARGET/run_aios.py"

python3 - <<PY
import importlib.util
from pathlib import Path
module_path = Path("$TARGET/aios/clarification.py")
spec = importlib.util.spec_from_file_location("clarification_smoke", module_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

mod.GENERATE_MORE_COMMAND = "more"
mod.ADD_OWN_OPTION_COMMAND = "own"
mod.DEFINE_PROMPT = "DEFINE"
mod.CHOOSE_PROMPT = "CHOOSE"
mod.ANALYTICAL_CHOOSE_PROMPT = "ANALYTICAL"
mod.CLARIFICATION_ANALYTICAL_MODE_VERSION = "clarification-analytical-mode-a1.1"
mod.clarification_route = lambda title, allow_ai=False: "choose_next_action"

assert mod.clarification_mode("AIOS: Audit execution rankings") == "analytical"
assert mod.clarification_prompt_for_mode("Validate rankings against metadata") == "ANALYTICAL"

raw = [
    "Retrieve the Top 25 rankings list",
    "Open the metadata dashboard",
    "Compare top-ranked tasks against underlying metadata",
]
cleaned = mod.clean_clarification_suggestions(raw, "analytical", "Compare Top 25 rankings against metadata")
assert "Retrieve the Top 25 rankings list" not in cleaned
assert "Open the metadata dashboard" not in cleaned
assert any("Compare" in s for s in cleaned)

fallback = mod.clean_clarification_suggestions(["Open the dashboard"], "analytical", "Audit rankings")
assert len(fallback) >= 2
assert any("anomal" in s.lower() for s in fallback)
print("Clarification analytical mode smoke tests passed")
PY

echo "Smoke test passed"
