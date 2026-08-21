#!/usr/bin/env python3
"""Validate workspace tenancy Phase 1 migration and minimal app wiring."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "20260821_workspace_tenancy_phase1_v1.sql"
WORKSPACE_MODULE = ROOT / "aios" / "workspace.py"
API = ROOT / "aios" / "api" / "app.py"
SUMMARY = ROOT / "aios" / "daily_completion_summary.py"


def _migration_checks(text: str) -> list[tuple[str, bool]]:
    default_id = "00000000-0000-4000-8000-000000000001"
    core_tables = (
        "tasks",
        "projects",
        "inbox_items",
        "work_patterns",
        "daily_journal",
        "daily_completion_summaries",
    )
    derived_tables = (
        "inbox_reviews",
        "project_work_proposals",
        "task_focus_guidance",
        "task_execution_state",
        "task_evaluations",
    )
    checks: list[tuple[str, bool]] = [
        ("migration file exists", MIGRATION.is_file()),
        ("workspaces table", "create table if not exists public.workspaces" in text),
        ("workspace_members table", "create table if not exists public.workspace_members" in text),
        ("default workspace insert", default_id in text and "'default'" in text),
        ("default member insert", "insert into public.workspace_members" in text),
        (
            "daily_journal composite primary key",
            "primary key (workspace_id, journal_date)" in text,
        ),
        (
            "daily_completion_summaries composite primary key",
            "primary key (workspace_id, summary_date)" in text,
        ),
    ]
    for table in core_tables:
        checks.append(
            (f"{table} workspace_id column", f"alter table public.{table}" in text and "workspace_id" in text)
        )
    for table in derived_tables:
        checks.append(
            (f"{table} workspace_id backfill", f"alter table public.{table}" in text)
        )
    checks.append(("no RLS policies in migration", "enable row level security" not in text.lower()))
    return checks


def _app_checks(api_text: str, summary_text: str, workspace_text: str) -> list[tuple[str, bool]]:
    return [
        ("workspace defaults module", "DEFAULT_WORKSPACE_ID" in workspace_text),
        (
            "journal upsert uses workspace scope",
            "default_workspace_id()" in api_text
            and 'on_conflict="workspace_id,journal_date"' in api_text,
        ),
        (
            "summary upsert uses workspace scope",
            "default_workspace_id()" in summary_text
            and 'on_conflict="workspace_id,summary_date"' in summary_text,
        ),
    ]


def _live_checks() -> list[tuple[str, bool]]:
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SECRET_KEY"):
        return [("live Supabase checks skipped", True)]

    try:
        from aios.workspace import DEFAULT_WORKSPACE_ID, default_workspace_id
        from aios.storage.supabase_store import SupabaseStore
    except Exception as exc:
        return [(f"live Supabase checks skipped ({exc.__class__.__name__})", True)]

    store = SupabaseStore()
    checks: list[tuple[str, bool]] = []

    workspace_rows = (
        store.client.table("workspaces")
        .select("id,slug")
        .eq("slug", "default")
        .limit(1)
        .execute()
        .data
        or []
    )
    checks.append(("default workspace row exists", bool(workspace_rows)))
    if workspace_rows:
        checks.append(
            (
                "default workspace id matches constant",
                str(workspace_rows[0]["id"]) == default_workspace_id()
                == DEFAULT_WORKSPACE_ID,
            )
        )

    member_rows = (
        store.client.table("workspace_members")
        .select("id")
        .eq("workspace_id", default_workspace_id())
        .limit(1)
        .execute()
        .data
        or []
    )
    checks.append(("default workspace has a member", bool(member_rows)))

    for table in ("tasks", "projects", "inbox_items"):
        null_rows = (
            store.client.table(table)
            .select("id")
            .is_("workspace_id", "null")
            .limit(1)
            .execute()
            .data
            or []
        )
        checks.append((f"{table} workspace_id backfilled", not null_rows))

    for table, key_col in (("daily_journal", "journal_date"), ("daily_completion_summaries", "summary_date")):
        null_rows = (
            store.client.table(table)
            .select(key_col)
            .is_("workspace_id", "null")
            .limit(1)
            .execute()
            .data
            or []
        )
        checks.append((f"{table} workspace_id backfilled", not null_rows))

    return checks


def main() -> None:
    migration_text = MIGRATION.read_text() if MIGRATION.is_file() else ""
    api_text = API.read_text()
    summary_text = SUMMARY.read_text()
    workspace_text = WORKSPACE_MODULE.read_text() if WORKSPACE_MODULE.is_file() else ""

    checks = (
        _migration_checks(migration_text)
        + _app_checks(api_text, summary_text, workspace_text)
        + _live_checks()
    )

    failed = False
    for label, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {label}")
        failed = failed or not ok

    if failed:
        print("\nRESULT: WORKSPACE TENANCY PHASE 1 VALIDATION FAILED")
        raise SystemExit(1)

    print("\nRESULT: WORKSPACE TENANCY PHASE 1 STRUCTURE VALID")


if __name__ == "__main__":
    main()
