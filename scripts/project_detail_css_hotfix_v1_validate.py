from pathlib import Path
import ast

p = Path("aios/web_capture/app.py")
text = p.read_text()

checks = [
    ("parent metadata CSS escaped",
     '.task-parent-meta {{ margin-top:5px;' in text),
    ("parent metadata link CSS escaped",
     '.task-parent-meta a {{ color:inherit;' in text),
    ("unescaped parent metadata CSS removed",
     '.task-parent-meta { margin-top:5px;' not in text),
]
failed = False
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + f": {label}")
    failed |= not ok

ast.parse(text)
print("web_capture app parses: PASS")

if failed:
    raise SystemExit("RESULT: PROJECT DETAIL CSS HOTFIX V1 VALIDATION FAILED")
print("RESULT: PROJECT DETAIL CSS HOTFIX V1 STRUCTURE VALID")
