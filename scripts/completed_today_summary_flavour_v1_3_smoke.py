from pathlib import Path
text = Path("aios/daily_completion_summary.py").read_text()
assert "25-45 words" in text
assert "Do not try to account for all completed work" in text
assert "at most one secondary thread" in text
assert "Synthesize rather than enumerate" in text
assert "brief journal reflection" in text
print("Shorter target: PASS")
print("Selective rather than comprehensive: PASS")
print("Single-secondary-thread cap: PASS")
print("Journal-flavour framing: PASS")
print("RESULT: COMPLETED TODAY SUMMARY FLAVOUR V1.3 SMOKE TEST PASSED")
