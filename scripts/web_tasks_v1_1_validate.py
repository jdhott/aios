#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
api = (root / "aios/api/app.py").read_text()
web = (root / "aios/web_capture/app.py").read_text()
ast.parse(api)
ast.parse(web)

checks = [
    ("API v1.1 marker", 'AIOS_WEB_TASKS_ACTIONS_VERSION = "web-tasks-v1.1-actions-score-sort"' in api),
    ("ExecutionRepository used", "ExecutionRepository" in api),
    ("execution score returned", '"execution_score": state.get("execution_score")' in api),
    ("default score sort", '"sort": "execution_score_desc"' in api),
    ("complete endpoint", '"/tasks/{task_id}/complete"' in api),
    ("delete endpoint", '"/tasks/{task_id}/delete"' in api),
    ("delete is soft archive", '"mode": "soft_archive"' in api and '"is_archived": True' in api),
    ("complete closes task", '"is_done": True' in api and '"is_open": False' in api),
    ("web v1.1 marker", 'WEB_TASK_ACTIONS_VERSION = "aios-web-tasks-v1.1-actions-score-sort"' in web),
    ("Done button", ">Done</button>" in web),
    ("Delete button", ">Delete</button>" in web),
    ("delete confirmation", "Delete this task?" in web),
    ("score displayed", 'meta_parts.append(f"Score ' in web),
    ("sort note displayed", "Sorted by Execution Score" in web),
]
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: AIOS WEB TASKS V1.1 VALIDATION FAILED")
print("RESULT: AIOS WEB TASKS V1.1 STRUCTURE VALID")
