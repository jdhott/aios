#!/usr/bin/env python3
from pathlib import Path
import ast
root=Path(__file__).resolve().parents[1]
web=(root/"aios/web_capture/app.py").read_text()
ast.parse(web)
checks=[
("checkbox control",'class="complete-checkbox"' in web),
("checkbox before task content",web.find('class="complete-checkbox"') < web.find('class="task-main"')),
("trash icon",'🗑️' in web),
("delete confirmation",'Delete this task?' in web),
("old Done button removed",'>Done</button>' not in web),
("old Delete button removed",'>Delete</button>' not in web),
("right aligned grid",'grid-template-columns:44px minmax(0,1fr) 44px' in web),
("accessible labels",'aria-label="Mark task done"' in web and 'aria-label="Delete task"' in web),
]
for label,ok in checks: print(("PASS" if ok else "FAIL")+": "+label)
if not all(ok for _,ok in checks): raise SystemExit(1)
print("RESULT: WEB TASKS V1.2 UI STRUCTURE VALID")
