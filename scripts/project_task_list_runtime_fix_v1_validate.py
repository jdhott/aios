from pathlib import Path
web=Path("aios/web_capture/app.py").read_text(); project=web[web.index('<section class="project-task-editor"'):web.index('@app.post("/projects/{project_id}/tasks")')]
checks=[("project page defines row wiring","function wireProjectTaskRow" in project),("project page defines add row","function addProjectTaskRow" in project),("project page serializes current titles","function syncProjectTasks" in project and "JSON.stringify(tasks)" in project),("project page wires trash","row.remove()" in project),("project page wires drag ordering","dragstart" in project and "dragover" in project and "insertBefore" in project)]
for name,ok in checks: print(("PASS: " if ok else "FAIL: ")+name); assert ok
print("RESULT: PROJECT TASK LIST RUNTIME FIX V1 STRUCTURE VALID")
