from pathlib import Path
root=Path(__file__).resolve().parents[1]
run=(root/'run_aios.py').read_text()
api=(root/'aios/api/app.py').read_text()
web=(root/'aios/web_capture/app.py').read_text()
writer=(root/'aios/storage/task_creation_writer.py').read_text()
checks=[
('broad verbs explicitly not evidence','broad verb such as plan, organize, prepare' in run.lower()),
('backyard regression example','Task: Prepare the backyard for winter' in run and 'Decision: no' in run),
('insurance regression example','Task: Organize paperwork for the insurance claim' in run),
('existing breakdown edit writer','def edit_children_for_existing_parent' in writer),
('completed children preserved','Completed children are durable history' in writer),
('API edit endpoint','/tasks/{task_id}/breakdown/edit' in api),
('task detail returns children','task["breakdown_children"]' in api),
('existing breakdown editor','Save Breakdown' in web and 'Open subtasks' in web),
('BNA pending spinner','<span class="mini-spinner"></span> Updating your focus…' in web),
]
for label,ok in checks:
    assert ok,label
    print('PASS:',label)
print('RESULT: BREAKDOWN V2 + EXISTING EDIT STRUCTURE VALID')
