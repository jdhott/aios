#!/usr/bin/env python3
import base64, os
from unittest.mock import patch
from fastapi.testclient import TestClient
import aios.web_capture.app as web

def basic(u,p):
    return {"Authorization":"Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()}

env={
    "AIOS_WEB_USERNAME":"aios",
    "AIOS_WEB_PASSWORD":"test-password",
    "AIOS_API_URL":"https://example.run.app",
}
sections={
    "top5":[{"id":"a","title":"Top task","execution_score":36,"execution_rank":1,"importance":"High Importance","due_at":None,"best_next_action":True,"surfaced_quick_win":False,"is_just_do_it":False}],
    "quick_wins":[{"id":"b","title":"Quick task","execution_score":12,"execution_rank":None,"importance":"High Importance","due_at":None,"best_next_action":False,"surfaced_quick_win":True,"is_just_do_it":False}],
    "today":[{"id":"c","title":"Today task","execution_score":6,"execution_rank":None,"importance":None,"due_at":"2026-08-14T12:00:00-04:00","best_next_action":False,"surfaced_quick_win":False,"is_just_do_it":False}],
    "just_do_it":[{"id":"d","title":"JDI task","execution_score":None,"execution_rank":None,"importance":None,"due_at":None,"best_next_action":False,"surfaced_quick_win":False,"is_just_do_it":True}],
}
with patch.dict(os.environ,env,clear=False), patch.object(web,"_fetch_open_tasks",lambda **k:sections):
    with TestClient(web.app) as client:
        r=client.get("/",headers=basic("aios","test-password"))
assert r.status_code==200
for s in ["Top 5","Quick Wins","Today","Just Do It","Top task","Quick task","Today task","JDI task"]:
    assert s in r.text
assert 'aria-label="Mark task done"' in r.text
assert 'aria-label="Delete task"' in r.text
print("Four dashboard sections render: PASS")
print("Task actions preserved: PASS")
print("RESULT: AIOS WEB DASHBOARD V1 SMOKE TEST PASSED")
