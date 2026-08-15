#!/usr/bin/env python3
import base64, os
from unittest.mock import patch
from fastapi.testclient import TestClient
import aios.web_capture.app as web

def basic(u,p):
    return {"Authorization":"Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()}

env={"AIOS_WEB_USERNAME":"aios","AIOS_WEB_PASSWORD":"test-password","AIOS_API_URL":"https://example.run.app"}
task={"id":"task-1","title":"Call insurance adjuster","due_at":"2026-08-15","defer_until":None,
      "importance":"High Importance","urgency":None,"effort":"Small Effort","duration":"15 min",
      "project_id":"project-1","is_quick_win":False,"is_just_do_it":False,"execution_score":28,
      "execution_rank":3,"best_next_action":True,"surfaced_quick_win":False}
sections={"top5":[task],"quick_wins":[],"today":[],"just_do_it":[]}
updates=[]

with patch.dict(os.environ,env,clear=False), patch.object(web,"_fetch_open_tasks",lambda **k:sections), patch.object(web,"_fetch_task_detail",lambda task_id:task), patch.object(web,"_update_task_detail",lambda task_id,payload: updates.append((task_id,payload)) or task):
    with TestClient(web.app) as client:
        r=client.get("/",headers=basic("aios","test-password"))
        assert r.status_code==200 and 'href="/tasks/task-1"' in r.text
        r=client.get("/tasks/task-1",headers=basic("aios","test-password"))
        assert r.status_code==200 and "Execution Score" in r.text
        r=client.post("/tasks/task-1/edit",headers=basic("aios","test-password"),
            data={"title":"Call adjuster today","due_at":"2026-08-15","defer_until":"",
                  "importance":"High Importance","urgency":"High Urgency","effort":"Small Effort",
                  "duration":"15 min","is_just_do_it":"true"},follow_redirects=False)
        assert r.status_code==303
assert updates and updates[0][1]["is_just_do_it"] is True
print("Dashboard task link: PASS")
print("Task detail render: PASS")
print("Task edit submit: PASS")
print("RESULT: TASK DETAIL/EDIT V1 SMOKE TEST PASSED")
