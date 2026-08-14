#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
text = (root / "aios/clarification.py").read_text()
ast.parse(text)

checks = [
    ("clear verifies empty children", "Cleared clarification blocks (verified)" in text),
    ("delete status checked", "ERROR deleting clarification block" in text),
    ("clear polls Notion", "time.sleep(0.4)" in text),
    ("targeted verifier exists", "def verify_targeted_question_ui(page_id):" in text),
    ("proposal verifier exists", "def verify_proposal_clarification_ui(page_id):" in text),
    ("targeted append guarded by clear", 'if not clear_page_children(page["id"]):' in text),
    ("awaiting_answer guarded by UI verification",
     'if not verify_targeted_question_ui(page["id"]):' in text),
    ("rebuild verifies proposal UI",
     "if not verify_proposal_clarification_ui(page_id):" in text),
    ("marker exists", "[Clarification UI] Verified replacement support active" in text),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CLARIFICATION UI REPLACEMENT VERIFICATION VALIDATION FAILED")

print("RESULT: CLARIFICATION UI REPLACEMENT VERIFICATION STRUCTURE VALID")
