#!/usr/bin/env python3
"""Generate read-only historical project affinity telemetry from the AIOS Notion task DB.

D1.1 hardening:
- validates configured task database IDs before querying
- falls back to Notion database discovery when the configured ID is stale/inaccessible
- remains strictly read-only: no Notion writes, no project mutation, no execution authority impact
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

try:
    import requests
except Exception as exc:  # pragma: no cover
    print(f"Missing dependency: requests ({exc})", file=sys.stderr)
    sys.exit(2)

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

# Allow running from project root without package installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.project_cognition.historical_affinity import (  # noqa: E402
    summarize_historical_affinity,
    task_from_notion_page,
)


TASK_DB_ENV_NAMES = (
    "NOTION_TASKS_DATABASE_ID",
    "TASKS_DATABASE_ID",
    "NOTION_TASK_DATABASE_ID",
    "TASK_DATABASE_ID",
)


class NotionQueryError(RuntimeError):
    def __init__(self, status_code: int, message: str, response_text: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


def _env_first(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip().strip('"').strip("'")
    return ""


def notion_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": os.getenv("NOTION_VERSION", "2022-06-28"),
        "Content-Type": "application/json",
    }


def notion_get_database(token: str, database_id: str) -> Dict[str, Any]:
    url = f"https://api.notion.com/v1/databases/{database_id}"
    response = requests.get(url, headers=notion_headers(token), timeout=30)
    if response.status_code >= 400:
        raise NotionQueryError(
            response.status_code,
            f"Notion database lookup failed for {database_id}: {response.status_code} {response.text[:500]}",
            response.text[:500],
        )
    return response.json()


def notion_query_database(token: str, database_id: str, *, page_size: int = 100, max_pages: int = 10) -> List[Dict[str, Any]]:
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload: Dict[str, Any] = {"page_size": page_size}
    pages: List[Dict[str, Any]] = []

    for _ in range(max_pages):
        response = requests.post(url, headers=notion_headers(token), json=payload, timeout=30)
        if response.status_code >= 400:
            raise NotionQueryError(
                response.status_code,
                f"Notion query failed for {database_id}: {response.status_code} {response.text[:500]}",
                response.text[:500],
            )
        data = response.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")
    return pages


def _database_title(database: Mapping[str, Any]) -> str:
    title = database.get("title") or []
    parts = [item.get("plain_text", "") for item in title if isinstance(item, Mapping)]
    return "".join(parts).strip()


def _schema_score(database: Mapping[str, Any], *, title_property: str, done_property: str) -> Tuple[int, List[str]]:
    props = database.get("properties") or {}
    score = 0
    reasons: List[str] = []

    title_prop = props.get(title_property) or {}
    if title_prop.get("type") == "title":
        score += 5
        reasons.append(f"title_property={title_property}")

    done_prop = props.get(done_property) or {}
    if done_prop.get("type") == "checkbox":
        score += 3
        reasons.append(f"done_property={done_property}")

    for name in ("Project", "Parent Task", "Execution Rank", "Execution Score", "Best Next Action", "Quick Win"):
        if name in props:
            score += 1
            reasons.append(name)

    title = _database_title(database).lower()
    if "task" in title or "aios" in title:
        score += 1
        reasons.append("name_hint")

    return score, reasons


def discover_task_database(
    token: str,
    *,
    title_property: str,
    done_property: str,
    min_score: int = 8,
    max_pages: int = 4,
) -> Tuple[str, Dict[str, Any], List[str]]:
    """Discover an accessible Notion database that looks like the AIOS task DB.

    This is read-only and uses Notion search. It prevents D1 telemetry from failing
    when a local .env or shell variable points at an old/inaccessible task database.
    """
    candidates: List[Tuple[int, str, Dict[str, Any], List[str]]] = []
    payload: Dict[str, Any] = {
        "filter": {"value": "database", "property": "object"},
        "page_size": 100,
    }
    url = "https://api.notion.com/v1/search"

    for _ in range(max_pages):
        response = requests.post(url, headers=notion_headers(token), json=payload, timeout=30)
        if response.status_code >= 400:
            raise NotionQueryError(
                response.status_code,
                f"Notion database discovery failed: {response.status_code} {response.text[:500]}",
                response.text[:500],
            )
        data = response.json()
        for database in data.get("results", []):
            if database.get("object") != "database":
                continue
            score, reasons = _schema_score(database, title_property=title_property, done_property=done_property)
            if score >= min_score:
                candidates.append((score, str(database.get("id") or ""), database, reasons))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")

    if not candidates:
        raise RuntimeError(
            "Could not discover an accessible AIOS task database. "
            "Share the Tasks database with the Notion integration or pass --database-id."
        )

    candidates.sort(key=lambda item: item[0], reverse=True)
    score, database_id, database, reasons = candidates[0]
    return database_id, database, [f"score={score}", *reasons]


def resolve_database_id(
    token: str,
    configured_database_id: str,
    *,
    title_property: str,
    done_property: str,
    allow_discovery: bool,
) -> Tuple[str, List[str]]:
    notes: List[str] = []
    if configured_database_id:
        try:
            database = notion_get_database(token, configured_database_id)
            score, reasons = _schema_score(database, title_property=title_property, done_property=done_property)
            if score >= 5:
                notes.append(f"configured_database_valid=true; schema_score={score}; reasons={','.join(reasons)}")
                return configured_database_id, notes
            notes.append(
                f"configured_database_schema_warning=true; schema_score={score}; reasons={','.join(reasons) or 'none'}"
            )
            return configured_database_id, notes
        except NotionQueryError as exc:
            if not allow_discovery or exc.status_code != 404:
                raise
            notes.append("configured_database_accessible=false; falling_back_to_discovery=true")

    if not allow_discovery:
        raise RuntimeError("Missing or inaccessible task database id and discovery is disabled.")

    database_id, _database, reasons = discover_task_database(
        token,
        title_property=title_property,
        done_property=done_property,
    )
    notes.append(f"discovered_database_id={database_id}; {'; '.join(reasons)}")
    return database_id, notes


def main(argv: Optional[List[str]] = None) -> int:
    if load_dotenv:
        # Do not override shell variables; this preserves normal AIOS behavior.
        load_dotenv()

    parser = argparse.ArgumentParser(description="AIOS D1 historical project affinity telemetry")
    parser.add_argument("--database-id", default="", help="Notion tasks database ID. Defaults to env NOTION_TASKS_DATABASE_ID/TASKS_DATABASE_ID/NOTION_TASK_DATABASE_ID.")
    parser.add_argument("--max-pages", type=int, default=int(os.getenv("AIOS_PROJECT_AFFINITY_MAX_PAGES", "10")))
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--title-property", default=os.getenv("AIOS_TASK_TITLE_PROPERTY", "Task Name"))
    parser.add_argument("--done-property", default=os.getenv("AIOS_DONE_PROPERTY", "Done"))
    parser.add_argument("--project-property", default=os.getenv("AIOS_PROJECT_PROPERTY", "Project"))
    parser.add_argument("--suggested-project-property", default=os.getenv("AIOS_SUGGESTED_PROJECT_PROPERTY", "Suggested Project"))
    parser.add_argument("--no-discover", action="store_true", help="Disable fallback Notion database discovery.")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON summary instead of compact telemetry lines.")
    args = parser.parse_args(argv)

    token = _env_first("NOTION_TOKEN")
    configured_database_id = args.database_id or _env_first(*TASK_DB_ENV_NAMES)

    if not token:
        print("Missing NOTION_TOKEN in environment/.env", file=sys.stderr)
        return 2

    try:
        database_id, resolution_notes = resolve_database_id(
            token,
            configured_database_id,
            title_property=args.title_property,
            done_property=args.done_property,
            allow_discovery=not args.no_discover,
        )
        pages = notion_query_database(token, database_id, page_size=args.page_size, max_pages=args.max_pages)
    except Exception as exc:
        print(f"[Project Cognition] D1 database resolution/query failed: {exc}", file=sys.stderr)
        print("[Project Cognition] Hint: verify TASKS_DATABASE_ID or share the Tasks database with the Notion integration.", file=sys.stderr)
        return 1

    tasks = [
        task_from_notion_page(
            page,
            title_property=args.title_property,
            done_property=args.done_property,
            project_property=args.project_property,
            suggested_project_property=args.suggested_project_property,
        )
        for page in pages
    ]
    summary = summarize_historical_affinity(tasks)

    if args.json:
        print(json.dumps({
            "database_id": database_id,
            "database_resolution": resolution_notes,
            "total_tasks": summary.total_tasks,
            "historical_tasks": summary.historical_tasks,
            "project_groups": summary.project_groups,
            "unassigned_historical_tasks": summary.unassigned_historical_tasks,
            "top_project_neighborhoods": summary.top_project_neighborhoods,
            "top_global_terms": summary.top_global_terms,
            "read_only": True,
            "writes": 0,
        }, indent=2))
    else:
        for note in resolution_notes:
            print(f"[Project Cognition] Database resolution: {note}")
        print("\n".join(summary.telemetry_lines()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
