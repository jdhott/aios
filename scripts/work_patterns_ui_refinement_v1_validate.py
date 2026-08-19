
from pathlib import Path
import ast
text=Path("aios/web_capture/app.py").read_text()
checks=[
 ("project section renamed","<h2>Work Patterns</h2>" in text),
 ("project copy tightened","Reuse a saved set of tasks" in text),
 ("pattern choice styling","pattern-choice" in text),
 ("projects navigation retained",'href="/work-patterns">Work Patterns</a>' in text),
 ("diagnostic logging removed","[Project Detail] Render failed:" not in text),
]
failed=False
for label,ok in checks:
 print(("PASS" if ok else "FAIL")+": "+label); failed |= not ok
ast.parse(text); print("web_capture app parses: PASS")
if failed: raise SystemExit("RESULT: WORK PATTERNS UI REFINEMENT V1 VALIDATION FAILED")
print("RESULT: WORK PATTERNS UI REFINEMENT V1 STRUCTURE VALID")
