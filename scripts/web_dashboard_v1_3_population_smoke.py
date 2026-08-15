#!/usr/bin/env python3
from unittest.mock import patch
from fastapi.testclient import TestClient
import aios.api.app as api_module

class Query:
    def __init__(self, rows):
        self.rows = rows
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def ilike(self, *a, **k): return self
    def in_(self, *a, **k): return self
    def execute(self):
        return type("Response", (), {"data": self.rows})()

class Client:
    def __init__(self, tasks, states):
        self.tasks = tasks
        self.states = states
    def table(self, name):
        if name == "tasks":
            return Query(self.tasks)
        if name == "task_execution_state":
            return Query(self.states)
        raise AssertionError(name)

class Store:
    def __init__(self, tasks, states):
        self.client = Client(tasks, states)

tasks = []
states = []

for i in range(60):
    tid = f"normal-{i}"
    tasks.append({
        "id": tid,
        "title": f"Normal task {i}",
        "status": None,
        "due_at": None,
        "project_id": None,
        "importance": None,
        "is_quick_win": False,
        "is_just_do_it": False,
        "created_at": None,
        "updated_at": None,
    })
    states.append({
        "task_id": tid,
        "execution_score": 100 - i,
        "execution_rank": i + 1,
        "best_next_action": False,
        "surfaced_quick_win": False,
    })

for i in range(10):
    tid = f"jdi-{i}"
    tasks.append({
        "id": tid,
        "title": f"JDI task {i}",
        "status": None,
        "due_at": None,
        "project_id": None,
        "importance": None,
        "is_quick_win": False,
        "is_just_do_it": True,
        "created_at": None,
        "updated_at": None,
    })
    states.append({
        "task_id": tid,
        "execution_score": None,
        "execution_rank": None,
        "best_next_action": False,
        "surfaced_quick_win": False,
    })

with patch.object(api_module, "_store", lambda: Store(tasks, states)):
    with TestClient(api_module.app) as client:
        r = client.get("/tasks?limit=50")

assert r.status_code == 200, r.text
jdi = r.json()["sections"]["just_do_it"]
assert len(jdi) == 10, f"Expected 10 JDI tasks, got {len(jdi)}"

print("All JDI tasks participate beyond first 50 source rows: PASS")
print("RESULT: FULL POPULATION FIX SMOKE TEST PASSED")
