from __future__ import annotations

import json
import os
from typing import Any

from aios.storage.supabase_store import SupabaseStore


FOCUS_ACTIVATION_SOURCE = "focus_activation"
_ALLOWED_MINUTES = (5, 10, 15)


def _plain_title(task: dict[str, Any]) -> str:
    direct = str(task.get("title") or "").strip()
    if direct:
        return direct

    props = task.get("properties") or {}
    for key in ("Task Name", "Name", "Title"):
        prop = props.get(key) or {}
        parts = prop.get("title") or prop.get("rich_text") or []
        text = "".join(
            str(
                item.get("plain_text")
                or item.get("text", {}).get("content")
                or ""
            )
            for item in parts
            if isinstance(item, dict)
        ).strip()
        if text:
            return text

    return "Untitled task"


def _resolve_supabase_task(
    store: SupabaseStore,
    task: dict[str, Any],
) -> dict[str, Any] | None:
    task_id = str(task.get("id") or "").strip()
    if not task_id:
        return None

    rows = (
        store.client
        .table("tasks")
        .select("id,title,legacy_notion_id,is_open,is_done,is_archived")
        .eq("id", task_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if rows:
        return dict(rows[0])

    rows = (
        store.client
        .table("tasks")
        .select("id,title,legacy_notion_id,is_open,is_done,is_archived")
        .eq("legacy_notion_id", task_id)
        .limit(1)
        .execute()
        .data
        or []
    )

    return dict(rows[0]) if rows else None


def _normalize_minutes(value: Any) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return 10

    return min(
        _ALLOWED_MINUTES,
        key=lambda option: abs(option - minutes),
    )


def list_focus_activation_children(
    store: SupabaseStore,
    parent_task_id: str,
) -> list[dict[str, Any]]:
    rows = (
        store.client
        .table("tasks")
        .select(
            "id,title,is_open,is_done,is_archived,is_just_do_it,"
            "parent_task_id,step_order,generated_source,duration,"
            "created_at,updated_at,completed_at"
        )
        .eq("parent_task_id", parent_task_id)
        .eq("generated_source", FOCUS_ACTIVATION_SOURCE)
        .order("step_order")
        .execute()
        .data
        or []
    )

    return list(rows)


def get_active_focus_activation(
    store: SupabaseStore,
    parent_task_id: str,
) -> dict[str, Any] | None:
    rows = (
        store.client
        .table("tasks")
        .select(
            "id,title,is_open,is_done,is_archived,is_just_do_it,"
            "parent_task_id,step_order,generated_source,duration"
        )
        .eq("parent_task_id", parent_task_id)
        .eq("generated_source", FOCUS_ACTIVATION_SOURCE)
        .eq("is_open", True)
        .eq("is_done", False)
        .eq("is_archived", False)
        .order("step_order")
        .limit(1)
        .execute()
        .data
        or []
    )

    return dict(rows[0]) if rows else None


def next_focus_activation_step_order(
    store: SupabaseStore,
    parent_task_id: str,
) -> int:
    rows = list_focus_activation_children(
        store,
        parent_task_id,
    )

    existing_orders = [
        int(row["step_order"])
        for row in rows
        if row.get("step_order") is not None
    ]

    return max(existing_orders, default=0) + 1


def create_focus_activation_child(
    store: SupabaseStore,
    *,
    parent_task_id: str,
    title: str,
    minutes: int = 10,
) -> dict[str, Any]:
    existing = get_active_focus_activation(
        store,
        parent_task_id,
    )

    if existing:
        return existing

    step_order = next_focus_activation_step_order(
        store,
        parent_task_id,
    )

    minutes = _normalize_minutes(minutes)

    response = (
        store.client
        .table("tasks")
        .insert({
            "legacy_notion_id": None,
            "title": title,
            "is_open": True,
            "is_done": False,
            "is_archived": False,
            "is_just_do_it": True,
            "is_quick_win": False,
            "duration": f"{minutes} min",
            "parent_task_id": parent_task_id,
            "step_order": step_order,
            "generated_source": FOCUS_ACTIVATION_SOURCE,
        })
        .execute()
    )

    rows = response.data or []

    if not rows:
        raise RuntimeError(
            "Focus activation child insert returned no row."
        )

    return dict(rows[0])


def generate_next_focus_activation(
    client,
    *,
    parent_title: str,
    completed_steps: list[str],
) -> dict[str, Any] | None:
    """
    Generate exactly one next JDI-sized activation step.

    Unlike the older dashboard guidance feature, this creates durable task
    state. If AI generation fails, return None rather than creating a generic
    fallback task.
    """
    if client is None:
        return None

    history = "\n".join(
        f"{index}. {step}"
        for index, step in enumerate(completed_steps, start=1)
    )

    if not history:
        history = "(No activation steps completed yet.)"

    model = os.getenv(
        "AIOS_FOCUS_GUIDANCE_MODEL",
        "gpt-4.1-mini",
    )

    prompt = f"""You are helping a person make progress on ONE already-selected priority task.

Parent task:
{parent_title}

Previously completed activation steps:
{history}

Generate exactly ONE next small action.

Return JSON only with exactly:
{{"title":"...","minutes":10}}

Rules:
- The action must advance the parent task.
- Do not repeat or substantially duplicate any completed activation step.
- It must be a concrete action the person can do now.
- Treat it as a Just Do It task: small, low-friction, and immediately executable.
- Prefer an action that can be completed in 5 to 15 minutes.
- Do not generate a plan or checklist containing multiple actions.
- Do not merely say "continue", "work on it", "get started", or "break it down".
- Do not invent people, deadlines, places, preferences, tools, or facts not provided.
- Choose minutes from 5, 10, or 15.
- Keep the title under 180 characters when possible.
"""

    try:
        response = client.responses.create(
            model=model,
            input=prompt,
        )

        raw = (response.output_text or "").strip()

        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        data = json.loads(raw)

        title = str(data.get("title") or "").strip()
        if not title:
            return None

        # Basic duplicate guard in addition to the prompt.
        normalized_title = " ".join(title.lower().split())
        normalized_history = {
            " ".join(step.lower().split())
            for step in completed_steps
        }

        if normalized_title in normalized_history:
            print(
                "[Focus Activation] AI returned an already-completed step; "
                "no child created."
            )
            return None

        return {
            "title": title[:300],
            "minutes": _normalize_minutes(data.get("minutes")),
        }

    except Exception as exc:
        print(
            f"[Focus Activation] AI generation failed: {exc}"
        )
        return None


def ensure_next_focus_activation(
    store: SupabaseStore,
    client,
    execution_task: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Ensure the current BNA has exactly one active activation child.

    If an active child already exists, reuse it.
    Otherwise generate the next child using completed activation history.
    """
    resolved = _resolve_supabase_task(
        store,
        execution_task,
    )

    if not resolved:
        print(
            "[Focus Activation] Could not resolve current BNA "
            "to Supabase task."
        )
        return None

    if (
        not resolved.get("is_open", True)
        or resolved.get("is_done")
        or resolved.get("is_archived")
    ):
        return None

    parent_task_id = str(resolved["id"])
    parent_title = str(
        resolved.get("title")
        or _plain_title(execution_task)
    ).strip()

    existing = get_active_focus_activation(
        store,
        parent_task_id,
    )

    if existing:
        print(
            f"[Focus Activation] Reusing active step "
            f"{existing.get('step_order')} for: {parent_title}"
        )
        return existing

    history = list_focus_activation_children(
        store,
        parent_task_id,
    )

    completed_steps = [
        str(row.get("title") or "").strip()
        for row in history
        if row.get("is_done")
        and not row.get("is_archived")
        and str(row.get("title") or "").strip()
    ]

    generated = generate_next_focus_activation(
        client,
        parent_title=parent_title,
        completed_steps=completed_steps,
    )

    if not generated:
        print(
            f"[Focus Activation] No new activation step generated for: "
            f"{parent_title}"
        )
        return None

    child = create_focus_activation_child(
        store,
        parent_task_id=parent_task_id,
        title=generated["title"],
        minutes=generated["minutes"],
    )

    print(
        f"[Focus Activation] Created step "
        f"{child.get('step_order')} "
        f"({generated['minutes']} min) for: {parent_title}"
    )

    return child
