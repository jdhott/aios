from __future__ import annotations

from typing import Any, Optional

from aios.models import Task
from aios.storage.execution_repository import ExecutionRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


def _title_property(value: str) -> dict[str, Any]:
    return {
        "type": "title",
        "title": [{"plain_text": value, "text": {"content": value}}],
    }


def _select_property(value: Optional[str]) -> dict[str, Any]:
    return {"type": "select", "select": {"name": value} if value else None}


def _checkbox_property(value: bool) -> dict[str, Any]:
    return {"type": "checkbox", "checkbox": bool(value)}


def _date_property(value) -> dict[str, Any]:
    return {"type": "date", "date": {"start": value.isoformat()} if value else None}


def _number_property(value: Optional[int | float]) -> dict[str, Any]:
    return {"type": "number", "number": value}


def task_to_legacy_execution_payload(
    task: Task,
    execution_state: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Convert Supabase task + current Supabase execution state to legacy engine payload."""
    execution_state = execution_state or {}
    return {
        "id": task.legacy_notion_id or task.id,
        "_supabase_id": task.id,
        "_source": "supabase",
        "properties": {
            "Task Name": _title_property(task.title),
            "Open Loop": _checkbox_property(task.is_open),
            "Done": _checkbox_property(task.is_done),
            "Archived": _checkbox_property(task.is_archived),
            "Status": _select_property(task.status),
            "Importance": _select_property(task.importance),
            "Urgency": _select_property(task.urgency),
            "Effort": _select_property(task.effort),
            "Duration": _select_property(task.duration),
            "Due Date": _date_property(task.due_at),
            "Defer Until": _date_property(task.defer_until),
            "Just Do It": _checkbox_property(task.is_just_do_it),
            "Quick Win": _checkbox_property(task.is_quick_win),
            "Execution Score": _number_property(execution_state.get("execution_score")),
            "Execution Rank": _number_property(execution_state.get("execution_rank")),
            "Best Next Action": _checkbox_property(bool(execution_state.get("best_next_action", False))),
            "Surfaced Quick Win": _checkbox_property(bool(execution_state.get("surfaced_quick_win", False))),
        },
    }


def get_supabase_execution_tasks() -> list[dict[str, Any]]:
    """
    Return current execution reconciliation population using Supabase only.

    tasks -> TaskRepository
    task_execution_state -> ExecutionRepository
    Population mirrors the current runtime query: Done = False.
    """
    print("[Execution Task Source] Loading durable task data from Supabase")
    store = SupabaseStore()
    task_repository = TaskRepository(store)
    execution_repository = ExecutionRepository(store)

    all_tasks = task_repository.get_all_tasks()
    execution_population = [task for task in all_tasks if not task.is_done]
    print(
        "[Execution Task Source] "
        f"Supabase non-done task population: {len(execution_population)}"
    )

    current_state = execution_repository.get_current_state()
    print(
        "[Execution Task Source] "
        f"Supabase current execution-state rows: {len(current_state)}"
    )

    payloads: list[dict[str, Any]] = []
    state_hits = 0
    for task in execution_population:
        state = current_state.get(task.id, {})
        if state:
            state_hits += 1
        payloads.append(task_to_legacy_execution_payload(task, state))

    print(
        "[Execution Task Source] "
        f"Execution payloads created: {len(payloads)}"
    )
    print(
        "[Execution Task Source] "
        f"Execution population tasks with current Supabase state: {state_hits}"
    )
    return payloads
