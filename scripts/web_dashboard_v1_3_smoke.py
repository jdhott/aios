#!/usr/bin/env python3
import base64
import os
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
    "top5":[{"id":"task-1","title":"Test task","execution_score":25,"execution_rank":1,"importance":"High Importance","due_at":None,"best_next_action":True,"surfaced_quick_win":False,"is_just_do_it":False}],
    "quick_wins":[],
    "today":[],
    "just_do_it":[],
}
with patch.dict(os.environ,env,clear=False), patch.object(web,"_fetch_open_tasks",lambda **k:sections):
    with TestClient(web.app) as client:
        r=client.get("/",headers=basic("aios","test-password"))

assert r.status_code==200
assert "aios-task-scroll-y" in r.text
assert 'classList.add("is-completing")' in r.text
assert 'content:"✓"' in r.text
assert 'class="complete-checkbox"' in r.text
assert 'class="trash-button"' in r.text

print("Scroll persistence script renders: PASS")
print("Immediate checkmark interaction renders: PASS")
print("Existing controls preserved: PASS")
print("RESULT: WEB DASHBOARD V1.3 SMOKE TEST PASSED")
