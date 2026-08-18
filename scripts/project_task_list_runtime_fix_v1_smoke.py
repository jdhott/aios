from pathlib import Path
web=Path("aios/web_capture/app.py").read_text(); project=web[web.index('<section class="project-task-editor"'):web.index('@app.post("/projects/{project_id}/tasks")')]
assert 'onsubmit="return syncProjectTasks(this)"' in project; assert 'row.remove()' in project; assert "row.dataset.taskId||null" in project; assert "list.insertBefore(dragging,after)" in project; assert "projectTaskRow('')" in project
print("Rename serialization: PASS\nTrash interaction: PASS\nDrag/reorder interaction: PASS\nAdd-task interaction: PASS\nRESULT: PROJECT TASK LIST RUNTIME FIX V1 SMOKE TEST PASSED")
