#!/usr/bin/env python3
import base64
import os
from unittest.mock import patch

from fastapi.testclient import TestClient

import aios.api.app as api_module
import aios.web_capture.app as web


def basic(u, p):
    return {
        "Authorization": "Basic "
        + base64.b64encode(f"{u}:{p}".encode()).decode()
    }


class Query:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def ilike(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def execute(self):
        return type(
            "Response",
            (),
            {"data": self.rows},
        )()


class Client:
    def __init__(self, task_rows, execution_rows):
        self.task_rows = task_rows
        self.execution_rows = execution_rows

    def table(self, name):
        if name == "tasks":
            return Query(self.task_rows)

        if name == "task_execution_state":
            return Query(self.execution_rows)

        raise AssertionError(
            f"Unexpected table: {name}"
        )


class Store:
    def __init__(self, task_rows, execution_rows):
        self.client = Client(
            task_rows,
            execution_rows,
        )


rows = [
    {
        "id": "task-1",
        "title": "Call insurance adjuster",
        "status": None,
        "due_at": "2026-08-15T12:00:00+00:00",
        "project_id": None,
        "is_quick_win": False,
        "is_just_do_it": False,
        "created_at": None,
        "updated_at": None,
    },
    {
        "id": "task-2",
        "title": "Buy furnace filters",
        "status": None,
        "due_at": None,
        "project_id": None,
        "is_quick_win": True,
        "is_just_do_it": False,
        "created_at": None,
        "updated_at": None,
    },
]

execution_rows = [
    {
        "task_id": "task-1",
        "execution_score": 28,
        "execution_rank": 3,
        "best_next_action": True,
        "surfaced_quick_win": False,
    },
    {
        "task_id": "task-2",
        "execution_score": 7,
        "execution_rank": None,
        "best_next_action": False,
        "surfaced_quick_win": True,
    },
]

with patch.object(
    api_module,
    "_store",
    lambda: Store(rows, execution_rows),
):
    with TestClient(api_module.app) as client:
        r = client.get("/tasks?limit=50")

assert r.status_code == 200, r.text
assert r.json()["count"] == 2
assert r.json()["sort"] == "execution_score_desc"

tasks = r.json()["tasks"]

assert tasks[0]["id"] == "task-1"
assert tasks[0]["execution_score"] == 28
assert tasks[1]["id"] == "task-2"
assert tasks[1]["execution_score"] == 7

print("Private API returns open task list: PASS")
print("Execution Score descending sort: PASS")


env = {
    "AIOS_WEB_USERNAME": "aios",
    "AIOS_WEB_PASSWORD": "test-password",
    "AIOS_API_URL": "https://aios-api.example.run.app",
}

with patch.dict(
    os.environ,
    env,
    clear=False,
), patch.object(
    web,
    "_fetch_open_tasks",
    lambda **k: tasks,
):
    with TestClient(web.app) as client:
        r = client.get(
            "/",
            headers=basic(
                "aios",
                "test-password",
            ),
        )

assert r.status_code == 200
assert "Open Tasks" in r.text
assert "Call insurance adjuster" in r.text
assert "Buy furnace filters" in r.text
assert "Score 28" in r.text
assert "Best Next Action" in r.text
assert ">Done</button>" in r.text
assert ">Delete</button>" in r.text

print("Web page renders open tasks: PASS")
print("Score and BNA metadata render: PASS")
print("Done/Delete controls render: PASS")

print(
    "RESULT: AIOS WEB TASKS V1 SMOKE TEST PASSED"
)
