#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]

    model_text = (
        root / "aios" / "review" / "models.py"
    ).read_text()
    repo_text = (
        root / "aios" / "review" / "repository.py"
    ).read_text()
    sql_text = (
        root / "sql" / "003_create_inbox_reviews.sql"
    ).read_text()
    run_text = (
        root / "run_aios.py"
    ).read_text()

    checks = [
        (
            "InboxReview model exists",
            "class InboxReview" in model_text,
        ),
        (
            "review types are limited to current workflows",
            '"clarification"' in model_text
            and '"possible_duplicate"' in model_text,
        ),
        (
            "review states support clarification workflow",
            all(
                token in model_text
                for token in [
                    '"pending"',
                    '"awaiting_answer"',
                    '"pending_confirmation"',
                    '"resolved"',
                ]
            ),
        ),
        (
            "InboxReviewRepository exists",
            "class InboxReviewRepository" in repo_text,
        ),
        (
            "repository can create, transition, resolve, delete",
            all(
                token in repo_text
                for token in [
                    "def create_review(",
                    "def update_state(",
                    "def resolve_review(",
                    "def delete_review(",
                ]
            ),
        ),
        (
            "schema creates inbox_reviews",
            "create table if not exists public.inbox_reviews"
            in sql_text,
        ),
        (
            "schema references inbox_items",
            "references public.inbox_items(id)"
            in sql_text,
        ),
        (
            "schema uses json payload and decision",
            "payload jsonb" in sql_text
            and "decision jsonb" in sql_text,
        ),
        (
            "Supabase runtime owns possible-duplicate review",
            "upsert_possible_duplicate_review(match)" in run_text
            and 'AIOS_DATASTORE == "supabase"' in run_text,
        ),
    ]

    ast.parse(model_text)
    ast.parse(repo_text)

    for label, ok in checks:
        print(
            f"{'PASS' if ok else 'FAIL'}: {label}"
        )

    if not all(ok for _, ok in checks):
        print(
            "\nRESULT: SUPABASE INBOX REVIEW POC "
            "VALIDATION FAILED"
        )
        raise SystemExit(1)

    print(
        "\nRESULT: SUPABASE INBOX REVIEW POC "
        "STRUCTURE VALID"
    )


if __name__ == "__main__":
    main()
