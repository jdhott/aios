#!/usr/bin/env python3
from unittest.mock import patch
from fastapi.testclient import TestClient
from datetime import datetime
from zoneinfo import ZoneInfo
import aios.api.app as api_module

class Query:
    def __init__(self, rows): self.rows=rows
    def select(self,*a,**k): return self
    def eq(self,*a,**k): return self
    def ilike(self,*a,**k): return self
    def in_(self,*a,**k): return self
    def execute(self): return type('Response',(),{'data':self.rows})()
class Client:
    def __init__(self,tasks,states): self.tasks=tasks; self.states=states
    def table(self,name): return Query(self.tasks if name=='tasks' else self.states)
class Store:
    def __init__(self,tasks,states): self.client=Client(tasks,states)

today=datetime.now(ZoneInfo('America/Toronto')).date().isoformat()
tasks=[]; states=[]
for rank in range(1,9):
    tid=f'rank-{rank}'
    tasks.append({'id':tid,'title':f'Rank {rank}','status':None,'due_at': today if rank in (1,7,8) else None,'project_id':None,'importance':None,'is_quick_win':False,'is_just_do_it':False,'created_at':None,'updated_at':None})
    states.append({'task_id':tid,'execution_score':100-rank,'execution_rank':rank,'best_next_action':rank==1,'surfaced_quick_win':False})
with patch.object(api_module,'_store',lambda:Store(tasks,states)):
    with TestClient(api_module.app) as client: r=client.get('/tasks')
assert r.status_code==200, r.text
sections=r.json()['sections']
assert [x['execution_rank'] for x in sections['top5']]==[2,3,4,5,6], sections['top5']
assert {x['id'] for x in sections['today']}=={'rank-1','rank-7','rank-8'}, sections['today']
print('Top 5 is exactly ranks 2-6: PASS')
print('Today includes every due/overdue task independent of rank: PASS')
print('RESULT: DASHBOARD SEMANTICS + CONTINUITY V1 SMOKE TEST PASSED')
