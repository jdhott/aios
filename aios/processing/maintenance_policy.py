"""Decide when processor runs should invoke expensive AI maintenance passes."""
from __future__ import annotations

import os
from typing import Any

from aios.storage.supabase_store import SupabaseStore

PROCESSOR_LIGHT_MAINTENANCE_VERSION = "processor-light-maintenance-v1"

_PENDING_FOCUS_CONTEXT_STATES = ("pending", "answer_pending")
_PENDING_PROJECT_WORK_STATES = (
    "pending",
    "answer_pending",
    "clarification",
    "context_review",
)


def _parse_env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def has_pending_inbox_work(inbox_items: list[Any] | None) -> bool:
    return bool(inbox_items)


def has_pipeline_activity(run_summary: dict[str, Any] | None) -> bool:
    summary = run_summary or {}
    return any(
        int(summary.get(key) or 0) > 0
        for key in (
            "tasks_created",
            "new_items_identified",
            "items_processed",
            "breakdown_parents_created",
            "clarification_tasks_created",
        )
    )


def has_pending_ai_work(store: SupabaseStore) -> bool:
    client = store.client

    pending_breakdown = (
        client.table("tasks")
        .select("id")
        .eq("breakdown_state", "pending")
        .limit(1)
        .execute()
        .data
        or []
    )
    if pending_breakdown:
        return True

    pending_focus_context = (
        client.table("tasks")
        .select("id")
        .in_("focus_context_help_state", list(_PENDING_FOCUS_CONTEXT_STATES))
        .limit(1)
        .execute()
        .data
        or []
    )
    if pending_focus_context:
        return True

    pending_project_work = (
        client.table("projects")
        .select("id")
        .in_("work_generation_state", list(_PENDING_PROJECT_WORK_STATES))
        .limit(1)
        .execute()
        .data
        or []
    )
    if pending_project_work:
        return True

    return False


def should_run_heavy_ai_maintenance(
    *,
    inbox_items: list[Any] | None,
    store: SupabaseStore,
    run_summary: dict[str, Any] | None = None,
) -> bool:
    """Return True when project discovery / project-work AI should run."""
    if _parse_env_bool("AIOS_FORCE_HEAVY_MAINTENANCE", False):
        return True

    if _parse_env_bool("AIOS_SKIP_HEAVY_MAINTENANCE", False):
        return False

    if has_pending_inbox_work(inbox_items):
        return True

    if has_pipeline_activity(run_summary):
        return True

    if has_pending_ai_work(store):
        return True

    return False
