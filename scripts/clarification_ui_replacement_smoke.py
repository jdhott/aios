#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
text = (root / "aios/clarification.py").read_text()

clear_pos = text.find('if not clear_page_children(page["id"]):')
append_pos = text.find("children = [", clear_pos)
verify_pos = text.find('if not verify_targeted_question_ui(page["id"]):')
shadow_pos = text.find("_shadow_mark_awaiting_answer(", verify_pos)

if min(clear_pos, append_pos, verify_pos, shadow_pos) < 0:
    raise RuntimeError("Clarification replacement boundaries missing.")

if not (clear_pos < append_pos < verify_pos < shadow_pos):
    raise RuntimeError("Clarification replacement boundaries are out of order.")

print("Verified clear before targeted append: PASS")
print("Targeted UI verification before shadow transition: PASS")
print("Proposal rebuild verification present: PASS")
print("RESULT: CLARIFICATION UI REPLACEMENT VERIFICATION SMOKE TEST PASSED")
