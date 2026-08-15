#!/usr/bin/env python3
import base64
import os
from datetime import datetime, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
import aios.api.app as api_module
import aios.web_capture.app as web

def basic(username, password):
    raw = f"{username}:{password}".encode()
    return {"Authorization": "Basic " + base64.b64encode(raw).decode()}

class Task:
    def __init__(self, task_id, title):
        self.id = task_id
        self.title = title
        self.status = None
        self.due_at = None
        self.project_id = None
        self.is_quick_win = False
        self.is_just_do_it = False
        self.is_open = True
        self.is_done = False
        self.is_archived = False
        self.created_at = datetime(2026, 8, 14, tzinfo=timezone.utc)
        self.updated_at = datetime(2026, 8, 14, tzinfo=timezone.utc)
        self.completed_at = None

class FakeTaskRepository:
    rows = [Task("low", "Low score task"), Task("high", "High score task"), Task("none", "No score task")]
    def __init__(self, _store): pass
    def get_all_tasks(self): return self.rows
    def get_task(self, task_id):
        return next((t for t in self.rows if t.id == task_id), None)

class FakeExecutionRepository:
    def __init__(self, _store): pass
    def get_current_state(self):
        return {
            "low": {"execution_score": 3, "execution_rank": None},
            "high": {"execution_score": 28, "execution_rank": 3, "best_next_action": True},
        }

class UpdateQuery:
    def __init__(self, client): self.client = client
    def update(self, payload): self.client.payload = payload; return self
    def eq(self, column, value): self.client.eq = (column, value); return self
    def execute(self): return type("Response", (), {"data": [self.client.payload]})()

class FakeClient:
    def __init__(self): self.payload = None; self.eq = None
    def table(self, name): assert name == "tasks"; return UpdateQuery(self)

class FakeStore:
    def __init__(self): self.client = FakeClient()

store = FakeStore()
with patch.object(api_module, "_store", lambda: store), patch.object(
    api_module, "TaskRepository", FakeTaskRepository
), patch.object(
    api_module, "ExecutionRepository", FakeExecutionRepository
), patch.object(
    api_module, "_request_processor_run", lambda: {"status": "coalesced"}
):
    with TestClient(api_module.app) as client:
        r = client.get("/tasks")
        assert r.status_code == 200
        assert [x["id"] for x in r.json()["tasks"]] == ["high", "low", "none"]
        assert r.json()["sort"] == "execution_score_desc"

        r = client.post("/tasks/low/complete")
        assert r.status_code == 200
        assert store.client.payload["is_done"] is True
        assert store.client.payload["is_open"] is False

        r = client.post("/tasks/low/delete")
        assert r.status_code == 200
        assert store.client.payload["is_archived"] is True
        assert r.json()["mode"] == "soft_archive"

print("Execution Score descending sort: PASS")
print("Complete task action: PASS")
print("Soft-delete task action: PASS")

env = {
    "AIOS_WEB_USERNAME": "aios",
    "AIOS_WEB_PASSWORD": "test-password",
    "AIOS_API_URL": "https://aios-api.example.run.app",
}
web_rows = [{
    "id": "high",
    "title": "High score task",
    "due_at": None,
    "is_quick_win": False,
    "is_just_do_it": False,
    "execution_score": 28,
    "execution_rank": 3,
    "best_next_action": True,
    "surfaced_quick_win": False,
}]
actions = []

with patch.dict(os.environ, env, clear=False), patch.object(
    web, "_fetch_open_tasks", lambda **_kwargs: web_rows
), patch.object(
    web, "_task_action",
    lambda task_id, action: actions.append((task_id, action)) or {"id": task_id}
):
    with TestClient(web.app) as client:
        r = client.get("/", headers=basic("aios", "test-password"))
        assert r.status_code == 200
        assert "Score 28" in r.text
        assert "Best Next Action" in r.text
        assert ">Done</button>" in r.text
        assert ">Delete</button>" in r.text

        r = client.post(
            "/tasks/high/complete",
            headers=basic("aios", "test-password"),
            data={"search": ""},
            follow_redirects=False,
        )
        assert r.status_code == 303

        r = client.post(
            "/tasks/high/delete",
            headers=basic("aios", "test-password"),
            data={"search": ""},
            follow_redirects=False,
        )
        assert r.status_code == 303

assert actions == [("high", "complete"), ("high", "delete")]
print("Web renders score + actions: PASS")
print("Web action routing: PASS")
print("RESULT: AIOS WEB TASKS V1.1 SMOKE TEST PASSED")
