
from pathlib import Path
text=Path("aios/web_capture/app.py").read_text()
assert '@app.get("/work-patterns")' in text
assert '@app.get("/projects/{project_id}/work-patterns")' in text
assert '@app.post("/projects/{project_id}/work-patterns/{pattern_id}/instantiate")' in text
assert "Nothing is created until you accept." in text
assert ".task-parent-meta {{ margin-top:5px;" in text
segment=text[text.index("def _project_detail_page"):text.index("def _possible_duplicate_new_task_page")]
assert "{focus_submit_feedback_script}" not in segment
print("Work Pattern routes retained: PASS")
print("Review-before-create retained: PASS")
print("Project Detail render regressions absent: PASS")
print("RESULT: WORK PATTERNS UI REFINEMENT V1 SMOKE TEST PASSED")
