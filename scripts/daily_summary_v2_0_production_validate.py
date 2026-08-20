from pathlib import Path
import ast

text = Path("aios/daily_completion_summary.py").read_text()

checks = [
    ("production version bumped", 'SUMMARY_VERSION = "v2.0"' in text),
    ("worth-remembering selection retained", "worth remembering months later" in text),
    ("routine-work omission retained", "may be omitted entirely" in text),
    ("task-count bias guard retained", "The number of tasks in an area is not evidence" in text),
    ("single-theme support retained", "summarize only that theme" in text),
    ("themes hidden", "Never state, label, list, or explain the themes" in text),
    ("active phrasing retained", "Prefer direct active phrasing without a subject" in text),
]

failed = False
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
    failed |= not ok

ast.parse(text)
print("daily_completion_summary parses: PASS")

if failed:
    raise SystemExit("RESULT: DAILY SUMMARY V2.0 PRODUCTION VALIDATION FAILED")

print("RESULT: DAILY SUMMARY V2.0 PRODUCTION STRUCTURE VALID")
