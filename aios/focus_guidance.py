"""Single-focus guidance for the AIOS dashboard."""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any

FOCUS_GUIDANCE_VERSION = "focus-guidance-v1"
_ALLOWED_MINUTES = (5, 10, 15, 20)


def _plain_title(task: dict[str, Any]) -> str:
    direct = str(task.get("title") or "").strip()
    if direct:
        return direct
    props = task.get("properties") or {}
    for key in ("Task Name", "Name", "Title"):
        prop = props.get(key) or {}
        parts = prop.get("title") or prop.get("rich_text") or []
        text = "".join(
            str(item.get("plain_text") or item.get("text", {}).get("content") or "")
            for item in parts if isinstance(item, dict)
        ).strip()
        if text:
            return text
    return "Untitled task"


def _generation_key(task_id: str, title: str) -> str:
    raw = f"{FOCUS_GUIDANCE_VERSION}|{task_id}|{title}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _resolve_supabase_task(store, task: dict[str, Any]) -> dict[str, Any] | None:
    task_id = str(task.get("id") or "").strip()
    if not task_id:
        return None
    rows = (store.client.table("tasks").select("id,title,legacy_notion_id").eq("id", task_id).limit(1).execute().data or [])
    if rows:
        return dict(rows[0])
    rows = (store.client.table("tasks").select("id,title,legacy_notion_id").eq("legacy_notion_id", task_id).limit(1).execute().data or [])
    return dict(rows[0]) if rows else None


def _normalize_minutes(value: Any) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return 10
    return min(_ALLOWED_MINUTES, key=lambda option: abs(option - minutes))


def _fallback_guidance(title: str) -> dict[str, Any]:
    return {
        "starter_step": f"Spend 10 minutes defining the smallest concrete next move for “{title}”.",
        "starter_minutes": 10,
        "source": "fallback",
    }


def generate_focus_guidance(client, title: str) -> dict[str, Any]:
    if client is None:
        return _fallback_guidance(title)
    model = os.getenv("AIOS_FOCUS_GUIDANCE_MODEL", "gpt-4.1-mini")
    prompt = f'''You are helping a person start ONE already-selected priority task.

Task: {title}

Return JSON only with exactly:
{{"starter_step":"...","starter_minutes":10}}

Rules:
- Do not re-rank the task.
- Give one tiny, concrete starting action that reduces activation energy.
- Do not say merely "work on it", "get started", or "break it down".
- Do not invent people, deadlines, places, tools, or facts not in the task.
- starter_minutes is ONLY for this starting action, never the whole task.
- Choose 5, 10, 15, or 20 minutes.
- Prefer 5 or 10 minutes when useful progress can start quickly.
- Keep starter_step under 180 characters when possible.'''
    try:
        response = client.responses.create(model=model, input=prompt)
        raw = (response.output_text or "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        data = json.loads(raw)
        step = str(data.get("starter_step") or "").strip()
        if not step:
            return _fallback_guidance(title)
        return {
            "starter_step": step[:300],
            "starter_minutes": _normalize_minutes(data.get("starter_minutes")),
            "source": "ai",
        }
    except Exception as exc:
        print(f"[Focus Guidance] AI generation failed: {exc}")
        return _fallback_guidance(title)


def ensure_focus_guidance(store, client, execution_task: dict[str, Any]) -> dict[str, Any] | None:
    resolved = _resolve_supabase_task(store, execution_task)
    if not resolved:
        print("[Focus Guidance] Could not resolve current BNA to Supabase task.")
        return None
    task_id = str(resolved["id"])
    title = str(resolved.get("title") or _plain_title(execution_task)).strip()
    generation_key = _generation_key(task_id, title)
    rows = (store.client.table("task_focus_guidance").select("*").eq("task_id", task_id).limit(1).execute().data or [])
    if rows and rows[0].get("generation_key") == generation_key:
        print(f"[Focus Guidance] Reusing cached guidance for: {title}")
        return dict(rows[0])
    guidance = generate_focus_guidance(client, title)
    row = {
        "task_id": task_id,
        "generation_key": generation_key,
        "starter_step": guidance["starter_step"],
        "starter_minutes": guidance["starter_minutes"],
        "source": guidance["source"],
    }
    result = store.client.table("task_focus_guidance").upsert(row, on_conflict="task_id").execute()
    saved = (result.data or [row])[0]
    print(f"[Focus Guidance] Saved {guidance['starter_minutes']}-minute starter for: {title}")
    return dict(saved)
