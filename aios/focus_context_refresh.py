"""Lightweight focus context coaching without a full processor run."""
from __future__ import annotations

from typing import Any

from aios.focus_context import ensure_focus_context_help
from aios.storage.supabase_store import SupabaseStore

FOCUS_CONTEXT_REFRESH_VERSION = "focus-context-refresh-v1"


def refresh_focus_context_for_task(
    store: SupabaseStore,
    client,
    task_id: str,
) -> dict[str, Any] | None:
    """Run context coaching when help state is pending or answer_pending."""
    task_key = str(task_id or "").strip()
    if not task_key:
        return None
    return ensure_focus_context_help(
        store,
        client,
        {"id": task_key},
    )
