#!/usr/bin/env python3
"""Generate read-only historical project affinity telemetry from the AIOS Notion task DB.

This script is intentionally observational. It does not update Notion.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

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


def _env_first(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return ""


def notion_query_database(token: str, database_id: str, *, page_size: int = 100, max_pages: int = 10) -> List[Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": os.getenv("NOTION_VERSION", "2022-06-28"),
        "Content-Type": "application/json",
    }
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload: Dict[str, Any] = {"page_size": page_size}
    pages: List[Dict[str, Any]] = []

    for _ in range(max_pages):
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code >= 400:
            raise RuntimeError(f"Notion query failed: {response.status_code} {response.text[:500]}")
        data = response.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")
    return pages


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="AIOS D1 historical project affinity telemetry")
    parser.add_argument("--database-id", default="", help="Notion tasks database ID. Defaults to env NOTION_TASKS_DATABASE_ID/TASKS_DATABASE_ID/NOTION_TASK_DATABASE_ID.")
    parser.add_argument("--max-pages", type=int, default=int(os.getenv("AIOS_PROJECT_AFFINITY_MAX_PAGES", "10")))
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--title-property", default=os.getenv("AIOS_TASK_TITLE_PROPERTY", "Task Name"))
    parser.add_argument("--done-property", default=os.getenv("AIOS_DONE_PROPERTY", "Done"))
    parser.add_argument("--project-property", default=os.getenv("AIOS_PROJECT_PROPERTY", "Project"))
    parser.add_argument("--suggested-project-property", default=os.getenv("AIOS_SUGGESTED_PROJECT_PROPERTY", "Suggested Project"))
    parser.add_argument("--json", action="store_true", help="Emit raw JSON summary instead of compact telemetry lines.")
    args = parser.parse_args(argv)

    if load_dotenv:
        load_dotenv()

    token = _env_first("NOTION_TOKEN")
    database_id = args.database_id or _env_first("NOTION_TASKS_DATABASE_ID", "TASKS_DATABASE_ID", "NOTION_TASK_DATABASE_ID")

    if not token:
        print("Missing NOTION_TOKEN in environment/.env", file=sys.stderr)
        return 2
    if not database_id:
        print("Missing tasks database id. Set NOTION_TASKS_DATABASE_ID or pass --database-id.", file=sys.stderr)
        return 2

    pages = notion_query_database(token, database_id, page_size=args.page_size, max_pages=args.max_pages)
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
            "read_only": True,
            "writes": 0,
        }, indent=2))
    else:
        print("\n".join(summary.telemetry_lines()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
