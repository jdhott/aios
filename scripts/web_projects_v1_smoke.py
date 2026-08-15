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

projects=[
    {"id":"project-1","name":"Basement Recovery","status":"Active","open_task_count":4},
]
detail={
    "project":{"id":"project-1","name":"Basement Recovery","status":"Active","open_task_count":1},
    "tasks":[
        {"id":"task-1","title":"Call insurance adjuster","due_at":"2026-08-15",
         "importance":"High Importance","is_quick_win":False,"is_just_do_it":False,
         "execution_score":28,"execution_rank":3,"best_next_action":True,
         "surfaced_quick_win":False}
    ],
}

with patch.dict(os.environ,env,clear=False), \
     patch.object(web,"_fetch_projects",lambda:projects), \
     patch.object(web,"_fetch_project_detail",lambda project_id:detail):
    with TestClient(web.app) as client:
        r=client.get("/projects",headers=basic("aios","test-password"))
        assert r.status_code==200
        assert "Basement Recovery" in r.text
        assert 'href="/projects/project-1"' in r.text

        r=client.get("/projects/project-1",headers=basic("aios","test-password"))
        assert r.status_code==200
        assert "Call insurance adjuster" in r.text
        assert "Rank 3" in r.text
        assert 'href="/tasks/task-1"' in r.text

print("Projects list renders: PASS")
print("Project detail renders: PASS")
print("Project tasks link to task detail: PASS")
print("RESULT: AIOS PROJECTS V1 FIX1 SMOKE TEST PASSED")
