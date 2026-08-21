"""Lightweight Start Here refresh without a full processor run."""
from __future__ import annotations

import os
from typing import Any

from aios.dashboard_focus import resolve_dashboard_focus_task
from aios.focus_activation import (
    FOCUS_ACTIVATION_SOURCE,
    ensure_next_focus_activation,
    get_active_focus_activation,
)
from aios.storage.supabase_store import SupabaseStore

FOCUS_ACTIVATION_REFRESH_VERSION = "focus-activation-refresh-v2"


def get_openai_client():
    """Return an OpenAI client when configured, otherwise None."""
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return None

    from openai import OpenAI

    return OpenAI(api_key=api_key)


def resolve_focus_parent_task_id(
    store: SupabaseStore,
    task_id: str,
) -> str | None:
    """Resolve a BNA parent id from a task id or activation child id."""
    rows = (
        store.client.table("tasks")
        .select("id,parent_task_id,generated_source,is_open,is_done,is_archived")
        .eq("id", task_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return None

    task = dict(rows[0])
    if task.get("generated_source") == FOCUS_ACTIVATION_SOURCE:
        parent_id = str(task.get("parent_task_id") or "").strip()
        return parent_id or None

    if task.get("is_done") or task.get("is_archived") or not task.get("is_open"):
        return None

    return str(task.get("id") or "").strip() or None


def refresh_focus_activation_for_parent(
    store: SupabaseStore,
    client,
    parent_task_id: str,
) -> dict[str, Any] | None:
    """Generate the next Start Here child for an open BNA parent task."""
    parent_id = str(parent_task_id or "").strip()
    if not parent_id:
        return None

    existing = get_active_focus_activation(store, parent_id)
    if existing:
        return existing

    return ensure_next_focus_activation(
        store,
        client,
        {"id": parent_id},
    )


def refresh_dashboard_focus_activation(
    store: SupabaseStore,
    client,
) -> dict[str, Any] | None:
    """Ensure Start Here exists for whichever task is currently in focus."""
    focus = resolve_dashboard_focus_task(store)
    if not focus:
        return None
    focus_id = str(focus.get("id") or "").strip()
    if not focus_id:
        return None
    return refresh_focus_activation_for_parent(store, client, focus_id)


def refresh_focus_activation_for_task(
    store: SupabaseStore,
    client,
    task_id: str,
) -> dict[str, Any] | None:
    """Refresh Start Here for a BNA parent or activation child task id."""
    parent_id = resolve_focus_parent_task_id(store, task_id)
    if not parent_id:
        return None
    return refresh_focus_activation_for_parent(store, client, parent_id)
