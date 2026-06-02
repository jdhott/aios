#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"

echo "=== Smoke Test: AIOS Clarification Analytical Mode A1.0 ==="
python3 -m py_compile "$ROOT/run_aios.py" "$ROOT/aios/clarification.py"

python3 - "$ROOT" <<'PY'
import importlib.util
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
mod_path = root / "aios" / "clarification.py"
spec = importlib.util.spec_from_file_location("clarification_under_test", mod_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Inject minimal runtime globals used by the new mode helpers.
mod.clarification_route = lambda title, allow_ai=True: "break_down"
mod.DEFINE_PROMPT = "DEFINE"
mod.CHOOSE_PROMPT = "CHOOSE"
mod.ANALYTICAL_CHOOSE_PROMPT = "ANALYTICAL"

cases = {
    "AIOS: Compare the Top 25 execution rankings against their underlying metadata": "analytical",
    "Validate that current rankings align with Urgency, Importance, and Due Date metadata": "analytical",
    "Buy milk": "procedural",
}

for title, expected in cases.items():
    actual = mod.clarification_mode(title)
    print(f"mode[{title[:45]}...]={actual}")
    assert actual == expected, (title, actual, expected)

assert mod.clarification_prompt_for_mode("AIOS: Audit rankings") == "ANALYTICAL"
print("Analytical mode classifier OK")
PY

grep -q "outcome-producing" "$ROOT/run_aios.py"
grep -q "\[Clarification\] mode=" "$ROOT/run_aios.py"

echo "Smoke test passed."
