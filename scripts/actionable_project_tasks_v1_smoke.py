from aios.web_capture import app as web
payload={
 'project': {'id':'project-1','name':'Test Project','status':'Active','open_task_count':1},
 'tasks':[{'id':'task-1','title':'Do the thing','execution_rank':2,'execution_score':10,'is_quick_win':False,'is_just_do_it':False}],
 'work_proposals':[]
}
html=web._project_detail_page(payload)
checks=[
 ('completion action rendered', 'action="/tasks/task-1/complete"' in html),
 ('delete action rendered', 'action="/tasks/task-1/delete"' in html),
 ('task detail link preserved', 'href="/tasks/task-1?return_to=/projects/project-1#project-tasks"' in html),
 ('return target preserved', 'value="/projects/project-1#project-tasks"' in html),
 ('project task anchor rendered', 'id="project-tasks"' in html),
]
failed=False
for label,ok in checks:
 print(f"{label}: {'PASS' if ok else 'FAIL'}"); failed |= not ok
print('RESULT: ACTIONABLE PROJECT TASKS V1 SMOKE TEST ' + ('FAILED' if failed else 'PASSED'))
raise SystemExit(1 if failed else 0)
