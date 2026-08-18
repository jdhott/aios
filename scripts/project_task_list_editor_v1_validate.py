from pathlib import Path
root=Path(__file__).resolve().parents[1]
web=(root/'aios/web_capture/app.py').read_text(); api=(root/'aios/api/app.py').read_text(); mig=(root/'migrations/20260818_project_task_order_v1.sql').read_text()
checks={
"project list has drag handle":"project-drag" in web,
"project titles inline editable":"project-editor-title" in web,
"project list has trash":"project-editor-trash" in web,
"project list can add task":"addProjectTaskRow" in web and "+ Add task" in web,
"project list saves structure":"syncProjectTasks" in web and 'Save Project Tasks' in web,
"completion stays available":'Mark task done' in web and 'project-complete-' in web,
"API supports ordered project list":'update_project_task_list_http' in api and 'project_order' in api,
"API creates new project tasks":'create_supabase_project_task(store, title=title, project_id=project_id)' in api,
"migration adds project order":'add column if not exists project_order integer' in mig,
}
for name,ok in checks.items():
 print(('PASS: ' if ok else 'FAIL: ')+name)
 assert ok,name
print('RESULT: PROJECT TASK LIST EDITOR V1 STRUCTURE VALID')
