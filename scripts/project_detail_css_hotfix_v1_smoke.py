# Regression: CSS inside the Project Detail f-string must use doubled braces.
from pathlib import Path
text = Path("aios/web_capture/app.py").read_text()
start = text.index("def _project_detail_page")
end = text.index("def _possible_duplicate_new_task_page", start)
segment = text[start:end]
assert '.task-parent-meta {{ margin-top:5px;' in segment
assert '.task-parent-meta a {{ color:inherit;' in segment
print("Project Detail parent metadata CSS no longer evaluates `margin` as Python: PASS")
print("RESULT: PROJECT DETAIL CSS HOTFIX V1 SMOKE TEST PASSED")
