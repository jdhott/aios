#!/usr/bin/env python3
from pathlib import Path
import ast
root=Path(__file__).resolve().parents[1]
api=(root/'aios/api/app.py').read_text(); web=(root/'aios/web_capture/app.py').read_text()
ast.parse(api); ast.parse(web)
checks=[
('API task marker','AIOS_WEB_TASKS_API_VERSION = "web-tasks-v1-read-only"' in api),
('GET /tasks endpoint','def list_open_tasks_http(' in api),
('open only','.eq("is_open", True)' in api),
('not done','.eq("is_done", False)' in api),
('not archived','.eq("is_archived", False)' in api),
('search supported','.ilike("title"' in api),
('web task marker','WEB_TASKS_VERSION = "aios-web-tasks-v1-read-only"' in web),
('web calls private tasks API','f"{api_url}/tasks"' in web),
('web has no Supabase access','SupabaseStore' not in web and '.table("tasks")' not in web),
('Open Tasks rendered','Open Tasks' in web),
('search UI rendered','Search open tasks' in web),]
for label,ok in checks: print(f"{'PASS' if ok else 'FAIL'}: {label}")
if not all(ok for _,ok in checks): raise SystemExit('RESULT: AIOS WEB TASKS V1 VALIDATION FAILED')
print('RESULT: AIOS WEB TASKS V1 STRUCTURE VALID')
