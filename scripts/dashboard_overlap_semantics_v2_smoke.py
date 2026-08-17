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
# Quick-win candidates deliberately cover every stronger section plus one residual.
for rank in range(1,10):
    tid=f'rank-{rank}'
    tasks.append({
        'id':tid,'title':f'Rank {rank}','status':None,
        'due_at':today if rank in (1,7) else None,
        'project_id':None,'importance':None,
        'is_quick_win':rank in (1,2,7,8,9),
        'is_just_do_it':rank==8,
        'created_at':None,'updated_at':None,
    })
    states.append({
        'task_id':tid,'execution_score':100-rank,'execution_rank':rank,
        'best_next_action':rank==1,'surfaced_quick_win':rank in (1,2,7,8,9),
    })
with patch.object(api_module,'_store',lambda:Store(tasks,states)):
    with TestClient(api_module.app) as client:
        r=client.get('/tasks')
assert r.status_code==200, r.text
sections=r.json()['sections']
assert [x['execution_rank'] for x in sections['top5']]==[2,3,4,5,6], sections['top5']
assert {x['id'] for x in sections['today']}=={'rank-1','rank-7'}, sections['today']
assert {x['id'] for x in sections['just_do_it']}=={'rank-8'}, sections['just_do_it']
quick={x['id'] for x in sections['quick_wins']}
assert quick=={'rank-9'}, quick
print('Top 5 remains ranks 2-6: PASS')
print('Today remains independent: PASS')
print('JDI remains independent: PASS')
print('Quick Wins excludes BNA, Top 5, Today, and JDI: PASS')
print('Residual Quick Win remains visible: PASS')
print('RESULT: DASHBOARD OVERLAP SEMANTICS V2 SMOKE TEST PASSED')
