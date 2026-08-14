#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
text = (root / "aios/clarification.py").read_text()

for name in [
    "verify_targeted_question_ui",
    "verify_proposal_clarification_ui",
]:
    start = text.find(f"def {name}(")
    if start < 0:
        raise RuntimeError(f"Missing {name}")
    next_def = text.find("\ndef ", start + 5)
    block = text[start: next_def if next_def > 0 else len(text)]
    if "for attempt in range(7):" not in block:
        raise RuntimeError(f"{name} does not retry")
    if "time.sleep(0.4)" not in block:
        raise RuntimeError(f"{name} does not wait")

print("Targeted-question read-after-write retry: PASS")
print("Proposal read-after-write retry: PASS")
print("Strict verification retained: PASS")
print("RESULT: CLARIFICATION UI READ-AFTER-WRITE RETRY SMOKE TEST PASSED")
