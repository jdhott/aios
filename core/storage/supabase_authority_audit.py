"""Observational audit of Notion mutations while Supabase is authoritative."""
from __future__ import annotations
import atexit, inspect, re
from collections import Counter
from dataclasses import dataclass

VERSION = "supabase-authority-audit-v1.1.0"
_INSTALLED = False
_ENABLED = False
_EVENTS = []


@dataclass
class AuditEvent:
    method: str
    url: str
    category: str
    detail: str
    caller: str


def _caller():
    f = inspect.currentframe()
    try:
        f = f.f_back if f else None
        for _ in range(20):
            if not f:
                break
            mod = str(f.f_globals.get("__name__", ""))
            name = f.f_code.co_name
            if mod != __name__ and not mod.startswith(("requests", "urllib3")):
                return f"{mod}.{name}"
            f = f.f_back
    finally:
        try:
            del f
        except Exception:
            pass
    return ""


def classify_mutation(method, url, payload=None):
    """Any Notion mutation is unexpected when Supabase is authoritative."""
    method = str(method).upper()
    url = str(url or "")
    return (
        "unexpected_notion",
        f"Notion {method} mutation observed in Supabase mode",
    )


def _record(method, url, payload=None):
    if not _ENABLED or "api.notion.com/v1/" not in str(url):
        return
    method_text = str(method).upper()
    url_text = str(url)
    # Notion database queries use HTTP POST but are read-only operations.
    # Keep them outside this mutation audit.
    if method_text == "POST" and re.search(
        r"/v1/databases/[^/?#]+/query(?:[?#].*)?$", url_text
    ):
        return
    category, detail = classify_mutation(method_text, url_text, payload)
    _EVENTS.append(
        AuditEvent(method_text, url_text, category, detail, _caller())
    )


def install_supabase_authority_audit(datastore):
    global _INSTALLED, _ENABLED
    if str(datastore).strip().lower() != "supabase":
        return False
    if _INSTALLED:
        _ENABLED = True
        return True

    import requests

    original_post = requests.post
    original_patch = requests.patch
    original_delete = requests.delete

    def post(url, *args, **kwargs):
        _record("POST", url, kwargs.get("json"))
        return original_post(url, *args, **kwargs)

    def patch(url, *args, **kwargs):
        _record("PATCH", url, kwargs.get("json"))
        return original_patch(url, *args, **kwargs)

    def delete(url, *args, **kwargs):
        _record("DELETE", url, kwargs.get("json"))
        return original_delete(url, *args, **kwargs)

    requests.post = post
    requests.patch = patch
    requests.delete = delete
    _INSTALLED = True
    _ENABLED = True
    atexit.register(emit_report)
    print(f"[Supabase Authority Audit] Installed — {VERSION}")
    return True


def emit_report():
    if not _ENABLED:
        return
    counts = Counter(event.category for event in _EVENTS)
    print("\n=== SUPABASE AUTHORITY AUDIT ===")
    print(f"[Supabase Authority Audit] Version: {VERSION}")
    print(
        "[Supabase Authority Audit] "
        f"Notion mutations observed: {len(_EVENTS)}"
    )
    print(
        "[Supabase Authority Audit] Unexpected Notion mutations: "
        f"{counts['unexpected_notion']}"
    )
    for event in _EVENTS[:20]:
        print(
            "[Supabase Authority Audit] unexpected_notion: "
            f"{event.method} {event.url} "
            f"caller={event.caller or 'unknown'} detail={event.detail}"
        )
    print(
        "RESULT: SUPABASE CORE PERSISTENCE AUTHORITY CLEAN"
        if not _EVENTS
        else "RESULT: SUPABASE CORE PERSISTENCE AUTHORITY NEEDS REVIEW"
    )
