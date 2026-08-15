#!/usr/bin/env python3
import base64, os
from unittest.mock import patch
from fastapi.testclient import TestClient
import aios.web_capture.app as web
def basic(u,p):
    return {"Authorization":"Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()}
env={"AIOS_WEB_USERNAME":"aios","AIOS_WEB_PASSWORD":"test-password","AIOS_API_URL":"https://example.run.app"}
task={"id":"task-1","title":"Test task","due_at":None,"importance":"High Importance",
      "is_quick_win":False,"is_just_do_it":False,"execution_score":28,
      "execution_rank":1,"best_next_action":True,"surfaced_quick_win":False}
sections={"top5":[task],"quick_wins":[],"today":[],"just_do_it":[]}
with patch.dict(os.environ,env,clear=False), patch.object(web,"_fetch_open_tasks",lambda **k:sections):
    with TestClient(web.app) as client:
        r=client.get("/",headers=basic("aios","test-password"))
assert r.status_code==200
assert ">Dashboard</h1>" in r.text
assert "<h2>Brain Dump</h2>" in r.text
assert 'id="brainDumpText"' in r.text
assert 'id="expandAllSections"' in r.text
assert 'id="collapseAllSections"' in r.text
assert '<details class="task-group"' in r.text
assert web._split_brain_dump("• One\n• Two\n- Three") == ["One","Two","Three"]
print("Compact dashboard capture renders: PASS")
print("Bullet Brain Dump parsing: PASS")
print("Collapsible task sections render: PASS")
print("RESULT: DASHBOARD V1.4 SMOKE TEST PASSED")
