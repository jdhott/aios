from __future__ import annotations

from typing import Any

from aios.storage.supabase_store import SupabaseStore


PROJECT_ANCHOR_ROLE = "project_anchor"


def mark_project_anchor(
    store: SupabaseStore,
    task_id: str,
) -> dict[str, Any]:
    rows = (
        store.client
        .table("tasks")
        .select("id,title,task_role")
        .eq("id", task_id)
        .limit(1)
        .execute()
        .data
        or []
    )

    if not rows:
        raise RuntimeError(
            f"Task {task_id} not found."
        )

    current = dict(rows[0])

    if current.get("task_role") == PROJECT_ANCHOR_ROLE:
        return current

    response = (
        store.client
        .table("tasks")
        .update({
            "task_role": PROJECT_ANCHOR_ROLE,
        })
        .eq("id", task_id)
        .execute()
    )

    updated = response.data or []

    if not updated:
        raise RuntimeError(
            "Project-anchor task update returned no row."
        )

    return dict(updated[0])
