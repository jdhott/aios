#!/usr/bin/env python3
import base64, os
from unittest.mock import patch
from fastapi.testclient import TestClient
import aios.web_capture.app as web

def basic(u,p):
    return {"Authorization":"Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()}

env = {
    "AIOS_WEB_USERNAME":"aios",
    "AIOS_WEB_PASSWORD":"test-password",
    "AIOS_API_URL":"https://example.run.app",
}

task = {
    "id":"task-1",
    "title":"Test task",
    "due_at":None,
    "defer_until":None,
    "importance":"High Importance",
    "urgency":"",
    "effort":"Small Effort",
    "duration":"15 min",
    "project_id":"project-1",
    "is_quick_win":False,
    "is_just_do_it":False,
    "execution_score":20,
    "execution_rank":2,
    "best_next_action":True,
    "surfaced_quick_win":False,
}

with patch.dict(os.environ,env,clear=False), \
     patch.object(web,"_fetch_task_detail",lambda task_id:task), \
     patch.object(web,"_update_task_detail",lambda task_id,payload:task):
    with TestClient(web.app) as client:
        r = client.get("/tasks/task-1",headers=basic("aios","test-password"))
        assert r.status_code == 200
        assert "← Back to Tasks" not in r.text
        assert ">Cancel</a>" in r.text

        r = client.post(
            "/tasks/task-1/edit",
            headers=basic("aios","test-password"),
            data={
                "title":"Test task",
                "due_at":"",
                "defer_until":"",
                "importance":"High Importance",
                "urgency":"",
                "effort":"Small Effort",
                "duration":"15 min",
            },
            follow_redirects=False,
        )
        assert r.status_code == 303
        assert r.headers["location"] == "/?message=Task+updated."

print("Back navigation removed: PASS")
print("Cancel returns to task list: PASS")
print("Save returns to task list with confirmation: PASS")
print("RESULT: TASK DETAIL UI V1.1 SMOKE TEST PASSED")
