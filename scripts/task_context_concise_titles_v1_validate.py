from pathlib import Path
root=Path(__file__).resolve().parents[1]
api=(root/'aios/api/app.py').read_text()
web=(root/'aios/web_capture/app.py').read_text()
focus=(root/'aios/focus_activation.py').read_text()
run=(root/'run_aios.py').read_text()
checks=[
('task context API model','context: str | None = None' in api),
('task detail reads context','id,title,context,status' in api),
('task detail parent id selected','parent_task_id' in api[api.index('def get_task_detail_http'):api.index('def update_task_detail_http')]),
('BNA parent title lookup','task["parent_title"] = None' in api[api.index('def get_dashboard_focus_http'):]),
('editable task context','name="context"' in web and 'Task context' in web),
('shared title guidance','AI_TASK_TITLE_GUIDANCE' in run and 'AI_TASK_TITLE_GUIDANCE' in focus),
('activation context generated','"context":"..."' in focus and 'context=generated.get("context")' in focus),
]
for n,ok in checks:
 print(('PASS: ' if ok else 'FAIL: ')+n)
 assert ok,n
print('RESULT: TASK CONTEXT + CONCISE TITLES V1 STRUCTURE VALID')
