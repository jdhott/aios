"""
AIOS Metadata Reconciliation — Phase 2.0 Closed-Task Execution Persistence Guard

Early runtime guard that prevents stale execution metadata from being written onto
closed/done tasks. This is intentionally narrow:

- Only intercepts Notion page PATCH calls.
- Only acts when the target page is known in runtime objects and is closed/done.
- Only strips non-null Execution Score / Execution Rank writes.
- Allows cleanup writes that set those fields to null.
- Leaves all other properties and requests untouched.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Set
import inspect
import re

VERSION = "metadata-reconciliation-phase2-closed-task-persistence-guard-v0.2.0"
_PATCHED = False
_ORIGINAL_PATCH = None
_BLOCKED_WRITES = 0
_STRIPPED_WRITES = 0

_EXECUTION_PROPERTY_NAMES = {"execution score", "score", "execution rank", "rank"}


def _plain_text(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, (int, float, bool)):
        return str(obj)
    if isinstance(obj, list):
        return "".join(_plain_text(x) for x in obj)
    if isinstance(obj, dict):
        if "plain_text" in obj:
            return str(obj.get("plain_text") or "")
        if "title" in obj:
            return _plain_text(obj.get("title"))
        if "rich_text" in obj:
            return _plain_text(obj.get("rich_text"))
        if "checkbox" in obj:
            return _plain_text(obj.get("checkbox"))
        if "formula" in obj:
            return _plain_text(obj.get("formula"))
        if "select" in obj:
            return _plain_text(obj.get("select"))
        if "status" in obj:
            return _plain_text(obj.get("status"))
        if "name" in obj:
            return str(obj.get("name") or "")
    return ""


def _bool(obj: Any) -> bool:
    if obj is None:
        return False
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, dict):
        if isinstance(obj.get("checkbox"), bool):
            return bool(obj["checkbox"])
        if isinstance(obj.get("formula"), dict) and isinstance(obj["formula"].get("boolean"), bool):
            return bool(obj["formula"]["boolean"])
    return _plain_text(obj).strip().lower() in {"true", "yes", "y", "1", "checked", "done"}


def _prop_value(properties: Mapping[str, Any], candidates: list[str]) -> Any:
    lower_map = {str(k).strip().lower(): v for k, v in properties.items()}
    for name in candidates:
        if name in properties:
            return properties[name]
        v = lower_map.get(name.strip().lower())
        if v is not None:
            return v
    return None


def _looks_like_page(obj: Any) -> bool:
    return isinstance(obj, Mapping) and isinstance(obj.get("properties"), Mapping)


def _is_closed_or_done_page(page: Mapping[str, Any]) -> bool:
    props = page.get("properties", {})
    if not isinstance(props, Mapping):
        return False
    done = _bool(_prop_value(props, ["Done", "Complete", "Completed"]))
    open_loop_raw = _prop_value(props, ["Open Loop", "Open", "Active"])
    open_loop = _bool(open_loop_raw) if open_loop_raw is not None else not done
    return bool(done or (open_loop_raw is not None and not open_loop))


def _collect_closed_page_ids_from_frame_globals() -> Set[str]:
    ids: Set[str] = set()
    seen: Set[int] = set()

    def add_from_obj(obj: Any) -> None:
        oid = id(obj)
        if oid in seen:
            return
        seen.add(oid)
        if _looks_like_page(obj):
            pid = str(obj.get("id") or "")
            if pid and _is_closed_or_done_page(obj):
                ids.add(pid)
        elif isinstance(obj, list):
            for item in obj:
                add_from_obj(item)
        elif isinstance(obj, dict):
            for key in ("results", "items", "tasks", "pages", "open_tasks", "all_tasks"):
                inner = obj.get(key)
                if isinstance(inner, list):
                    add_from_obj(inner)

    frame = inspect.currentframe()
    if frame is None:
        return ids
    try:
        # Walk outward from the requests.patch wrapper into the runtime caller stack.
        f = frame.f_back
        depth = 0
        while f is not None and depth < 12:
            for value in f.f_globals.values():
                add_from_obj(value)
            for value in f.f_locals.values():
                add_from_obj(value)
            f = f.f_back
            depth += 1
    finally:
        del frame
    return ids


def _extract_page_id_from_url(url: Any) -> Optional[str]:
    text = str(url or "")
    m = re.search(r"/v1/pages/([^/?#]+)", text)
    return m.group(1) if m else None


def _is_non_null_execution_write(prop_name: str, prop_value: Any) -> bool:
    if prop_name.strip().lower() not in _EXECUTION_PROPERTY_NAMES:
        return False
    if not isinstance(prop_value, Mapping):
        return True
    if "number" in prop_value:
        return prop_value.get("number") is not None
    # Conservative: other encodings of execution writes are considered non-null.
    return True


class _GuardedResponse:
    status_code = 200
    text = "AIOS metadata persistence guard stripped closed-task execution write"

    def json(self) -> Dict[str, Any]:
        return {"object": "page", "aios_guard": True}

    @property
    def ok(self) -> bool:
        return True


def install_closed_task_execution_persistence_guard() -> bool:
    global _PATCHED, _ORIGINAL_PATCH
    if _PATCHED:
        return True
    try:
        import requests  # type: ignore
    except Exception as exc:
        print(f"[Metadata Persistence Guard] Install skipped: requests unavailable: {exc}")
        return False

    original_patch = requests.patch
    _ORIGINAL_PATCH = original_patch

    def guarded_patch(url: Any, *args: Any, **kwargs: Any) -> Any:
        global _BLOCKED_WRITES, _STRIPPED_WRITES
        page_id = _extract_page_id_from_url(url)
        payload = kwargs.get("json")
        properties = payload.get("properties") if isinstance(payload, Mapping) else None
        if page_id and isinstance(properties, Mapping):
            closed_ids = _collect_closed_page_ids_from_frame_globals()
            if page_id in closed_ids:
                stripped = {
                    name: value
                    for name, value in properties.items()
                    if _is_non_null_execution_write(str(name), value)
                }
                if stripped:
                    _STRIPPED_WRITES += len(stripped)
                    new_properties = {k: v for k, v in properties.items() if k not in stripped}
                    if new_properties:
                        new_payload = dict(payload)
                        new_payload["properties"] = new_properties
                        kwargs["json"] = new_payload
                        print(
                            "[Metadata Persistence Guard] Stripped closed/done execution write: "
                            f"page={page_id}, fields={', '.join(stripped.keys())}"
                        )
                    else:
                        _BLOCKED_WRITES += 1
                        print(
                            "[Metadata Persistence Guard] Blocked closed/done execution-only write: "
                            f"page={page_id}, fields={', '.join(stripped.keys())}"
                        )
                        return _GuardedResponse()
        return original_patch(url, *args, **kwargs)

    requests.patch = guarded_patch
    _PATCHED = True
    print(f"[Metadata Persistence Guard] Closed-task execution persistence guard installed — {VERSION}")
    return True


def guard_status_lines() -> list[str]:
    return [
        f"[Metadata Persistence Guard] Version: {VERSION}",
        f"[Metadata Persistence Guard] Installed: {_PATCHED}",
        f"[Metadata Persistence Guard] Execution-only writes blocked: {_BLOCKED_WRITES}",
        f"[Metadata Persistence Guard] Execution fields stripped: {_STRIPPED_WRITES}",
    ]
