from pathlib import Path
api=Path('aios/api/app.py').read_text(); web=Path('aios/web_capture/app.py').read_text(); mod=Path('aios/work_patterns.py').read_text(); mig=Path('migrations/20260818_work_patterns_v1.sql').read_text()
checks=[
('pattern tables migration','create table if not exists public.work_patterns' in mig and 'work_pattern_steps' in mig),
('pattern repository exists','def save_work_pattern' in mod and 'def instantiate_pattern_for_project' in mod),
('API CRUD exists','@app.post("/work-patterns"' in api and '@app.put("/work-patterns/{pattern_id}"' in api and '@app.delete("/work-patterns/{pattern_id}"' in api),
('duplicate endpoint exists','/duplicate' in api),
('project instantiation endpoint exists','/projects/{project_id}/work-patterns/{pattern_id}/instantiate' in api),
('library UI exists','def _patterns_library' in web and '+ New Pattern' in web),
('ordered editor exists','draggable="true"' in web and 'data-list' in web),
('project detail entry exists','Use Work Pattern' in web and 'Manage Patterns' in web),
('review before create','Nothing is created until you accept.' in web),
('task context preserved','update["task_context"]=context' in mod),
('normal task creation reused','create_supabase_project_task' in mod),
]
failed=False
for label,ok in checks: print(('PASS' if ok else 'FAIL')+': '+label); failed|=not ok
if failed: raise SystemExit('RESULT: WORK PATTERNS V1 VALIDATION FAILED')
print('RESULT: WORK PATTERNS V1 STRUCTURE VALID')
