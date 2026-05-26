"""Read-only historical project affinity telemetry for AIOS.

D1 scope:
- observes historical/completed task/project affinity
- emits compact telemetry
- performs no Notion writes
- does not affect execution ranking, BNA, Quick Wins, or governance reconciliation
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "at", "with",
    "from", "by", "about", "into", "up", "out", "over", "under", "new", "old",
    "task", "tasks", "todo", "do", "make", "get", "set", "check", "review", "update",
    "create", "add", "fix", "clean", "prepare", "finish", "complete", "work", "next",
}

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'_-]{2,}")


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
    return [str(item.get("id")) for item in relation if isinstance(item, Mapping) and item.get("id")]


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


@dataclass(frozen=True)
class AffinitySummary:
    total_tasks: int
    historical_tasks: int
    project_groups: int
    unassigned_historical_tasks: int
    top_project_neighborhoods: List[Dict[str, Any]]
    top_global_terms: List[Tuple[str, int]]

    def telemetry_lines(self) -> List[str]:
        lines = [
            "=== PROJECT COGNITION — D1: HISTORICAL AFFINITY TELEMETRY ===",
            f"[Project Cognition] Historical tasks observed: {self.historical_tasks}/{self.total_tasks}",
            f"[Project Cognition] Project affinity groups: {self.project_groups}; unassigned_historical={self.unassigned_historical_tasks}",
        ]
        if self.top_global_terms:
            terms = ", ".join(f"{term}:{count}" for term, count in self.top_global_terms[:10])
            lines.append(f"[Project Cognition] Top historical terms: {terms}")
        for item in self.top_project_neighborhoods[:8]:
            terms = ", ".join(f"{term}:{count}" for term, count in item["terms"][:6])
            lines.append(
                "[Project Cognition] Neighborhood "
                f"{item['project_key']} — tasks={item['task_count']}; terms={terms}"
            )
        lines.append("[Project Cognition] D1 mode: read_only=true; writes=0; execution_authority_impact=none")
        return lines


def summarize_historical_affinity(
    tasks: Sequence[HistoricalTask],
    *,
    min_group_tasks: int = 2,
    top_terms: int = 10,
) -> AffinitySummary:
    """Build compact read-only affinity telemetry from historical task records."""
    historical = [task for task in tasks if task.done or task.archived]
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
            "task_count": len(project_tasks),
            "terms": term_counts.most_common(top_terms),
        })

    neighborhoods.sort(key=lambda item: (item["task_count"], len(item["terms"])), reverse=True)

    return AffinitySummary(
        total_tasks=len(tasks),
        historical_tasks=len(historical),
        project_groups=len(neighborhoods),
        unassigned_historical_tasks=len(grouped.get("unassigned", [])),
        top_project_neighborhoods=neighborhoods,
        top_global_terms=global_terms.most_common(top_terms),
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
