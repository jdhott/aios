#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
text = (root / "aios/clarification.py").read_text()
ast.parse(text)

checks = [
    ("version marker", "read-after-write-retry-v1" in text),
    ("targeted verifier retries",
     "def verify_targeted_question_ui(page_id):" in text
     and "for attempt in range(7):" in text),
    ("proposal verifier retries",
     "def verify_proposal_clarification_ui(page_id):" in text
     and text.count("for attempt in range(7):") >= 2),
    ("retry delay present", text.count("time.sleep(0.4)") >= 2),
    ("strict targeted guard retained",
     'if not verify_targeted_question_ui(page["id"]):' in text),
    ("strict proposal guard retained",
     "if not verify_proposal_clarification_ui(page_id):" in text),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CLARIFICATION UI READ-AFTER-WRITE RETRY VALIDATION FAILED")

print("RESULT: CLARIFICATION UI READ-AFTER-WRITE RETRY STRUCTURE VALID")
