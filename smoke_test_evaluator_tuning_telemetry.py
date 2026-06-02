#!/usr/bin/env python3
"""Smoke test for evaluator tuning telemetry package.

Runs Execution Engine V2 against a small in-memory task set and verifies that
read-only evaluator tuning telemetry is emitted without requiring Notion access.
"""

import contextlib
import io

from execution_engine_v2 import rebuild_execution_state


def prop_title(title):
    return {"title": [{"plain_text": title}]}


def prop_select(name):
    if name is None:
        return {"select": None}
    return {"select": {"name": name}}


def prop_checkbox(value=False):
    return {"checkbox": bool(value)}


def task(task_id, title, priority=None, urgency=None, duration=None, effort=None, jdi=False):
    return {
        "id": task_id,
        "properties": {
            "Task Name": prop_title(title),
            "Priority": prop_select(priority),
            "Urgency": prop_select(urgency),
            "Duration": prop_select(duration),
            "Effort": prop_select(effort),
            "Just Do It": prop_checkbox(jdi),
            "Execution Score": {"number": None},
            "Execution Rank": {"number": None},
        },
    }


updates = []


def fake_update(task_id, properties):
    updates.append((task_id, properties))


sample_tasks = [
    task("task-1", "Email workshop attendees", priority="High Priority"),
    task("task-2", "Buy bread bags", duration="10 min"),
    task("task-3", "Review bakery production plan", effort="Medium Effort"),
    task("task-4", "Make notes for therapy session"),
    task("task-5", "Pool", priority="High Priority"),  # rejected non-actionable
    task("task-6", "Just do it empty dishwasher", jdi=True),
]

buffer = io.StringIO()
with contextlib.redirect_stdout(buffer):
    winners = rebuild_execution_state(sample_tasks, fake_update, max_best_next_actions=3)

output = buffer.getvalue()

required = [
    "--- Evaluator Tuning Telemetry ---",
    "[Evaluator Tuning] Pool:",
    "[Evaluator Tuning] Score bands:",
    "[Evaluator Tuning] Signal distribution:",
    "[Evaluator Tuning] Scoring source health:",
]

missing = [needle for needle in required if needle not in output]
if missing:
    raise SystemExit("Missing expected telemetry lines: " + ", ".join(missing))

if len(winners) != 3:
    raise SystemExit(f"Expected 3 winners, got {len(winners)}")

print("Evaluator tuning telemetry smoke test passed")
print("Observed telemetry excerpt:")
for line in output.splitlines():
    if "Evaluator Tuning" in line:
        print(line)
