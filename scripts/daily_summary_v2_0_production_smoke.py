from pathlib import Path

text = Path("aios/daily_completion_summary.py").read_text()

assert 'SUMMARY_VERSION = "v2.0"' in text
assert "worth remembering months later" in text
assert "Routine chores, cleanup, maintenance, and minor administrative work may be omitted entirely" in text

print("Production fingerprint version: PASS")
print("Accepted V2.0 prompt retained: PASS")
print("RESULT: DAILY SUMMARY V2.0 PRODUCTION SMOKE TEST PASSED")
