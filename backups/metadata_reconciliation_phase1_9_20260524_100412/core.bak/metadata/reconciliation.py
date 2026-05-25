"""
AIOS Metadata Reconciliation — Phase 1.8 Closed Task Execution Cleanup

Narrow mutation reconciliation layer.

Mutates only validated reconciliation conditions:
- stale Quick Win on future-deferred tasks
- meaningful Execution Score / Execution Rank on closed or done tasks

Safety boundary: this module mutates Notion only when:
- Defer Until is in the future and Quick Win is checked; OR
- a task is closed/done and has meaningful Execution Score / Execution Rank metadata.

It does not change Best Next Action, Do = Today, Focus, evaluator logic, or task content.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import datetime as _dt
import os
import re

VERSION = "metadata-reconciliation-phase1-closed-task-execution-cleanup-v0.1.8"
_MAX_EXAMPLES = 8


@dataclass
class ReconciliationFinding:
    key: str
    label: str
    count: int = 0
    examples: List[str] = field(default_factory=list)

    def add(self, title: str, detail: str = "") -> None:
        self.count += 1
        if title and len(self.examples) < _MAX_EXAMPLES:
            self.examples.append(f"{title} — {detail}" if detail else title)


@dataclass
class ReconciliationSummary:
    scanned: int = 0
    open_tasks: int = 0
    done_tasks: int = 0
    closed_tasks: int = 0
    findings: Dict[str, ReconciliationFinding] = field(default_factory=dict)

    def finding(self, key: str, label: str) -> ReconciliationFinding:
        if key not in self.findings:
            self.findings[key] = ReconciliationFinding(key=key, label=label)
        return self.findings[key]


def _prop_value(properties: Mapping[str, Any], candidates: Sequence[str]) -> Any:
    lower_map = {str(k).strip().lower(): v for k, v in properties.items()}
    for name in candidates:
        if name in properties:
            return properties[name]
        v = lower_map.get(name.strip().lower())
        if v is not None:
            return v
    return None


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
        if "text" in obj and isinstance(obj["text"], dict):
            return str(obj["text"].get("content") or "")
        if "name" in obj:
            return str(obj.get("name") or "")
        if "title" in obj:
            return _plain_text(obj.get("title"))
        if "rich_text" in obj:
            return _plain_text(obj.get("rich_text"))
        if "select" in obj:
            return _plain_text(obj.get("select"))
        if "status" in obj:
            return _plain_text(obj.get("status"))
        if "formula" in obj:
            return _plain_text(obj.get("formula"))
        if "number" in obj:
            return _plain_text(obj.get("number"))
        if "checkbox" in obj:
            return _plain_text(obj.get("checkbox"))
    return ""


def _number(obj: Any) -> Optional[float]:
    if obj is None:
        return None
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        return float(obj)
    if isinstance(obj, dict):
        if isinstance(obj.get("number"), (int, float)):
            return float(obj["number"])
        if isinstance(obj.get("formula"), dict):
            f = obj["formula"]
            for key in ("number", "string"):
                val = f.get(key)
                try:
                    if val not in (None, ""):
                        return float(val)
                except (TypeError, ValueError):
                    pass
    try:
        text = _plain_text(obj).strip()
        if text:
            return float(text)
    except (TypeError, ValueError):
        return None
    return None


def _bool(obj: Any) -> bool:
    if obj is None:
        return False
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, dict):
        if isinstance(obj.get("checkbox"), bool):
            return bool(obj["checkbox"])
        if isinstance(obj.get("formula"), dict):
            f = obj["formula"]
            if isinstance(f.get("boolean"), bool):
                return bool(f["boolean"])
    text = _plain_text(obj).strip().lower()
    return text in {"true", "yes", "y", "1", "checked", "done"}



def _select_name(obj: Any) -> str:
    if isinstance(obj, dict):
        if isinstance(obj.get("select"), dict):
            return str(obj["select"].get("name") or "")
        if isinstance(obj.get("status"), dict):
            return str(obj["status"].get("name") or "")
    return _plain_text(obj).strip()


def _closed_task_clear_preview_detail(
    *,
    quick_win: bool,
    best_next: bool,
    do_today: bool,
    focus_now: bool,
    exec_score: Optional[float],
    exec_rank: Optional[float],
) -> str:
    fields: List[str] = []
    if best_next:
        fields.append("Best Next Action=true")
    if do_today:
        fields.append("Do = Today=true")
    if quick_win:
        fields.append("Quick Win=true")
    if focus_now:
        fields.append("Focus Now=true")
    if exec_rank is not None:
        fields.append(f"Execution Rank={exec_rank:g}")
    if exec_score is not None:
        if exec_score == 0:
            fields.append("Execution Score=0 (present/default)")
        else:
            fields.append(f"Execution Score={exec_score:g}")
    return "Fields present: " + "; ".join(fields) if fields else "Fields present: none"


def _active_surface_details(
    *,
    quick_win: bool,
    best_next: bool,
    do_today: bool,
    focus_now: bool,
    exec_score: Optional[float],
    exec_rank: Optional[float],
    defer_text: str = "",
) -> str:
    parts: List[str] = []
    if defer_text:
        parts.append(f"Defer Until={defer_text}")
    if best_next:
        parts.append("Best Next Action=true")
    if do_today:
        parts.append("Do = Today=true")
    if quick_win:
        parts.append("Quick Win=true")
    if focus_now:
        parts.append("Focus Now=true")
    if exec_rank is not None:
        parts.append(f"Execution Rank={exec_rank:g}")
    if exec_score is not None:
        parts.append(f"Execution Score={exec_score:g}")
    return ", ".join(parts) if parts else "no active surface fields detected"


def _date_text(obj: Any) -> str:
    if isinstance(obj, dict):
        if isinstance(obj.get("date"), dict):
            return str(obj["date"].get("start") or "")
        if isinstance(obj.get("formula"), dict):
            return _date_text(obj.get("formula"))
        for k in ("start", "date", "string"):
            if obj.get(k):
                return str(obj[k])
    return _plain_text(obj)


def _today() -> _dt.date:
    return _dt.date.today()


def _is_future_date(obj: Any) -> bool:
    text = _date_text(obj).strip()
    if not text:
        return False
    try:
        # Notion dates may be YYYY-MM-DD or ISO datetimes.
        d = _dt.date.fromisoformat(text[:10])
        return d > _today()
    except ValueError:
        return False


def _task_title(page: Mapping[str, Any]) -> str:
    props = page.get("properties", {}) if isinstance(page, Mapping) else {}
    val = _prop_value(props, ["Task Name", "Name", "Title", "Task"])
    title = _plain_text(val).strip()
    if title:
        return title
    return str(page.get("id") or "Untitled task")[:80]


def _looks_like_page(obj: Any) -> bool:
    return isinstance(obj, Mapping) and isinstance(obj.get("properties"), Mapping)


def _extract_pages_from_globals(runtime_globals: Optional[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    if not runtime_globals:
        return []
    pages: List[Mapping[str, Any]] = []
    seen: set[str] = set()

    def add_page(p: Mapping[str, Any]) -> None:
        pid = str(p.get("id") or id(p))
        if pid not in seen:
            seen.add(pid)
            pages.append(p)

    for value in runtime_globals.values():
        if _looks_like_page(value):
            add_page(value)
        elif isinstance(value, list):
            for item in value:
                if _looks_like_page(item):
                    add_page(item)
        elif isinstance(value, dict):
            # Some query wrappers store pages under results/items/tasks.
            for key in ("results", "items", "tasks", "pages", "open_tasks"):
                inner = value.get(key)
                if isinstance(inner, list):
                    for item in inner:
                        if _looks_like_page(item):
                            add_page(item)
    return pages


def scan_pages(pages: Iterable[Mapping[str, Any]]) -> ReconciliationSummary:
    summary = ReconciliationSummary()

    for page in pages:
        props = page.get("properties", {}) if isinstance(page, Mapping) else {}
        if not isinstance(props, Mapping):
            continue
        summary.scanned += 1
        title = _task_title(page)

        done = _bool(_prop_value(props, ["Done", "Complete", "Completed"]))
        open_loop_raw = _prop_value(props, ["Open Loop", "Open", "Active"])
        open_loop = _bool(open_loop_raw) if open_loop_raw is not None else not done
        closed_or_done = done or (open_loop_raw is not None and not open_loop)
        jdi = _bool(_prop_value(props, ["JDI", "Just Do It", "Just Do It?", "Just Do It"] )) or bool(re.search(r"\b(jdi|just do it)\b", title, re.I))
        quick_win = _bool(_prop_value(props, ["Quick Win", "Quick Wins", "QuickWin"] ))
        best_next = _bool(_prop_value(props, ["Best Next Action", "Best Next", "BNA"] ))
        do_today = _bool(_prop_value(props, ["Do = Today", "Do Today", "Today"] ))
        focus_now = _bool(_prop_value(props, ["Focus Now", "Focus"] ))
        defer_prop = _prop_value(props, ["Defer Until", "Deferred Until", "Defer"] )
        defer_text = _date_text(defer_prop).strip()
        deferred_future = _is_future_date(defer_prop)
        exec_score = _number(_prop_value(props, ["Execution Score", "Score"] ))
        exec_rank = _number(_prop_value(props, ["Execution Rank", "Rank"] ))

        if done:
            summary.done_tasks += 1
        if closed_or_done:
            summary.closed_tasks += 1
        elif open_loop:
            summary.open_tasks += 1

        # Meaningful execution metadata excludes a default/present zero score.
        # Notion may preserve number properties as 0 even when there is no active
        # execution state to reconcile; flagging those created noisy diagnostics.
        has_meaningful_execution_score = exec_score is not None and exec_score != 0
        has_execution_metadata = any([
            has_meaningful_execution_score,
            exec_rank is not None,
            best_next,
            focus_now,
        ])
        has_presentation_metadata = any([quick_win, do_today, best_next, focus_now])

        surface_detail = _active_surface_details(
            quick_win=quick_win,
            best_next=best_next,
            do_today=do_today,
            focus_now=focus_now,
            exec_score=exec_score,
            exec_rank=exec_rank,
            defer_text=defer_text,
        )

        if done and has_presentation_metadata:
            summary.finding("done_presentation", "Done tasks with active presentation metadata").add(title, surface_detail)
        if done and has_execution_metadata:
            summary.finding("done_execution", "Done tasks with execution metadata").add(title, surface_detail)
        if closed_or_done and has_presentation_metadata:
            summary.finding("closed_presentation_preview", "Closed/done tasks with active presentation metadata").add(title, surface_detail)
        if closed_or_done and has_execution_metadata:
            summary.finding("closed_execution_preview", "Closed/done tasks with execution metadata").add(title, surface_detail)
            summary.finding(
                "would_clear_closed_execution_preview",
                "Would clear closed/done execution metadata",
            ).add(
                title,
                _closed_task_clear_preview_detail(
                    quick_win=False,
                    best_next=best_next,
                    do_today=False,
                    focus_now=focus_now,
                    exec_score=exec_score if exec_score != 0 else None,
                    exec_rank=exec_rank,
                ),
            )
        if closed_or_done and has_presentation_metadata:
            summary.finding(
                "would_clear_closed_presentation_preview",
                "Would clear closed/done presentation metadata",
            ).add(
                title,
                _closed_task_clear_preview_detail(
                    quick_win=quick_win,
                    best_next=False,
                    do_today=do_today,
                    focus_now=focus_now,
                    exec_score=None,
                    exec_rank=None,
                ),
            )
        if jdi and has_execution_metadata:
            summary.finding("jdi_execution", "JDI tasks with forbidden execution metadata").add(title, surface_detail)
        if deferred_future and has_presentation_metadata:
            summary.finding("deferred_surface", "Deferred future tasks still surfaced").add(title, surface_detail)
        if deferred_future and quick_win:
            summary.finding("would_clear_quick_win_deferred", "Would clear Quick Win").add(
                title,
                f"Reason: deferred until future date; {surface_detail}"
            )
        if best_next and exec_rank is None:
            summary.finding("bna_without_rank", "Best Next Action without Execution Rank").add(title, surface_detail)
        if best_next and exec_score is None:
            summary.finding("bna_without_score", "Best Next Action without Execution Score").add(title, surface_detail)
        if do_today and not best_next:
            summary.finding("today_without_bna", "Do = Today without Best Next Action").add(title, surface_detail)
        if focus_now:
            summary.finding("legacy_focus", "Legacy Focus/Focus Now metadata still present").add(title, surface_detail)
        if quick_win and done:
            summary.finding("done_quick_win", "Done tasks still marked Quick Win").add(title, surface_detail)

    return summary



def _prop_name_present(properties: Mapping[str, Any], candidates: Sequence[str]) -> Optional[str]:
    """Return the actual Notion property name present on this page."""
    lower_map = {str(k).strip().lower(): str(k) for k in properties.keys()}
    for name in candidates:
        if name in properties:
            return name
        actual = lower_map.get(name.strip().lower())
        if actual:
            return actual
    return None


def collect_quick_win_deferred_cleanup_actions(pages: Iterable[Mapping[str, Any]]) -> List[Dict[str, str]]:
    """Collect the exact pages eligible for Phase 1.4 mutation.

    Eligible means only: future Defer Until + Quick Win checked.
    """
    actions: List[Dict[str, str]] = []
    for page in pages:
        if not _looks_like_page(page):
            continue
        props = page.get("properties", {})
        if not isinstance(props, Mapping):
            continue
        quick_win_prop_name = _prop_name_present(props, ["Quick Win", "Quick Wins", "QuickWin"])
        if not quick_win_prop_name:
            continue
        quick_win = _bool(props.get(quick_win_prop_name))
        defer_prop = _prop_value(props, ["Defer Until", "Deferred Until", "Defer"])
        if quick_win and _is_future_date(defer_prop):
            actions.append({
                "page_id": str(page.get("id") or ""),
                "title": _task_title(page),
                "quick_win_property": quick_win_prop_name,
                "defer_until": _date_text(defer_prop).strip(),
            })
    return [a for a in actions if a["page_id"]]


def apply_quick_win_deferred_cleanup(actions: Sequence[Mapping[str, str]]) -> Tuple[int, List[str]]:
    """Apply the only Phase 1.4 mutation: Quick Win=false.

    Returns (updated_count, error_messages). This function is intentionally tiny and
    does not touch any other property.
    """
    if not actions:
        return 0, []

    token = os.getenv("NOTION_TOKEN", "").strip()
    if not token:
        return 0, ["NOTION_TOKEN missing; mutation skipped"]

    try:
        import requests  # type: ignore
    except Exception as exc:
        return 0, [f"requests import failed; mutation skipped: {exc}"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": os.getenv("NOTION_VERSION", "2022-06-28"),
        "Content-Type": "application/json",
    }
    updated = 0
    errors: List[str] = []
    for action in actions:
        page_id = action.get("page_id", "")
        prop_name = action.get("quick_win_property", "Quick Win")
        title = action.get("title", page_id)
        try:
            resp = requests.patch(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=headers,
                json={"properties": {prop_name: {"checkbox": False}}},
                timeout=20,
            )
            if 200 <= resp.status_code < 300:
                updated += 1
            else:
                errors.append(f"{title}: HTTP {resp.status_code} {resp.text[:220]}")
        except Exception as exc:
            errors.append(f"{title}: {exc}")
    return updated, errors


def collect_closed_execution_cleanup_actions(pages: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Collect pages eligible for Phase 1.8 closed/done execution cleanup.

    Eligible means:
    - Done is checked, OR Open Loop exists and is false
    - Execution Rank is present OR Execution Score is present and non-zero

    Default Execution Score=0 is ignored as Notion/property noise.
    """
    actions: List[Dict[str, Any]] = []
    for page in pages:
        if not _looks_like_page(page):
            continue
        props = page.get("properties", {})
        if not isinstance(props, Mapping):
            continue

        done = _bool(_prop_value(props, ["Done", "Complete", "Completed"]))
        open_loop_raw = _prop_value(props, ["Open Loop", "Open", "Active"])
        open_loop = _bool(open_loop_raw) if open_loop_raw is not None else not done
        closed_or_done = done or (open_loop_raw is not None and not open_loop)
        if not closed_or_done:
            continue

        exec_score_prop_name = _prop_name_present(props, ["Execution Score", "Score"])
        exec_rank_prop_name = _prop_name_present(props, ["Execution Rank", "Rank"])
        exec_score = _number(props.get(exec_score_prop_name)) if exec_score_prop_name else None
        exec_rank = _number(props.get(exec_rank_prop_name)) if exec_rank_prop_name else None

        properties_to_clear: Dict[str, Dict[str, Any]] = {}
        detail_parts: List[str] = []
        if exec_rank_prop_name and exec_rank is not None:
            properties_to_clear[exec_rank_prop_name] = {"number": None}
            detail_parts.append(f"Execution Rank={exec_rank:g}")
        if exec_score_prop_name and exec_score is not None and exec_score != 0:
            properties_to_clear[exec_score_prop_name] = {"number": None}
            detail_parts.append(f"Execution Score={exec_score:g}")

        if properties_to_clear:
            actions.append({
                "page_id": str(page.get("id") or ""),
                "title": _task_title(page),
                "properties": properties_to_clear,
                "detail": "; ".join(detail_parts),
            })
    return [a for a in actions if a["page_id"]]


def apply_closed_execution_cleanup(actions: Sequence[Mapping[str, Any]]) -> Tuple[int, List[str]]:
    """Apply Phase 1.8 mutation: clear Execution Score / Execution Rank on closed tasks."""
    if not actions:
        return 0, []

    token = os.getenv("NOTION_TOKEN", "").strip()
    if not token:
        return 0, ["NOTION_TOKEN missing; closed execution cleanup skipped"]

    try:
        import requests  # type: ignore
    except Exception as exc:
        return 0, [f"requests import failed; closed execution cleanup skipped: {exc}"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": os.getenv("NOTION_VERSION", "2022-06-28"),
        "Content-Type": "application/json",
    }
    updated = 0
    errors: List[str] = []
    for action in actions:
        page_id = str(action.get("page_id", ""))
        title = str(action.get("title") or page_id)
        properties = action.get("properties")
        if not page_id or not isinstance(properties, Mapping) or not properties:
            continue
        try:
            resp = requests.patch(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=headers,
                json={"properties": dict(properties)},
                timeout=20,
            )
            if 200 <= resp.status_code < 300:
                updated += 1
            else:
                errors.append(f"{title}: HTTP {resp.status_code} {resp.text[:220]}")
        except Exception as exc:
            errors.append(f"{title}: {exc}")
    return updated, errors


def format_summary(summary: ReconciliationSummary) -> List[str]:
    lines = []
    lines.append("=== METADATA RECONCILIATION — PHASE 1.8: CLOSED TASK EXECUTION CLEANUP + QUICK WIN CLEANUP ===")
    lines.append(f"[Metadata Reconciliation] Version: {VERSION}")
    lines.append(f"[Metadata Reconciliation] Tasks scanned: {summary.scanned}")
    lines.append(f"[Metadata Reconciliation] Open tasks observed: {summary.open_tasks}")
    lines.append(f"[Metadata Reconciliation] Done tasks observed: {summary.done_tasks}")
    lines.append(f"[Metadata Reconciliation] Closed/done tasks observed: {summary.closed_tasks}")

    if not summary.findings:
        lines.append("[Metadata Reconciliation] Findings: 0")
        lines.append("[Metadata Reconciliation] No metadata reconciliation issues observed in available runtime objects.")
        return lines

    total = sum(f.count for f in summary.findings.values())
    lines.append(f"[Metadata Reconciliation] Findings: {total}")
    for key in sorted(summary.findings):
        f = summary.findings[key]
        lines.append(f"[Metadata Reconciliation] {f.label}: {f.count}")
        for ex in f.examples:
            lines.append(f"[Metadata Reconciliation] Finding detail: {f.label} — {ex}")
    lines.append("[Metadata Reconciliation] Non-execution/presentation findings remain diagnostics only.")
    return lines


def emit_metadata_reconciliation_diagnostics(runtime_globals: Optional[Mapping[str, Any]] = None) -> ReconciliationSummary:
    """Scan available runtime task objects, print diagnostics, and apply one safe cleanup.

    Phase 1.8 behavior:
    - Clear meaningful closed/done Execution Score and Execution Rank metadata.
    - Ignore default Execution Score=0 noise.

    Phase 1.4 mutation boundary:
    - Clear Quick Win only when Defer Until is in the future.
    - Closed/done Execution Score and Execution Rank findings are now safely mutated.
    - No other properties are changed.
    """
    pages = _extract_pages_from_globals(runtime_globals)
    summary = scan_pages(pages)
    actions = collect_quick_win_deferred_cleanup_actions(pages)
    closed_actions = collect_closed_execution_cleanup_actions(pages)

    for line in format_summary(summary):
        print(line)

    if actions:
        print(f"[Metadata Reconciliation] Applying Quick Win deferred cleanup: {len(actions)}")
        for action in actions[:_MAX_EXAMPLES]:
            print(
                "[Metadata Reconciliation] Clearing Quick Win: "
                f"{action.get('title')} — Defer Until={action.get('defer_until')}"
            )
        updated, errors = apply_quick_win_deferred_cleanup(actions)
        print(f"[Metadata Reconciliation] Quick Win cleared: {updated}")
        if errors:
            print(f"[Metadata Reconciliation] Mutation errors: {len(errors)}")
            for err in errors[:_MAX_EXAMPLES]:
                print(f"[Metadata Reconciliation] Mutation error detail: {err}")
    else:
        print("[Metadata Reconciliation] Quick Win deferred cleanup: 0")

    if closed_actions:
        print(f"[Metadata Reconciliation] Applying closed/done execution cleanup: {len(closed_actions)}")
        for action in closed_actions[:_MAX_EXAMPLES]:
            print(
                "[Metadata Reconciliation] Clearing closed/done execution metadata: "
                f"{action.get('title')} — {action.get('detail')}"
            )
        updated, errors = apply_closed_execution_cleanup(closed_actions)
        print(f"[Metadata Reconciliation] Closed/done execution metadata cleared: {updated}")
        if errors:
            print(f"[Metadata Reconciliation] Closed/done mutation errors: {len(errors)}")
            for err in errors[:_MAX_EXAMPLES]:
                print(f"[Metadata Reconciliation] Closed/done mutation error detail: {err}")
    else:
        print("[Metadata Reconciliation] Closed/done execution cleanup: 0")

    return summary
