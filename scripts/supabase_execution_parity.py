"""
AIOS Supabase execution parity test.

Compares Execution Engine V2 results for the same task sample from:

1. Raw Notion task records
2. Supabase Task models loaded through TaskRepository

This script is READ ONLY.

It does not:
- update Notion
- update Supabase
- change Execution Score / Rank
- change BNA state

Run from the AIOS project root:

    python -m scripts.supabase_execution_parity
"""

from __future__ import annotations

import argparse
from typing import Any

from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository

from execution_engine_v2 import (
    EVALUATOR_AVAILABLE,
    evaluate_execution_scoring,
    extract_title,
    filter_execution_eligible_tasks,
)

from scripts.supabase_poc_import import (
    TASKS_DATABASE_ID,
    notion_task_to_model,
    query_database,
    select_representative_tasks,
)


DEFAULT_LIMIT = 25
DEFAULT_BNA_LIMIT = 5


# ---------------------------------------------------------------------------
# Legacy Execution Engine compatibility helpers
# ---------------------------------------------------------------------------

def title_property(value: str) -> dict[str, Any]:
    return {
        "type": "title",
        "title": [
            {
                "plain_text": value,
                "text": {
                    "content": value,
                },
            }
        ],
    }


def select_property(value: str | None) -> dict[str, Any]:
    return {
        "type": "select",
        "select": (
            {"name": value}
            if value
            else None
        ),
    }


def checkbox_property(value: bool) -> dict[str, Any]:
    return {
        "type": "checkbox",
        "checkbox": bool(value),
    }


def date_property(value: str | None) -> dict[str, Any]:
    return {
        "type": "date",
        "date": (
            {"start": value}
            if value
            else None
        ),
    }


def number_property(value: int | float | None) -> dict[str, Any]:
    return {
        "type": "number",
        "number": value,
    }


def task_model_to_engine_task(task) -> dict[str, Any]:
    """
    Convert the datastore-neutral AIOS Task model into the temporary
    Notion-shaped structure expected by the current Execution Engine V2.

    This compatibility layer is temporary and will disappear once the
    execution engine consumes Task models directly.
    """

    return {
        "id": task.legacy_notion_id,
        "_supabase_id": task.id,
        "_source": "supabase",

        "properties": {
            "Task Name":
                title_property(
                    task.title
                ),

            "Open Loop":
                checkbox_property(
                    task.is_open
                ),

            "Done":
                checkbox_property(
                    task.is_done
                ),

            "Archived":
                checkbox_property(
                    task.is_archived
                ),

            "Status":
                select_property(
                    task.status
                ),

            "Importance":
                select_property(
                    task.importance
                ),

            "Urgency":
                select_property(
                    task.urgency
                ),

            "Effort":
                select_property(
                    task.effort
                ),

            "Duration":
                select_property(
                    task.duration
                ),

            "Due Date":
                date_property(
                    task.due_at.isoformat()
                    if task.due_at
                    else None
                ),

            "Defer Until":
                date_property(
                    task.defer_until.isoformat()
                    if task.defer_until
                    else None
                ),

            "Just Do It":
                checkbox_property(
                    task.is_just_do_it
                ),

            "Quick Win":
                checkbox_property(
                    task.is_quick_win
                ),

            # These no longer live on the task row in Supabase.
            # They remain present here only because the legacy engine
            # expects the properties to exist.
            "Execution Score":
                number_property(None),

            "Execution Rank":
                number_property(None),
        },
    }


# ---------------------------------------------------------------------------
# Legacy row compatibility helper
#
# Keep this for now because supabase_write_evaluations.py still imports it.
# We will remove it when that script is converted to TaskRepository too.
# ---------------------------------------------------------------------------

def supabase_row_to_engine_task(
    row: dict[str, Any],
) -> dict[str, Any]:

    return {
        "id": row["legacy_notion_id"],
        "_supabase_id": row["id"],
        "_source": "supabase",

        "properties": {
            "Task Name":
                title_property(
                    row.get("title")
                    or "(Untitled Task)"
                ),

            "Open Loop":
                checkbox_property(
                    row.get("is_open", True)
                ),

            "Done":
                checkbox_property(
                    row.get("is_done", False)
                ),

            "Archived":
                checkbox_property(
                    row.get("is_archived", False)
                ),

            "Status":
                select_property(
                    row.get("status")
                ),

            "Importance":
                select_property(
                    row.get("importance")
                ),

            "Urgency":
                select_property(
                    row.get("urgency")
                ),

            "Effort":
                select_property(
                    row.get("effort")
                ),

            "Duration":
                select_property(
                    row.get("duration")
                ),

            "Due Date":
                date_property(
                    row.get("due_at")
                ),

            "Defer Until":
                date_property(
                    row.get("defer_until")
                ),

            "Just Do It":
                checkbox_property(
                    row.get(
                        "is_just_do_it",
                        False,
                    )
                ),

            "Quick Win":
                checkbox_property(
                    row.get(
                        "is_quick_win",
                        False,
                    )
                ),

            "Execution Score":
                number_property(None),

            "Execution Rank":
                number_property(None),
        },
    }


# ---------------------------------------------------------------------------
# Pure ranking wrapper around current Execution Engine V2
# ---------------------------------------------------------------------------

def rank_tasks_like_execution_engine(
    open_tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Reproduce the scoring/ranking portion of rebuild_execution_state()
    without calling mutation, telemetry or persistence paths.

    Uses the current Execution Engine V2 scoring functions themselves.
    """

    eligible_tasks = filter_execution_eligible_tasks(
        open_tasks
    )

    ranked: list[dict[str, Any]] = []

    for task in eligible_tasks:

        title = extract_title(task)

        orchestration = evaluate_execution_scoring(
            task
        )

        if EVALUATOR_AVAILABLE:

            score = orchestration.evaluator_score

            reasons = [
                component.name
                for component
                in orchestration.evaluator_components
            ]

            # Match current Execution Engine V2 fallback behaviour.
            if score == 0:

                if orchestration.legacy_score > 0:

                    score = orchestration.legacy_score
                    reasons = orchestration.legacy_reasons

                else:

                    structurally_reasonable = (
                        len(
                            title.strip().split()
                        ) >= 3
                    )

                    if structurally_reasonable:
                        score = 1
                        reasons = [
                            "baseline_executable"
                        ]

        else:

            score = orchestration.legacy_score
            reasons = orchestration.legacy_reasons

        ranked.append({
            "task": task,
            "legacy_notion_id": task["id"],
            "title": title,
            "score": score,
            "reasons": reasons,
            "legacy_score":
                orchestration.legacy_score,
            "evaluator_score":
                orchestration.evaluator_score,
            "divergence":
                orchestration.divergence,
            "components": [
                {
                    "name": component.name,
                    "score": component.score,
                }
                for component
                in orchestration.evaluator_components
            ],
        })

    ranked.sort(
        key=lambda item: (
            -item["score"],
            item["title"].lower(),
            item.get("page_id", ""),
        )
    )

    for rank, item in enumerate(
        ranked,
        start=1,
    ):
        item["rank"] = rank

    return ranked


# ---------------------------------------------------------------------------
# Fetch the same sample from both systems
# ---------------------------------------------------------------------------

def get_notion_sample(
    limit: int,
) -> tuple[
    list[dict[str, Any]],
    set[str],
]:
    print("Reading Notion Tasks...")

    pages = query_database(
        TASKS_DATABASE_ID
    )

    models = [
        notion_task_to_model(page)
        for page in pages
    ]

    selected_models = (
        select_representative_tasks(
            models,
            limit,
        )
    )

    selected_ids = {
        task.id
        for task in selected_models
    }

    selected_pages = [
        page
        for page in pages
        if page["id"] in selected_ids
    ]

    return selected_pages, selected_ids


def get_supabase_sample(
    store: SupabaseStore,
    notion_ids: set[str],
) -> list[dict[str, Any]]:
    """
    Fetch the imported POC sample through TaskRepository.

    Supabase table structure is intentionally hidden from this function.
    """

    repository = TaskRepository(
        store
    )

    tasks = repository.get_all_tasks()

    selected = [
        task
        for task in tasks
        if task.legacy_notion_id in notion_ids
    ]

    return [
        task_model_to_engine_task(task)
        for task in selected
    ]


# ---------------------------------------------------------------------------
# Open-task input
# ---------------------------------------------------------------------------

def notion_is_open(
    task: dict[str, Any],
) -> bool:

    props = task.get(
        "properties",
        {}
    )

    return (
        props.get(
            "Open Loop",
            {}
        ).get("checkbox") is True

        and props.get(
            "Done",
            {}
        ).get("checkbox") is not True

        and props.get(
            "Archived",
            {}
        ).get("checkbox") is not True
    )


def get_open_tasks(
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    return [
        task
        for task in tasks
        if notion_is_open(task)
    ]


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def indexed_by_id(
    ranked: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:

    return {
        item["legacy_notion_id"]: item
        for item in ranked
    }


def compare_rankings(
    notion_ranked: list[dict[str, Any]],
    supabase_ranked: list[dict[str, Any]],
    bna_limit: int,
) -> bool:

    notion_index = indexed_by_id(
        notion_ranked
    )

    supabase_index = indexed_by_id(
        supabase_ranked
    )

    all_ids = (
        set(notion_index)
        | set(supabase_index)
    )

    differences: list[str] = []

    print("\n" + "=" * 72)
    print("TASK-BY-TASK PARITY")
    print("=" * 72)

    for notion_id in sorted(all_ids):

        notion_item = notion_index.get(
            notion_id
        )

        supabase_item = supabase_index.get(
            notion_id
        )

        if not notion_item:

            differences.append(
                f"{notion_id}: eligible only "
                "from Supabase"
            )
            continue

        if not supabase_item:

            differences.append(
                f"{notion_id}: eligible only "
                "from Notion"
            )
            continue

        same_score = (
            notion_item["score"]
            == supabase_item["score"]
        )

        same_rank = (
            notion_item["rank"]
            == supabase_item["rank"]
        )

        same_legacy = (
            notion_item["legacy_score"]
            == supabase_item["legacy_score"]
        )

        same_evaluator = (
            notion_item["evaluator_score"]
            == supabase_item["evaluator_score"]
        )

        result = (
            "MATCH"
            if (
                same_score
                and same_rank
                and same_legacy
                and same_evaluator
            )
            else "DIFF"
        )

        print(
            f"{result:5} "
            f"rank N={notion_item['rank']:>2} "
            f"S={supabase_item['rank']:>2} | "
            f"score N={notion_item['score']:>3} "
            f"S={supabase_item['score']:>3} | "
            f"{notion_item['title']}"
        )

        if result == "DIFF":

            differences.append(
                (
                    f"{notion_item['title']}: "
                    f"rank "
                    f"{notion_item['rank']} / "
                    f"{supabase_item['rank']}, "
                    f"score "
                    f"{notion_item['score']} / "
                    f"{supabase_item['score']}, "
                    f"legacy "
                    f"{notion_item['legacy_score']} / "
                    f"{supabase_item['legacy_score']}, "
                    f"evaluator "
                    f"{notion_item['evaluator_score']} / "
                    f"{supabase_item['evaluator_score']}"
                )
            )

    notion_winners = [
        item["legacy_notion_id"]
        for item
        in notion_ranked[:bna_limit]
    ]

    supabase_winners = [
        item["legacy_notion_id"]
        for item
        in supabase_ranked[:bna_limit]
    ]

    print("\n" + "=" * 72)
    print("SAMPLE BNA PARITY")
    print("=" * 72)

    print("\nNotion sample winners:")

    for item in notion_ranked[:bna_limit]:
        print(
            f"  {item['rank']}. "
            f"{item['title']} "
            f"(score={item['score']})"
        )

    print("\nSupabase sample winners:")

    for item in supabase_ranked[:bna_limit]:
        print(
            f"  {item['rank']}. "
            f"{item['title']} "
            f"(score={item['score']})"
        )

    bna_match = (
        notion_winners
        == supabase_winners
    )

    if not bna_match:
        differences.append(
            "Top BNA sample ordering differs."
        )

    print("\n" + "=" * 72)
    print("PARITY SUMMARY")
    print("=" * 72)

    print(
        f"Notion eligible tasks:   "
        f"{len(notion_ranked)}"
    )

    print(
        f"Supabase eligible tasks: "
        f"{len(supabase_ranked)}"
    )

    print(
        f"BNA sample match:        "
        f"{bna_match}"
    )

    print(
        f"Differences:             "
        f"{len(differences)}"
    )

    if differences:

        print("\nDifferences found:")

        for difference in differences:
            print(
                f"  - {difference}"
            )

        print(
            "\nRESULT: PARITY FAILED"
        )

        return False

    print(
        "\nRESULT: EXACT EXECUTION PARITY"
    )

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "Compare current AIOS execution "
            "scoring from Notion and Supabase."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=(
            "Representative POC sample size. "
            f"Default: {DEFAULT_LIMIT}"
        ),
    )

    parser.add_argument(
        "--bna-limit",
        type=int,
        default=DEFAULT_BNA_LIMIT,
        help=(
            "Number of sample winners to compare. "
            f"Default: {DEFAULT_BNA_LIMIT}"
        ),
    )

    return parser.parse_args()


def main() -> None:

    args = parse_args()

    print("=" * 72)
    print("AIOS SUPABASE EXECUTION PARITY TEST")
    print("=" * 72)

    print(
        f"Evaluator available: {EVALUATOR_AVAILABLE}"
    )

    print(
        "\nREAD ONLY: no Notion or "
        "Supabase records will be changed."
    )

    notion_tasks, notion_ids = (
        get_notion_sample(
            args.limit
        )
    )

    print(
        f"\nNotion POC tasks found: "
        f"{len(notion_tasks)}"
    )

    store = SupabaseStore()

    supabase_tasks = (
        get_supabase_sample(
            store,
            notion_ids,
        )
    )

    print(
        f"Supabase POC tasks found: "
        f"{len(supabase_tasks)}"
    )

    if (
        len(supabase_tasks)
        != len(notion_tasks)
    ):
        print(
            "\nWARNING: The two sources do "
            "not contain the same sample size."
        )

    notion_open = get_open_tasks(
        notion_tasks
    )

    supabase_open = get_open_tasks(
        supabase_tasks
    )

    print(
        f"\nOpen tasks in Notion sample: "
        f"{len(notion_open)}"
    )

    print(
        f"Open tasks in Supabase sample: "
        f"{len(supabase_open)}"
    )

    print("\n--- NOTION EXECUTION PASS ---")

    notion_ranked = (
        rank_tasks_like_execution_engine(
            notion_open
        )
    )

    print("\n--- SUPABASE EXECUTION PASS ---")

    supabase_ranked = (
        rank_tasks_like_execution_engine(
            supabase_open
        )
    )

    success = compare_rankings(
        notion_ranked,
        supabase_ranked,
        args.bna_limit,
    )

    if not success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()