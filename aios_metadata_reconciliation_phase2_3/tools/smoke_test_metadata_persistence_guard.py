#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.metadata.persistence_guard import install_closed_task_execution_persistence_guard


def prop_checkbox(value):
    return {"checkbox": value}


def prop_number(value):
    return {"number": value}


def prop_title(value):
    return {"title": [{"plain_text": value}]}


# Global page object intentionally present so the guard can discover it in runtime globals.
closed_page = {
    "id": "closed-page-1",
    "properties": {
        "Task Name": prop_title("Closed guarded task"),
        "Done": prop_checkbox(True),
    },
}
open_page = {
    "id": "open-page-1",
    "properties": {
        "Task Name": prop_title("Open task"),
        "Open Loop": prop_checkbox(True),
    },
}
all_tasks = [closed_page, open_page]

install_closed_task_execution_persistence_guard()

import requests

calls = []

# Replace the underlying original patch after guard install by wrapping requests.patch's closure is hard,
# so this smoke test focuses on install idempotence and callable behavior without external network.
# A synthetic guarded response should be returned for closed-page execution-only writes.
resp = requests.patch(
    "https://api.notion.com/v1/pages/closed-page-1",
    json={"properties": {"Execution Rank": {"number": 3}, "Execution Score": {"number": 17}}},
)
assert getattr(resp, "ok", False) is True
assert getattr(resp, "status_code", None) == 200
assert "guard" in resp.text.lower()

print("Persistence guard smoke test passed")
