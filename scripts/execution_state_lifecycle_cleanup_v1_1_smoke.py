#!/usr/bin/env python3
from types import SimpleNamespace
from unittest.mock import patch

import aios.storage.execution_task_source as source


class FakeTaskRepository:
    def __init__(self, _store):
        pass

    def get_all_tasks(self):
        return [
            SimpleNamespace(
                id="open-task",
                legacy_notion_id="notion-open",
                title="Open task",
                is_open=True,
                is_done=False,
                is_archived=False,
                status=None,
                importance=None,
                urgency=None,
                effort=None,
                duration=None,
                due_at=None,
                defer_until=None,
                is_just_do_it=False,
                is_quick_win=False,
            ),
            SimpleNamespace(
                id="archived-task",
                legacy_notion_id="notion-archived",
                title="Archived task",
                is_open=False,
                is_done=False,
                is_archived=True,
                status=None,
                importance=None,
                urgency=None,
                effort=None,
                duration=None,
                due_at=None,
                defer_until=None,
                is_just_do_it=False,
                is_quick_win=False,
            ),
            SimpleNamespace(
                id="closed-task",
                legacy_notion_id="notion-closed",
                title="Closed task",
                is_open=False,
                is_done=False,
                is_archived=False,
                status=None,
                importance=None,
                urgency=None,
                effort=None,
                duration=None,
                due_at=None,
                defer_until=None,
                is_just_do_it=False,
                is_quick_win=False,
            ),
            SimpleNamespace(
                id="done-task",
                legacy_notion_id="notion-done",
                title="Done task",
                is_open=False,
                is_done=True,
                is_archived=False,
                status=None,
                importance=None,
                urgency=None,
                effort=None,
                duration=None,
                due_at=None,
                defer_until=None,
                is_just_do_it=False,
                is_quick_win=False,
            ),
        ]


class FakeExecutionRepository:
    cleared = []

    def __init__(self, _store):
        pass

    def get_current_state(self):
        return {
            "open-task": {
                "execution_score": 20,
                "execution_rank": 1,
                "best_next_action": True,
                "surfaced_quick_win": False,
            },
            "archived-task": {
                "execution_score": 28,
                "execution_rank": 3,
                "best_next_action": True,
                "surfaced_quick_win": False,
            },
            "closed-task": {
                "execution_score": 18,
                "execution_rank": 4,
                "best_next_action": False,
                "surfaced_quick_win": False,
            },
            "done-task": {
                "execution_score": 10,
                "execution_rank": 7,
                "best_next_action": False,
                "surfaced_quick_win": False,
            },
        }

    def clear_execution_state(self, task_ids, **_kwargs):
        self.__class__.cleared.extend(task_ids)


FakeExecutionRepository.cleared = []

with patch.object(source, "SupabaseStore", lambda: object()), \
     patch.object(source, "TaskRepository", FakeTaskRepository), \
     patch.object(source, "ExecutionRepository", FakeExecutionRepository):
    payloads = source.get_supabase_execution_tasks()

assert set(FakeExecutionRepository.cleared) == {
    "archived-task",
    "closed-task",
    "done-task",
}

# Critical v1.1 assertion:
# only genuinely active tasks reach Execution Engine V2.
payload_ids = {row["_supabase_id"] for row in payloads}
assert payload_ids == {"open-task"}

props = payloads[0]["properties"]
assert props["Execution Score"]["number"] == 20
assert props["Execution Rank"]["number"] == 1
assert props["Best Next Action"]["checkbox"] is True

print("Closed/archived/done stale state identified: PASS")
print("Repository cleanup invoked: PASS")
print("Archived task excluded from execution population: PASS")
print("Closed non-done task excluded from execution population: PASS")
print("Done task excluded from execution population: PASS")
print("Open active task preserved: PASS")
print(
    "RESULT: EXECUTION STATE LIFECYCLE CLEANUP V1.1 SMOKE TEST PASSED"
)
