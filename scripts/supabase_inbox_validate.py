#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]

    repo_text = (
        root / "aios" / "storage" / "inbox_repository.py"
    ).read_text()
    source_text = (
        root / "aios" / "ingestion" / "supabase_source.py"
    ).read_text()
    sql_text = (
        root / "sql" / "001_create_inbox_items.sql"
    ).read_text()
    run_text = (
        root / "run_aios.py"
    ).read_text()

    checks = [
        (
            "InboxRepository follows SupabaseStore pattern",
            "class InboxRepository" in repo_text
            and "SupabaseStore" in repo_text
            and '.table("inbox_items")' in repo_text,
        ),
        (
            "SupabaseInboxSource exists",
            "class SupabaseInboxSource" in source_text,
        ),
        (
            "Supabase source returns InboxItem population",
            "list_pending_items" in source_text
            and "get_pending_items()" in source_text,
        ),
        (
            "Supabase lifecycle marks processed rather than deletes",
            "mark_processed(" in source_text
            and "delete_item(" not in source_text,
        ),
        (
            "schema creates inbox_items",
            "create table if not exists public.inbox_items"
            in sql_text,
        ),
        (
            "schema supports multiple sources",
            "source text not null" in sql_text
            and "source_metadata jsonb" in sql_text,
        ),
        (
            "schema supports durable lifecycle",
            "'pending', 'review', 'processed', 'archived'"
            in sql_text
            and "processed_at timestamptz" in sql_text,
        ),
        (
            "schema supports future review UI",
            "review_type text" in sql_text
            and "review_payload jsonb" in sql_text
            and "review_decision text" in sql_text,
        ),
        (
            "production runtime still uses Notion source",
            "NotionInboxSource(" in run_text
            and "SupabaseInboxSource(" not in run_text,
        ),
    ]

    ast.parse(repo_text)
    ast.parse(source_text)

    for label, ok in checks:
        print(
            f"{'PASS' if ok else 'FAIL'}: {label}"
        )

    if not all(ok for _, ok in checks):
        print(
            "\nRESULT: SUPABASE INBOX POC "
            "VALIDATION FAILED"
        )
        raise SystemExit(1)

    print(
        "\nRESULT: SUPABASE INBOX POC "
        "STRUCTURE VALID"
    )


if __name__ == "__main__":
    main()
