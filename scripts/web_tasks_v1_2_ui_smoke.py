#!/usr/bin/env python3
import base64, os
from unittest.mock import patch
from fastapi.testclient import TestClient
import aios.web_capture.app as web
def basic(u,p): return {"Authorization":"Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()}
rows=[{"id":"task-1","title":"Test task","due_at":None,"is_quick_win":False,"is_just_do_it":False,"execution_score":28,"execution_rank":3,"best_next_action":True,"surfaced_quick_win":False}]
env={"AIOS_WEB_USERNAME":"aios","AIOS_WEB_PASSWORD":"test-password","AIOS_API_URL":"https://example.run.app"}
with patch.dict(os.environ,env,clear=False), patch.object(web,"_fetch_open_tasks",lambda **k: rows):
    with TestClient(web.app) as client:
        r=client.get("/",headers=basic("aios","test-password"))
assert r.status_code==200
assert 'aria-label="Mark task done"' in r.text
assert 'aria-label="Delete task"' in r.text
assert "🗑️" in r.text
assert ">Done</button>" not in r.text
assert ">Delete</button>" not in r.text
assert "Score 28" in r.text
print("Checkbox + trash UI render: PASS")
print("Task metadata preserved: PASS")
print("RESULT: WEB TASKS V1.2 UI SMOKE TEST PASSED")
