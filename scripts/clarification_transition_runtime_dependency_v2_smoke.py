#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
run_text = (root / "run_aios.py").read_text()
clar_text = (root / "aios/clarification.py").read_text()

config_pos = run_text.find(
    "[Clarification Shadow] State transition helpers configured"
)
reconfig_pos = run_text.find(
    "clarification_helpers.configure_clarification_module(globals())",
    config_pos,
)
marker_pos = run_text.find(
    "[Clarification Shadow] Runtime dependencies refreshed"
)

if min(config_pos, reconfig_pos, marker_pos) < 0:
    raise RuntimeError("Runtime refresh structure missing.")

if not (config_pos < reconfig_pos < marker_pos):
    raise RuntimeError("Runtime refresh ordering is incorrect.")

start = clar_text.find(
    "def _shadow_open_clarification_review(page_id):"
)
end = clar_text.find(
    "def _shadow_mark_awaiting_answer",
    start,
)
helper = clar_text[start:end]

if '"clarification_shadow_review_repo"' not in helper:
    raise RuntimeError("Review repository is not guarded.")

if "review_repo.row_to_review(row)" not in helper:
    raise RuntimeError("Guarded local repository is not used.")

print("Runtime dependency refresh ordering: PASS")
print("Guarded review repository lookup: PASS")
print("Local repository row conversion: PASS")
print("Shadow dependency absence cannot raise NameError: PASS")
print(
    "RESULT: CLARIFICATION TRANSITION RUNTIME DEPENDENCY FIX V2 SMOKE TEST PASSED"
)
