#!/usr/bin/env python3
import base64,os
from unittest.mock import patch
from fastapi.testclient import TestClient
import aios.web_capture.app as web
def basic(u,p): return {'Authorization':'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()}
focus={'id':'task-1','title':'Plan 90th birthday party for Mum','importance':'High Importance','execution_rank':1,'execution_score':36,'starter_step':'Write down the 3–5 decisions that still need to be made for the party.','starter_minutes':10}
sections={'top5':[focus,{'id':'task-2','title':'Prepare emergency kit for home','importance':'High Importance','due_at':None,'is_quick_win':False,'is_just_do_it':False,'execution_rank':2,'execution_score':32,'best_next_action':True,'surfaced_quick_win':False}],'quick_wins':[],'today':[],'just_do_it':[]}
env={'AIOS_WEB_USERNAME':'aios','AIOS_WEB_PASSWORD':'test-password','AIOS_API_URL':'https://example.run.app'}
with patch.dict(os.environ,env,clear=False),patch.object(web,'_fetch_open_tasks',lambda **k:sections),patch.object(web,'_fetch_focus',lambda:focus):
    with TestClient(web.app) as client: r=client.get('/',headers=basic('aios','test-password'))
assert r.status_code==200
assert '⭐ Best Next Action' in r.text and 'Start here' in r.text and 'Give it 10 minutes' in r.text
assert 'action="/tasks/task-1/complete"' in r.text and 'action="/tasks/task-1/delete"' in r.text and 'href="/tasks/task-1"' in r.text
assert r.text.count('Plan 90th birthday party for Mum')==1
assert '<details class="task-group" data-section="top5">' in r.text
assert '<details class="task-group" data-section="top5" open>' not in r.text
print('Single actionable focus card: PASS')
print('AI starter guidance + timebox render: PASS')
print('Rank1 removed from Top 5: PASS')
print('Alternative sections collapsed by default: PASS')
print('RESULT: DASHBOARD FOCUS V1 SMOKE TEST PASSED')
