from pathlib import Path
root=Path(__file__).resolve().parents[1]
files={p:(root/p).read_text() for p in ['aios/project_work.py','aios/project_work_processor.py','aios/api/app.py','aios/web_capture/app.py','migrations/20260818_project_work_dialogue_v1.sql']}
checks=[
('generator can ask one targeted question','"state":"clarification"' in files['aios/project_work.py'] and 'one specific missing fact' in files['aios/project_work.py']),
('dialogue capped at two rounds','clarification_round < 2' in files['aios/project_work.py']),
('answer is summarized into durable context','summarize_project_work_answer' in files['aios/project_work.py'] and 'Preserve uncertainty' in files['aios/project_work.py']),
('processor persists clarification state','MANUAL_STATE_CLARIFICATION' in files['aios/project_work_processor.py'] and 'work_generation_question' in files['aios/project_work_processor.py']),
('processor creates editable context proposal','MANUAL_STATE_CONTEXT_REVIEW' in files['aios/project_work_processor.py'] and 'work_generation_context_update' in files['aios/project_work_processor.py']),
('API accepts answer asynchronously','work-proposals/answer' in files['aios/api/app.py'] and 'answer_pending' in files['aios/api/app.py']),
('API adds approved context then continues','work-proposals/context' in files['aios/api/app.py'] and '"context": merged' in files['aios/api/app.py']),
('UI shows targeted question','AIOS needs one thing from you' in files['aios/web_capture/app.py']),
('UI lets user edit context before save','Add to Project Context' in files['aios/web_capture/app.py'] and 'Add &amp; Continue' in files['aios/web_capture/app.py']),
('migration supports bounded dialogue states','clarification' in files['migrations/20260818_project_work_dialogue_v1.sql'] and 'work_generation_round' in files['migrations/20260818_project_work_dialogue_v1.sql']),
]
failed=[]
for label,ok in checks:
 print(('PASS' if ok else 'FAIL')+': '+label)
 if not ok: failed.append(label)
print('RESULT: PROJECT WORK DIALOGUE V1 STRUCTURE '+('VALID' if not failed else 'FAILED'))
raise SystemExit(1 if failed else 0)
