"""
Bootstrap current AIOS execution state from Notion into Supabase.

Default mode is DRY RUN.

Dry run:
    python -m scripts.supabase_execution_state_bootstrap

Write:
    python -m scripts.supabase_execution_state_bootstrap --write

The bootstrap only preserves CURRENT execution state:

- ranked tasks (Execution Rank is populated)
- surfaced Quick Wins (Surfaced Quick Win = true)

Best Next Action is derived from:
    execution_rank <= 5

Historical/stale Execution Score values on unranked tasks are intentionally
not migrated into task_execution_state.
"""

from __future__ import annotations

import argparse
from typing import Any, Optional

from aios.storage.execution_repository import ExecutionRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository

from scripts.supabase_poc_import import (
    TASKS_DATABASE_ID,
    query_database,
)


# ---------------------------------------------------------------------------
# Notion helpers
# ---------------------------------------------------------------------------

def notion_number(
    properties: dict[str, Any],
    name: str,
) -> Optional[int | float]:
    prop = properties.get(name, {})

    if prop.get("type") != "number":
        return None

    return prop.get("number")


def notion_checkbox(
    properties: dict[str, Any],
    name: str,
) -> bool:
    prop = properties.get(name, {})

    if prop.get("type") != "checkbox":
        return False

    return prop.get("checkbox") is True


def notion_title(
    page: dict[str, Any],
) -> str:
    prop = (
        page.get("properties", {})
        .get("Task Name", {})
    )

    values = prop.get("title", [])

    text = "".join(
        item.get("plain_text", "")
        for item in values
    ).strip()

    return text or "(Untitled Task)"


# ---------------------------------------------------------------------------
# Source loading
# ---------------------------------------------------------------------------

def load_notion_non_done_tasks() -> list[dict[str, Any]]:
    print(
        "\nReading current non-done task "
        "population from Notion..."
    )

    pages = query_database(
        TASKS_DATABASE_ID
    )

    non_done = []

    for page in pages:
        properties = page.get(
            "properties",
            {},
        )

        if notion_checkbox(
            properties,
            "Done",
        ):
            continue

        non_done.append(page)

    print(
        f"Total Notion tasks read: "
        f"{len(pages)}"
    )

    print(
        f"Non-done Notion tasks:   "
        f"{len(non_done)}"
    )

    return non_done


# ---------------------------------------------------------------------------
# Supabase task mapping
# ---------------------------------------------------------------------------

def build_task_map(
    repository: TaskRepository,
) -> dict[str, str]:
    """
    Notion task ID -> Supabase UUID
    """

    print(
        "\nLoading task mappings from Supabase..."
    )

    tasks = repository.get_all_tasks()

    mapping = {
        task.legacy_notion_id: task.id
        for task in tasks
        if task.legacy_notion_id
    }

    print(
        f"Supabase tasks read:     "
        f"{len(tasks)}"
    )

    print(
        f"Legacy ID mappings:      "
        f"{len(mapping)}"
    )

    return mapping


# ---------------------------------------------------------------------------
# Current-state extraction
# ---------------------------------------------------------------------------

def build_current_state_rows(
    notion_pages: list[dict[str, Any]],
    task_map: dict[str, str],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """
    Build only CURRENT execution-state rows.

    A row is created if:
    - Execution Rank is populated, OR
    - Surfaced Quick Win is true
    """

    rows = []
    missing_mappings = []

    for page in notion_pages:
        notion_id = page.get("id")

        if not notion_id:
            continue

        properties = page.get(
            "properties",
            {},
        )

        execution_rank = notion_number(
            properties,
            "Execution Rank",
        )

        execution_score = notion_number(
            properties,
            "Execution Score",
        )

        surfaced_quick_win = notion_checkbox(
            properties,
            "Surfaced Quick Win",
        )

        # Ignore stale historical score-only state.
        if (
            execution_rank is None
            and not surfaced_quick_win
        ):
            continue

        supabase_task_id = task_map.get(
            notion_id
        )

        if not supabase_task_id:
            missing_mappings.append({
                "notion_id": notion_id,
                "title": notion_title(page),
            })
            continue

        best_next_action = (
            execution_rank is not None
            and execution_rank <= 5
        )

        rows.append({
            "task_id": supabase_task_id,
            "execution_score": (
                execution_score
                if execution_rank is not None
                else None
            ),
            "execution_rank": execution_rank,
            "best_next_action": best_next_action,
            "surfaced_quick_win": surfaced_quick_win,
            "_title": notion_title(page),
        })

    return rows, missing_mappings


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_summary(
    rows: list[dict[str, Any]],
    missing_mappings: list[dict[str, Any]],
) -> None:

    ranked = [
        row
        for row in rows
        if row["execution_rank"] is not None
    ]

    bna = [
        row
        for row in rows
        if row["best_next_action"]
    ]

    surfaced = [
        row
        for row in rows
        if row["surfaced_quick_win"]
    ]

    print(
        "\n"
        + "=" * 72
    )

    print(
        "EXECUTION STATE BOOTSTRAP SUMMARY"
    )

    print(
        "=" * 72
    )

    print(
        f"Current state rows:        "
        f"{len(rows)}"
    )

    print(
        f"Ranked execution rows:     "
        f"{len(ranked)}"
    )

    print(
        f"Best Next Actions:         "
        f"{len(bna)}"
    )

    print(
        f"Surfaced Quick Wins:       "
        f"{len(surfaced)}"
    )

    print(
        f"Missing task mappings:     "
        f"{len(missing_mappings)}"
    )

    print(
        "\nCurrent ranked tasks:"
    )

    for row in sorted(
        ranked,
        key=lambda item: item["execution_rank"],
    ):
        print(
            f"  rank={row['execution_rank']} "
            f"score={row['execution_score']} "
            f"bna={row['best_next_action']} "
            f"title={row['_title']}"
        )

    print(
        "\nCurrent Surfaced Quick Wins:"
    )

    for row in surfaced:
        print(
            f"  - {row['_title']}"
        )

    if missing_mappings:
        print(
            "\nMissing mappings:"
        )

        for item in missing_mappings:
            print(
                f"  - {item['title']} "
                f"({item['notion_id']})"
            )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def normalized_state(
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    Normalize proposed bootstrap rows for parity comparison.
    """

    return {
        row["task_id"]: {
            "execution_score":
                row.get("execution_score"),

            "execution_rank":
                row.get("execution_rank"),

            "best_next_action":
                bool(
                    row.get(
                        "best_next_action",
                        False,
                    )
                ),

            "surfaced_quick_win":
                bool(
                    row.get(
                        "surfaced_quick_win",
                        False,
                    )
                ),
        }
        for row in rows
    }


def normalized_repository_state(
    state: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        task_id: {
            "execution_score":
                row.get("execution_score"),

            "execution_rank":
                row.get("execution_rank"),

            "best_next_action":
                bool(
                    row.get(
                        "best_next_action",
                        False,
                    )
                ),

            "surfaced_quick_win":
                bool(
                    row.get(
                        "surfaced_quick_win",
                        False,
                    )
                ),
        }
        for task_id, row in state.items()
    }


def validate_proposed_state(
    rows: list[dict[str, Any]],
    missing_mappings: list[dict[str, Any]],
) -> None:

    if missing_mappings:
        raise RuntimeError(
            "Bootstrap cannot continue: "
            "one or more current-state tasks "
            "could not be mapped."
        )

    ranked = [
        row
        for row in rows
        if row["execution_rank"] is not None
    ]

    ranks = sorted(
        int(row["execution_rank"])
        for row in ranked
    )

    if ranks != list(
        range(
            1,
            len(ranked) + 1,
        )
    ):
        raise RuntimeError(
            "Current execution ranks are not "
            f"canonical: {ranks}"
        )

    bna_count = sum(
        1
        for row in rows
        if row["best_next_action"]
    )

    expected_bna_count = min(
        5,
        len(ranked),
    )

    if bna_count != expected_bna_count:
        raise RuntimeError(
            "Unexpected BNA count: "
            f"{bna_count}, expected "
            f"{expected_bna_count}"
        )


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def write_bootstrap(
    repository: ExecutionRepository,
    rows: list[dict[str, Any]],
) -> None:

    print(
        "\nWriting current execution state "
        "to Supabase..."
    )

    # Remove reporting-only title field.
    write_rows = [
        {
            key: value
            for key, value in row.items()
            if not key.startswith("_")
        }
        for row in rows
    ]

    repository.upsert_current_state(
        write_rows
    )

    print(
        f"Rows written/upserted: "
        f"{len(write_rows)}"
    )


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

def reconcile_written_state(
    repository: ExecutionRepository,
    proposed_rows: list[dict[str, Any]],
) -> None:

    print(
        "\nValidating Supabase current state..."
    )

    stored = (
        repository.get_current_state()
    )

    expected = normalized_state(
        proposed_rows
    )

    actual = normalized_repository_state(
        stored
    )

    print(
        f"Expected state rows: "
        f"{len(expected)}"
    )

    print(
        f"Stored state rows:   "
        f"{len(actual)}"
    )

    if expected != actual:

        expected_ids = set(expected)
        actual_ids = set(actual)

        only_expected = (
            expected_ids - actual_ids
        )

        only_actual = (
            actual_ids - expected_ids
        )

        changed = []

        for task_id in (
            expected_ids
            & actual_ids
        ):
            if (
                expected[task_id]
                != actual[task_id]
            ):
                changed.append(
                    task_id
                )

        print(
            "\nExecution-state parity failed."
        )

        print(
            f"Only expected: "
            f"{len(only_expected)}"
        )

        print(
            f"Only stored:   "
            f"{len(only_actual)}"
        )

        print(
            f"Different rows:"
            f" {len(changed)}"
        )

        raise RuntimeError(
            "Supabase execution-state "
            "reconciliation failed."
        )

    print(
        "\nRESULT: EXACT CURRENT "
        "EXECUTION STATE PARITY"
    )


# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap current AIOS execution "
            "state into Supabase."
        )
    )

    parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "Write current execution state "
            "to Supabase. Without this flag "
            "the script is read-only."
        ),
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:

    args = parse_args()

    print(
        "=" * 72
    )

    print(
        "AIOS SUPABASE EXECUTION "
        "STATE BOOTSTRAP"
    )

    print(
        "=" * 72
    )

    if args.write:
        print(
            "\nMODE: WRITE"
        )
    else:
        print(
            "\nMODE: DRY RUN"
        )

    print(
        "Notion is always read-only."
    )

    notion_pages = (
        load_notion_non_done_tasks()
    )

    store = SupabaseStore()

    task_repository = (
        TaskRepository(store)
    )

    execution_repository = (
        ExecutionRepository(store)
    )

    task_map = build_task_map(
        task_repository
    )

    (
        rows,
        missing_mappings,
    ) = build_current_state_rows(
        notion_pages,
        task_map,
    )

    print_summary(
        rows,
        missing_mappings,
    )

    validate_proposed_state(
        rows,
        missing_mappings,
    )

    if not args.write:

        print(
            "\nDRY RUN COMPLETE — "
            "NO SUPABASE RECORDS WERE CHANGED."
        )

        print(
            "\nRESULT: EXECUTION STATE "
            "BOOTSTRAP READY TO WRITE"
        )

        return

    write_bootstrap(
        execution_repository,
        rows,
    )

    reconcile_written_state(
        execution_repository,
        rows,
    )


if __name__ == "__main__":
    main()