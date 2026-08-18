from pathlib import Path
text = Path("aios/daily_completion_summary.py").read_text()
checks = [
    ("summary version v1.3", "v1.3" in text),
    ("25-45 word target", "25-45 words" in text),
    ("distinctive-day objective", "what made today distinctive" in text),
    ("single dominant thread", "single dominant thread" in text),
    ("one secondary thread maximum", "at most one secondary thread" in text),
    ("permission to omit most tasks", "most individual tasks will go unmentioned" in text),
    ("anti-enumeration guidance", "Synthesize rather than enumerate" in text),
    ("journal-reflection framing", "brief journal reflection" in text),
]
failed = False
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + f": {label}")
    failed |= not ok
if failed:
    raise SystemExit("RESULT: COMPLETED TODAY SUMMARY FLAVOUR V1.3 VALIDATION FAILED")
print("RESULT: COMPLETED TODAY SUMMARY FLAVOUR V1.3 STRUCTURE VALID")
