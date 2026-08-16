from __future__ import annotations

from typing import Any, Optional

from aios.models import Task
from aios.storage.execution_repository import ExecutionRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository

EXECUTION_STATE_LIFECYCLE_CLEANUP_VERSION = "v1.1"


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


def _rich_text_property(
    value: Optional[str],
) -> dict[str, Any]:
    text = str(value or "").strip()

    return {
        "type": "rich_text",
        "rich_text": (
            [{
                "plain_text": text,
                "text": {"content": text},
            }]
            if text
            else []
        ),
    }


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
            "Task Role": _rich_text_property(task.task_role),
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
    execution_population = [
        task
        for task in all_tasks
        if task.is_open
        and not task.is_done
        and not task.is_archived
    ]
    print(
        "[Execution Task Source] "
        f"Supabase active execution population: {len(execution_population)}"
    )

    current_state = execution_repository.get_current_state()

    # Lifecycle cleanup is intentionally separate from execution cognition.
    # A task that is Done, Archived, or no longer Open must not retain
    # canonical Execution Score / Rank / Best Next Action state.
    #
    # We do not change the population supplied to Execution Engine V2 here.
    # This cleanup only reconciles persisted state against durable task
    # lifecycle so closed tasks cannot occupy stale ranks indefinitely.
    task_by_id = {
        task.id: task
        for task in all_tasks
    }

    stale_state_task_ids = []

    for task_id, state in current_state.items():
        task = task_by_id.get(task_id)

        if task is None:
            continue

        lifecycle_closed = (
            task.is_done
            or task.is_archived
            or not task.is_open
        )

        has_execution_state = (
            state.get("execution_score") is not None
            or state.get("execution_rank") is not None
            or bool(state.get("best_next_action", False))
        )

        if lifecycle_closed and has_execution_state:
            stale_state_task_ids.append(task_id)

    if stale_state_task_ids:
        execution_repository.clear_execution_state(
            stale_state_task_ids
        )
        print(
            "[Execution Task Source] "
            "Cleared stale execution state for "
            f"{len(stale_state_task_ids)} closed task(s)"
        )

        # Keep the in-memory snapshot consistent with the just-cleared
        # canonical state so the remainder of this run cannot re-read stale
        # values from the pre-cleanup snapshot.
        for task_id in stale_state_task_ids:
            state = current_state.get(task_id)
            if not state:
                continue
            state["execution_score"] = None
            state["execution_rank"] = None
            state["best_next_action"] = False
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
