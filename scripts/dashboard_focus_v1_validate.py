#!/usr/bin/env python3
from pathlib import Path
import ast
root=Path(__file__).resolve().parents[1]
run=(root/'run_aios.py').read_text(); api=(root/'aios/api/app.py').read_text(); web=(root/'aios/web_capture/app.py').read_text(); focus=(root/'aios/focus_guidance.py').read_text()
for text in (run,api,web,focus): ast.parse(text)
checks=[
('processor focus marker','AIOS_DASHBOARD_FOCUS_VERSION = "dashboard-focus-v1"' in run),
('rank1 guidance only','EXECUTION_ENGINE_WINNERS[0]' in run and 'ensure_focus_guidance' in run),
('AI starter prompt','starter_minutes' in focus and 'activation energy' in focus),
('guidance cache','table("task_focus_guidance")' in focus),
('focus API','@app.get("/focus"' in api),
('web focus fetch','def _fetch_focus()' in web),
('actionable checkbox','focus-complete' in web),
('actionable trash','focus-delete' in web),
('focus title link','class="focus-title"' in web),
('rank1 removed from alternatives','if focus_id:' in web),
('collapsed by default','data-section="{html.escape(key)}">' in web),
('Start here','Start here' in web),
('timebox','Give it' in web),
]
for label,ok in checks: print(('PASS' if ok else 'FAIL')+': '+label)
if not all(ok for _,ok in checks): raise SystemExit('RESULT: DASHBOARD FOCUS V1 VALIDATION FAILED')
print('RESULT: DASHBOARD FOCUS V1 STRUCTURE VALID')
