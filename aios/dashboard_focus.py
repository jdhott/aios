"""Shared dashboard focus resolution for API fast paths."""
from __future__ import annotations

import os
from typing import Any

from aios.storage.supabase_store import SupabaseStore
from aios.temporal import is_future_task_datetime

DASHBOARD_FOCUS_RESOLVER_VERSION = "dashboard-focus-resolver-v1"


def _is_future_defer(value: str | None) -> bool:
    try:
        return is_future_task_datetime(
            value,
            timezone_name=os.getenv("AIOS_LOCAL_TIMEZONE", "America/Toronto"),
        )
    except (TypeError, ValueError):
        return False


def resolve_dashboard_focus_task(store: SupabaseStore) -> dict[str, Any] | None:
    """Return the current actionable BNA task, skipping deferred rows."""
    states = (
        store.client.table("task_execution_state")
        .select("task_id,execution_score,execution_rank,best_next_action")
        .not_.is_("execution_rank", "null")
        .order("execution_rank")
        .limit(25)
        .execute()
        .data
        or []
    )
    if not states:
        return None

    for candidate_state in states:
        candidate_id = candidate_state.get("task_id")
        if not candidate_id:
            continue
        tasks = (
            store.client.table("tasks")
            .select(
                "id,title,context,status,due_at,defer_until,importance,urgency,effort,"
                "duration,project_id,parent_task_id,is_quick_win,is_just_do_it,is_open,"
                "is_done,is_archived,focus_context_help_state,focus_context_draft,"
                "focus_context_question"
            )
            .eq("id", candidate_id)
            .eq("is_open", True)
            .eq("is_done", False)
            .eq("is_archived", False)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not tasks:
            continue
        candidate_task = dict(tasks[0])
        if _is_future_defer(candidate_task.get("defer_until")):
            continue
        candidate_task["execution_score"] = candidate_state.get("execution_score")
        candidate_task["execution_rank"] = candidate_state.get("execution_rank")
        candidate_task["best_next_action"] = bool(
            candidate_state.get("best_next_action", False)
        )
        return candidate_task

    return None
