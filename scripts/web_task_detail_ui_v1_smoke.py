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
task={
    "id":"task-1","title":"Book train ticket from Toronto",
    "due_at":"2026-08-15","defer_until":None,
    "importance":"High Importance","urgency":"",
    "effort":"Small Effort","duration":"15 min",
    "project_id":"project-1","is_quick_win":False,
    "is_just_do_it":False,"execution_score":None,
    "execution_rank":None,"best_next_action":False,
    "surfaced_quick_win":False,
}
with patch.dict(os.environ,env,clear=False), patch.object(web,"_fetch_task_detail",lambda task_id:task):
    with TestClient(web.app) as client:
        r=client.get("/tasks/task-1",headers=basic("aios","test-password"))

assert r.status_code==200
for value in [
    "Task Details",
    "Book train ticket from Toronto",
    "Save Changes",
    "Cancel",
    "Execution Score",
    "Best Next Action",
]:
    assert value in r.text

print("Styled task detail page renders: PASS")
print("Existing task data preserved: PASS")
print("RESULT: TASK DETAIL UI V1 SMOKE TEST PASSED")
