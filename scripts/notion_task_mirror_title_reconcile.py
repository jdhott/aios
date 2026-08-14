#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import requests
from dotenv import find_dotenv, load_dotenv

from aios.storage.notion_task_mirror_writer import NotionTaskMirrorTitleWriter
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


NOTION_VERSION = "2022-06-28"


def load_env():
    load_dotenv(find_dotenv() or ".env", override=True)
    token = os.getenv("NOTION_TOKEN", "").strip()
    task_db = os.getenv("TASKS_DATABASE_ID", "").strip()

    if not token:
        raise RuntimeError("NOTION_TOKEN is not configured.")
    if not task_db:
        raise RuntimeError("TASKS_DATABASE_ID is not configured.")

    return (
        {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
        task_db,
    )


def get_title(page):
    prop = (page.get("properties") or {}).get("Task Name") or {}
    if prop.get("type") != "title":
        return ""
    return "".join(
        item.get("plain_text", "")
        for item in prop.get("title", [])
    ).strip()


def query_clarify_mirrors(headers, task_db):
    url = f"https://api.notion.com/v1/databases/{task_db}/query"
    base_payload = {
        "page_size": 100,
        "filter": {
            "property": "Task Name",
            "title": {"starts_with": "Clarify next action:"},
        },
    }

    results = []
    cursor = None

    while True:
        payload = dict(base_payload)
        if cursor:
            payload["start_cursor"] = cursor

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30,
        )
        if not response.ok:
            raise RuntimeError(
                "Notion clarify-title query failed: "
                f"HTTP {response.status_code} {response.text[:500]}"
            )

        data = response.json()
        results.extend(data.get("results") or [])

        if not data.get("has_more"):
            return results

        cursor = data.get("next_cursor")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    headers, task_db = load_env()
    repo = TaskRepository(SupabaseStore())

    by_legacy_id = {
        str(task.legacy_notion_id): task
        for task in repo.get_all_tasks()
        if getattr(task, "legacy_notion_id", None)
    }

    pages = query_clarify_mirrors(headers, task_db)

    candidates = []
    preserved = []
    unmapped = []

    for page in pages:
        page_id = str(page.get("id") or "")
        notion_title = get_title(page)
        task = by_legacy_id.get(page_id)

        if task is None:
            unmapped.append((page_id, notion_title))
            continue

        supabase_title = str(getattr(task, "title", "") or "").strip()

        if not supabase_title:
            unmapped.append((page_id, notion_title))
            continue

        if supabase_title.lower().startswith("clarify next action:"):
            preserved.append((page_id, notion_title, supabase_title))
            continue

        if supabase_title != notion_title:
            candidates.append((page_id, notion_title, supabase_title))

    print(
        "=== NOTION TASK MIRROR TITLE RECONCILIATION — "
        + ("APPLY" if args.apply else "DRY RUN")
        + " ==="
    )
    print("Clarify-titled Notion mirrors:", len(pages))
    print("Resolved-title candidates:", len(candidates))
    print("Still legitimately Clarify in Supabase:", len(preserved))
    print("Unmapped / unsafe:", len(unmapped))

    if candidates:
        print()
        print("WILL UPDATE:" if args.apply else "WOULD UPDATE:")
        for page_id, old, new in candidates:
            print(f"- {old}")
            print(f"  → {new}")
            print(f"  page={page_id}")

    if preserved:
        print()
        print("PRESERVED ACTIVE CLARIFY MIRRORS:")
        for page_id, old, _ in preserved:
            print(f"- {old} [{page_id}]")

    if unmapped:
        print()
        print("UNMAPPED / NOT TOUCHED:")
        for page_id, old in unmapped:
            print(f"- {old} [{page_id}]")

    if not args.apply:
        print()
        print("Dry run only. No Notion titles were changed.")
        return

    writer = NotionTaskMirrorTitleWriter(headers=headers)

    updated = 0
    failed = 0

    for page_id, old, new in candidates:
        try:
            writer.update_title(
                notion_page_id=page_id,
                authoritative_title=new,
            )
            updated += 1
        except Exception as exc:
            failed += 1
            print(f"FAILED: {old} → {new}: {exc}")

    print()
    print(f"Reconciliation complete. Updated: {updated}, Failed: {failed}")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
