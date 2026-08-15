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

projects = [
    {"id":"project-1","name":"AIOS System Development and Enhancement","open_task_count":18},
]

created = []

with patch.dict(os.environ,env,clear=False), \
     patch.object(web,"_fetch_project_options",lambda:projects), \
     patch.object(web,"_create_task",lambda payload: created.append(payload) or {"id":"task-new"}):
    with TestClient(web.app) as client:
        r = client.get("/tasks/new",headers=basic("aios","test-password"))
        assert r.status_code == 200
        assert "New Task" in r.text
        assert "AIOS System Development and Enhancement" in r.text
        assert 'href="/">Home</a>' in r.text

        r = client.post(
            "/tasks/new",
            headers=basic("aios","test-password"),
            data={
                "title":"Test direct task",
                "due_at":"2026-08-16",
                "defer_until":"",
                "importance":"High Importance",
                "urgency":"",
                "effort":"Small Effort",
                "duration":"15 min",
                "project_id":"project-1",
                "is_just_do_it":"true",
            },
            follow_redirects=False,
        )

        assert r.status_code == 303
        assert r.headers["location"] == "/?message=Task+created."

assert created
payload = created[0]
assert payload["title"] == "Test direct task"
assert payload["project_id"] == "project-1"
assert payload["is_just_do_it"] is True

print("New Task page renders: PASS")
print("Project selector renders: PASS")
print("Direct task create submits: PASS")
print("Save returns to dashboard: PASS")
print("RESULT: CREATE TASK + HOME V1 SMOKE TEST PASSED")
