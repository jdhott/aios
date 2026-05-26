#!/usr/bin/env python3
"""Generate read-only historical project affinity telemetry from the AIOS Notion task DB.

D1.2 scope:
- read-only project cognition telemetry
- validates TASKS_DATABASE_ID before querying
- can discover accessible Notion databases by schema/title when config is stale
- performs no Notion writes
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

try:
    import requests
except Exception as exc:  # pragma: no cover
    print(f"Missing dependency: requests ({exc})", file=sys.stderr)
    sys.exit(2)

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.project_cognition.historical_affinity import (  # noqa: E402
    summarize_historical_affinity,
    task_from_notion_page,
)

NOTION_VERSION = os.getenv("NOTION_VERSION", "2022-06-28")


def _env_first(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip().strip('"').strip("'")
    return ""


def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def normalize_notion_id(value: str) -> str:
    """Normalize Notion UUID-ish IDs while preserving already-valid IDs."""
    raw = (value or "").strip().strip('"').strip("'")
    compact = raw.replace("-", "")
    if len(compact) == 32:
        return f"{compact[0:8]}-{compact[8:12]}-{compact[12:16]}-{compact[16:20]}-{compact[20:32]}"
    return raw


def notion_get_database(token: str, database_id: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    database_id = normalize_notion_id(database_id)
    url = f"https://api.notion.com/v1/databases/{database_id}"
    response = requests.get(url, headers=_headers(token), timeout=30)
    if response.status_code >= 400:
        return False, None, f"{response.status_code} {response.text[:300]}"
    return True, response.json(), ""


def database_title(db: Mapping[str, Any]) -> str:
    title = db.get("title") or []
    return "".join(part.get("plain_text", "") for part in title if isinstance(part, Mapping)).strip()


def database_schema_score(db: Mapping[str, Any]) -> int:
    props = db.get("properties") or {}
    prop_names = set(props.keys())
    score = 0
    # AIOS task DB schema signals. Keep this generic enough for renamed DBs.
    if "Task Name" in prop_names:
        score += 6
    if "Done" in prop_names:
        score += 4
    if "Open Loop" in prop_names:
        score += 3
    if "Best Next Action" in prop_names:
        score += 3
    if "Execution Rank" in prop_names:
        score += 3
    if "Execution Score" in prop_names:
        score += 3
    if "Suggested Project" in prop_names:
        score += 2
    if "Project" in prop_names or "Parent Task" in prop_names:
        score += 2
    # Penalize known non-task telemetry/log schemas.
    if "Log Type" in prop_names or "AI Response" in prop_names:
        score -= 4
    if "Run ID" in prop_names or "Topology" in prop_names:
        score -= 4
    return score


def notion_search_databases(token: str, *, query: str = "", page_size: int = 100, max_pages: int = 3) -> List[Dict[str, Any]]:
    url = "https://api.notion.com/v1/search"
    payload: Dict[str, Any] = {
        "filter": {"value": "database", "property": "object"},
        "page_size": page_size,
    }
    if query:
        payload["query"] = query
    results: List[Dict[str, Any]] = []
    for _ in range(max_pages):
        response = requests.post(url, headers=_headers(token), json=payload, timeout=30)
        if response.status_code >= 400:
            raise RuntimeError(f"Notion database search failed: {response.status_code} {response.text[:500]}")
        data = response.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")
    return results


def discover_task_database(token: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Find the accessible database that looks most like the AIOS Tasks DB."""
    seen: Dict[str, Dict[str, Any]] = {}
    for query in ("Tasks", "Task", "AIOS", ""):
        for db in notion_search_databases(token, query=query):
            dbid = normalize_notion_id(str(db.get("id") or ""))
            if dbid:
                seen[dbid] = db

    scored: List[Dict[str, Any]] = []
    for dbid, db in seen.items():
        score = database_schema_score(db)
        scored.append({
            "id": dbid,
            "title": database_title(db),
            "score": score,
            "properties": sorted((db.get("properties") or {}).keys()),
        })
    scored.sort(key=lambda item: item["score"], reverse=True)

    candidates = [item for item in scored if item["score"] >= 8]
    if candidates:
        return candidates[0]["id"], scored
    return "", scored


def notion_query_database(token: str, database_id: str, *, page_size: int = 100, max_pages: int = 10) -> List[Dict[str, Any]]:
    database_id = normalize_notion_id(database_id)
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload: Dict[str, Any] = {"page_size": page_size}
    pages: List[Dict[str, Any]] = []

    for _ in range(max_pages):
        response = requests.post(url, headers=_headers(token), json=payload, timeout=30)
        if response.status_code >= 400:
            raise RuntimeError(f"Notion query failed: {response.status_code} {response.text[:500]}")
        data = response.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")
    return pages


def print_database_candidates(candidates: List[Dict[str, Any]]) -> None:
    if not candidates:
        print("[Project Cognition] Accessible databases discovered: 0")
        return
    print(f"[Project Cognition] Accessible databases discovered: {len(candidates)}")
    for item in candidates[:12]:
        props = ", ".join(item.get("properties", [])[:10])
        print(f"- score={item['score']:>2} title={item['title'] or '(untitled)'} id={item['id']} props={props}")


def resolve_database_id(token: str, configured_id: str, *, allow_discovery: bool, print_candidates: bool = False) -> str:
    if configured_id:
        normalized = normalize_notion_id(configured_id)
        ok, db, error = notion_get_database(token, normalized)
        if ok:
            score = database_schema_score(db or {})
            title = database_title(db or {})
            if score >= 8:
                print(f"[Project Cognition] Using configured task database: {title or normalized} ({normalized})")
                return normalized
            print(
                "[Project Cognition] Configured TASKS_DATABASE_ID is accessible but does not look like the AIOS Tasks DB "
                f"(score={score}, title={title or '(untitled)'})."
            )
        else:
            print(f"[Project Cognition] Configured TASKS_DATABASE_ID is not accessible: {normalized}")
            print(f"[Project Cognition] Notion response: {error}")

    if allow_discovery:
        discovered_id, candidates = discover_task_database(token)
        if print_candidates or not discovered_id:
            print_database_candidates(candidates)
        if discovered_id:
            match = next((c for c in candidates if c["id"] == discovered_id), {})
            print(f"[Project Cognition] Using discovered task database: {match.get('title') or discovered_id} ({discovered_id})")
            return discovered_id

    raise RuntimeError(
        "Could not resolve an accessible AIOS task database. "
        "The most likely cause is that TASKS_DATABASE_ID points to an old/unshared database. "
        "Share the real Tasks database with the Notion integration, update TASKS_DATABASE_ID in .env, "
        "or rerun with --database-id <current_tasks_database_id>."
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="AIOS D1 historical project affinity telemetry")
    parser.add_argument("--database-id", default="", help="Notion Tasks database ID. Overrides env TASKS_DATABASE_ID/NOTION_TASKS_DATABASE_ID.")
    parser.add_argument("--max-pages", type=int, default=int(os.getenv("AIOS_PROJECT_AFFINITY_MAX_PAGES", "10")))
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--title-property", default=os.getenv("AIOS_TASK_TITLE_PROPERTY", "Task Name"))
    parser.add_argument("--done-property", default=os.getenv("AIOS_DONE_PROPERTY", "Done"))
    parser.add_argument("--project-property", default=os.getenv("AIOS_PROJECT_PROPERTY", "Project"))
    parser.add_argument("--suggested-project-property", default=os.getenv("AIOS_SUGGESTED_PROJECT_PROPERTY", "Suggested Project"))
    parser.add_argument("--json", action="store_true", help="Emit raw JSON summary instead of compact telemetry lines.")
    parser.add_argument("--no-discovery", action="store_true", help="Disable Notion database search fallback.")
    parser.add_argument("--list-databases", action="store_true", help="List accessible databases and schema scores, then exit.")
    args = parser.parse_args(argv)

    if load_dotenv:
        load_dotenv()

    token = _env_first("NOTION_TOKEN")
    if not token:
        print("Missing NOTION_TOKEN in environment/.env", file=sys.stderr)
        return 2

    if args.list_databases:
        _, candidates = discover_task_database(token)
        print_database_candidates(candidates)
        return 0

    configured_id = args.database_id or _env_first("TASKS_DATABASE_ID", "NOTION_TASKS_DATABASE_ID", "NOTION_TASK_DATABASE_ID")

    try:
        database_id = resolve_database_id(token, configured_id, allow_discovery=not args.no_discovery)
        pages = notion_query_database(token, database_id, page_size=args.page_size, max_pages=args.max_pages)
    except Exception as exc:
        print(f"[Project Cognition] D1 database resolution/query failed: {exc}", file=sys.stderr)
        print("[Project Cognition] Useful diagnostic command:", file=sys.stderr)
        print("  ./venv/bin/python scripts/aios_project_affinity_report.py --list-databases", file=sys.stderr)
        return 2

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
            "total_tasks": summary.total_tasks,
            "historical_tasks": summary.historical_tasks,
            "project_groups": summary.project_groups,
            "unassigned_historical_tasks": summary.unassigned_historical_tasks,
            "top_project_neighborhoods": summary.top_project_neighborhoods,
            "top_global_terms": summary.top_global_terms,
            "database_id": database_id,
            "read_only": True,
            "writes": 0,
        }, indent=2))
    else:
        print("\n".join(summary.telemetry_lines()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
