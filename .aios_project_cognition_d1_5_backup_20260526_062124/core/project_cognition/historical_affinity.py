"""Read-only historical project affinity telemetry for AIOS.

D1 scope:
- observes historical/completed task/project affinity
- emits compact telemetry
- performs no Notion writes
- does not affect execution ranking, BNA, Quick Wins, or governance reconciliation

D1.3 adds display-name resolution for Project relation page IDs so telemetry can show
human-readable project neighborhoods instead of raw Notion relation IDs.

D1.4 adds read-only active-task affinity previews: current open tasks are compared
against historical neighborhoods and printed as candidate matches only. These previews
are observational telemetry and never mutate Notion.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import re
from typing import Any, Dict, List, Mapping, Sequence, Tuple


_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "at", "with",
    "from", "by", "about", "into", "up", "out", "over", "under", "new", "old",
    "task", "tasks", "todo", "do", "make", "get", "set", "check", "review", "update",
    "create", "add", "fix", "clean", "prepare", "finish", "complete", "work", "next",
}

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'_-]{2,}")


def normalize_notion_id(value: str) -> str:
    """Normalize Notion page/database IDs to dashed UUID format when possible."""
    raw = (value or "").strip().strip('"').strip("'")
    compact = raw.replace("-", "")
    if len(compact) == 32:
        return f"{compact[0:8]}-{compact[8:12]}-{compact[12:16]}-{compact[16:20]}-{compact[20:32]}"
    return raw


def tokenize_title(text: str) -> List[str]:
    """Tokenize task titles for lightweight operational-neighborhood analysis."""
    tokens = []
    for raw in _TOKEN_RE.findall(text or ""):
        token = raw.lower().strip("'_- ")
        if token and token not in _STOPWORDS and len(token) >= 3:
            tokens.append(token)
    return tokens


def notion_title_plain_text(prop: Mapping[str, Any]) -> str:
    items = prop.get("title") or []
    return "".join(part.get("plain_text", "") for part in items if isinstance(part, Mapping)).strip()


def notion_rich_text_plain_text(prop: Mapping[str, Any]) -> str:
    items = prop.get("rich_text") or []
    return "".join(part.get("plain_text", "") for part in items if isinstance(part, Mapping)).strip()


def notion_checkbox(prop: Mapping[str, Any]) -> bool:
    return bool(prop.get("checkbox"))


def notion_select_name(prop: Mapping[str, Any]) -> str:
    selected = prop.get("select") or {}
    return str(selected.get("name") or "").strip()


def notion_relation_ids(prop: Mapping[str, Any]) -> List[str]:
    relation = prop.get("relation") or []
    return [normalize_notion_id(str(item.get("id"))) for item in relation if isinstance(item, Mapping) and item.get("id")]


def notion_page_title(page: Mapping[str, Any]) -> str:
    """Extract the first title property from a Notion page, regardless of property name."""
    props = page.get("properties") or {}
    for prop in props.values():
        if isinstance(prop, Mapping) and prop.get("type") == "title":
            title = notion_title_plain_text(prop)
            if title:
                return title
    return ""


@dataclass(frozen=True)
class HistoricalTask:
    id: str
    title: str
    done: bool = False
    archived: bool = False
    project_ids: Tuple[str, ...] = ()
    suggested_project: str = ""

    @property
    def project_key(self) -> str:
        if self.project_ids:
            return "relation:" + ",".join(sorted(self.project_ids))
        if self.suggested_project:
            return "suggested:" + self.suggested_project.strip().lower()
        return "unassigned"

    @property
    def is_historical(self) -> bool:
        return self.done or self.archived

    @property
    def is_active(self) -> bool:
        return not self.done and not self.archived


@dataclass(frozen=True)
class AffinitySummary:
    total_tasks: int
    historical_tasks: int
    active_tasks: int
    project_groups: int
    unassigned_historical_tasks: int
    top_project_neighborhoods: List[Dict[str, Any]]
    top_global_terms: List[Tuple[str, int]]
    active_task_previews: List[Dict[str, Any]]

    def telemetry_lines(self) -> List[str]:
        lines = [
            "=== PROJECT COGNITION — D1.4: HISTORICAL AFFINITY TELEMETRY ===",
            f"[Project Cognition] Historical tasks observed: {self.historical_tasks}/{self.total_tasks}",
            f"[Project Cognition] Active tasks observed: {self.active_tasks}/{self.total_tasks}",
            f"[Project Cognition] Project affinity groups: {self.project_groups}; unassigned_historical={self.unassigned_historical_tasks}",
        ]
        if self.top_global_terms:
            terms = ", ".join(f"{term}:{count}" for term, count in self.top_global_terms[:10])
            lines.append(f"[Project Cognition] Top historical terms: {terms}")
        for item in self.top_project_neighborhoods[:8]:
            terms = ", ".join(f"{term}:{count}" for term, count in item["terms"][:6])
            label = item.get("project_label") or item.get("project_key") or "(unknown)"
            key = item.get("project_key", "")
            if key.startswith("relation:") and label != key:
                lines.append(
                    "[Project Cognition] Neighborhood Project: "
                    f"{label} — tasks={item['task_count']}; terms={terms}"
                )
            else:
                lines.append(
                    "[Project Cognition] Neighborhood "
                    f"{label} — tasks={item['task_count']}; terms={terms}"
                )

        if self.active_task_previews:
            lines.append(
                "[Project Cognition] Active affinity preview: "
                f"candidates={len(self.active_task_previews)}; read_only=true"
            )
            for item in self.active_task_previews[:8]:
                overlap = ", ".join(item.get("overlap_terms", [])[:5])
                lines.append(
                    "[Project Cognition] Active candidate: "
                    f"{item['task_title']} → {item['project_label']} "
                    f"(confidence={item['confidence']}; score={item['score']}; overlap={overlap})"
                )
        else:
            lines.append("[Project Cognition] Active affinity preview: candidates=0; read_only=true")

        lines.append("[Project Cognition] D1 mode: read_only=true; writes=0; execution_authority_impact=none")
        return lines


def project_key_label(project_key: str, project_name_by_id: Mapping[str, str] | None = None) -> str:
    """Return a human-readable project/neighborhood label for telemetry."""
    project_name_by_id = project_name_by_id or {}
    if project_key.startswith("relation:"):
        raw_ids = [normalize_notion_id(item) for item in project_key.removeprefix("relation:").split(",") if item]
        names = [project_name_by_id.get(pid, "").strip() for pid in raw_ids]
        names = [name for name in names if name]
        if names:
            return " + ".join(names)
        if raw_ids:
            return "unresolved_relation:" + ",".join(raw_ids)
    if project_key.startswith("suggested:"):
        return "suggested:" + project_key.removeprefix("suggested:")
    return project_key


def _confidence_for_score(score: int) -> str:
    if score >= 10:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


def build_active_task_previews(
    tasks: Sequence[HistoricalTask],
    neighborhoods: Sequence[Mapping[str, Any]],
    *,
    min_score: int = 3,
    max_candidates: int = 12,
) -> List[Dict[str, Any]]:
    """Compare active tasks to historical neighborhoods and return read-only preview candidates."""
    previews: List[Dict[str, Any]] = []
    active_tasks = [task for task in tasks if task.is_active and task.title]

    for task in active_tasks:
        task_tokens = Counter(tokenize_title(task.title))
        if not task_tokens:
            continue

        best: Dict[str, Any] | None = None
        for neighborhood in neighborhoods:
            term_counts = dict(neighborhood.get("terms") or [])
            if not term_counts:
                continue
            overlap_terms = [term for term in task_tokens if term in term_counts]
            if not overlap_terms:
                continue
            # Weight matches by historical strength but cap each term so one dominant token
            # does not completely overwhelm a multi-term operational signal.
            score = sum(min(int(term_counts.get(term, 0)), 5) * int(task_tokens[term]) for term in overlap_terms)
            if score < min_score:
                continue
            candidate = {
                "task_id": task.id,
                "task_title": task.title,
                "project_key": neighborhood.get("project_key", ""),
                "project_label": neighborhood.get("project_label") or neighborhood.get("project_key") or "(unknown)",
                "score": score,
                "confidence": _confidence_for_score(score),
                "overlap_terms": sorted(overlap_terms, key=lambda term: term_counts.get(term, 0), reverse=True),
            }
            if best is None or candidate["score"] > best["score"]:
                best = candidate

        if best is not None:
            previews.append(best)

    previews.sort(key=lambda item: (item["score"], item["task_title"].lower()), reverse=True)
    return previews[:max_candidates]


def summarize_historical_affinity(
    tasks: Sequence[HistoricalTask],
    *,
    min_group_tasks: int = 2,
    top_terms: int = 10,
    project_name_by_id: Mapping[str, str] | None = None,
    include_active_preview: bool = True,
    active_preview_min_score: int = 3,
    active_preview_limit: int = 12,
) -> AffinitySummary:
    """Build compact read-only affinity telemetry from historical task records."""
    historical = [task for task in tasks if task.is_historical]
    active = [task for task in tasks if task.is_active]
    grouped: Dict[str, List[HistoricalTask]] = defaultdict(list)
    global_terms: Counter[str] = Counter()

    for task in historical:
        grouped[task.project_key].append(task)
        global_terms.update(tokenize_title(task.title))

    neighborhoods: List[Dict[str, Any]] = []
    for project_key, project_tasks in grouped.items():
        if project_key == "unassigned" or len(project_tasks) < min_group_tasks:
            continue
        term_counts: Counter[str] = Counter()
        for task in project_tasks:
            term_counts.update(tokenize_title(task.title))
        neighborhoods.append({
            "project_key": project_key,
            "project_label": project_key_label(project_key, project_name_by_id),
            "task_count": len(project_tasks),
            "terms": term_counts.most_common(top_terms),
        })

    neighborhoods.sort(key=lambda item: (item["task_count"], len(item["terms"])), reverse=True)
    active_previews = []
    if include_active_preview:
        active_previews = build_active_task_previews(
            tasks,
            neighborhoods,
            min_score=active_preview_min_score,
            max_candidates=active_preview_limit,
        )

    return AffinitySummary(
        total_tasks=len(tasks),
        historical_tasks=len(historical),
        active_tasks=len(active),
        project_groups=len(neighborhoods),
        unassigned_historical_tasks=len(grouped.get("unassigned", [])),
        top_project_neighborhoods=neighborhoods,
        top_global_terms=global_terms.most_common(top_terms),
        active_task_previews=active_previews,
    )


def task_from_notion_page(
    page: Mapping[str, Any],
    *,
    title_property: str = "Task Name",
    done_property: str = "Done",
    project_property: str = "Project",
    suggested_project_property: str = "Suggested Project",
) -> HistoricalTask:
    props = page.get("properties") or {}
    title_prop = props.get(title_property) or {}
    title = notion_title_plain_text(title_prop)
    if not title:
        title = notion_page_title(page)
    done = notion_checkbox(props.get(done_property) or {})
    archived = bool(page.get("archived"))
    project_ids = tuple(notion_relation_ids(props.get(project_property) or {}))
    suggested = ""
    suggested_prop = props.get(suggested_project_property) or {}
    ptype = suggested_prop.get("type")
    if ptype == "rich_text":
        suggested = notion_rich_text_plain_text(suggested_prop)
    elif ptype == "select":
        suggested = notion_select_name(suggested_prop)
    return HistoricalTask(
        id=str(page.get("id") or ""),
        title=title,
        done=done,
        archived=archived,
        project_ids=project_ids,
        suggested_project=suggested,
    )
