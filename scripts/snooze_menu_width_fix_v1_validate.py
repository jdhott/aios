from pathlib import Path
import ast

text = Path("aios/web_capture/app.py").read_text()

checks = [
    ("snooze menu widened", "width:260px" in text),
    ("date column minimum set", "grid-template-columns:minmax(145px,1fr) auto" in text),
    ("date input minimum set", "min-width:145px" in text),
    ("cancel retained", 'class="snooze-cancel"' in text),
]

failed = False
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + f": {label}")
    failed |= not ok

ast.parse(text)
print("web_capture app parses: PASS")

if failed:
    raise SystemExit("RESULT: SNOOZE MENU WIDTH FIX V1 VALIDATION FAILED")
print("RESULT: SNOOZE MENU WIDTH FIX V1 STRUCTURE VALID")
