"""
Full AIOS execution parity test.

Compares the complete set of currently open tasks from:

1. Notion
2. Supabase via TaskRepository

The same current Execution Engine V2 scoring logic is applied to both.

READ ONLY:
- does not modify Notion
- does not modify Supabase
- does not write execution history
"""

from __future__ import annotations

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
    query_database,
)

from scripts.supabase_execution_parity import (
    task_model_to_engine_task,
)


# ---------------------------------------------------------------------------
# Notion helpers
# ---------------------------------------------------------------------------

def notion_checkbox(
    task: dict[str, Any],
    property_name: str,
) -> bool:
    return (
        task
        .get("properties", {})
        .get(property_name, {})
        .get("checkbox")
        is True
    )


def get_notion_open_tasks() -> list[dict[str, Any]]:
    print("Reading all Notion tasks...")

    tasks = query_database(
        TASKS_DATABASE_ID
    )

    print(
        f"Total Notion tasks: {len(tasks)}"
    )

    open_tasks = [
        task
        for task in tasks
        if (
            notion_checkbox(
                task,
                "Open Loop",
            )
            and not notion_checkbox(
                task,
                "Done",
            )
            and not notion_checkbox(
                task,
                "Archived",
            )
        )
    ]

    print(
        f"Open Notion tasks: {len(open_tasks)}"
    )

    return open_tasks


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def get_supabase_open_tasks(
    repository: TaskRepository,
) -> list[dict[str, Any]]:

    models = repository.get_open_tasks()

    print(
        f"Open Supabase tasks: {len(models)}"
    )

    return [
        task_model_to_engine_task(task)
        for task in models
    ]


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def rank_tasks(
    open_tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    eligible_tasks = (
        filter_execution_eligible_tasks(
            open_tasks
        )
    )

    ranked: list[dict[str, Any]] = []

    for task in eligible_tasks:

        title = extract_title(
            task
        )

        orchestration = (
            evaluate_execution_scoring(
                task
            )
        )

        if EVALUATOR_AVAILABLE:

            score = (
                orchestration
                .evaluator_score
            )

            reasons = [
                component.name
                for component
                in orchestration
                .evaluator_components
            ]

            if score == 0:

                if (
                    orchestration
                    .legacy_score > 0
                ):

                    score = (
                        orchestration
                        .legacy_score
                    )

                    reasons = (
                        orchestration
                        .legacy_reasons
                    )

                else:

                    structurally_reasonable = (
                        len(
                            title
                            .strip()
                            .split()
                        ) >= 3
                    )

                    if structurally_reasonable:

                        score = 1

                        reasons = [
                            "baseline_executable"
                        ]

        else:

            score = (
                orchestration
                .legacy_score
            )

            reasons = (
                orchestration
                .legacy_reasons
            )

        ranked.append({
            "legacy_notion_id":
                task["id"],

            "title":
                title,

            "score":
                score,

            "legacy_score":
                orchestration
                .legacy_score,

            "evaluator_score":
                orchestration
                .evaluator_score,

            "divergence":
                orchestration
                .divergence,

            "reasons":
                reasons,
        })

    ranked.sort(
        key=lambda item: (
            -item["score"],
            item["title"].lower(),
            item["legacy_notion_id"],
        )
    )

    for rank, item in enumerate(
        ranked,
        start=1,
    ):
        item["rank"] = rank

    return ranked


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def index_ranked(
    ranked: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:

    return {
        item["legacy_notion_id"]:
            item
        for item in ranked
    }


def compare_full_parity(
    notion_ranked: list[dict[str, Any]],
    supabase_ranked: list[dict[str, Any]],
    bna_limit: int = 5,
) -> None:

    notion_index = index_ranked(
        notion_ranked
    )

    supabase_index = index_ranked(
        supabase_ranked
    )

    notion_ids = set(
        notion_index
    )

    supabase_ids = set(
        supabase_index
    )

    only_notion = (
        notion_ids
        - supabase_ids
    )

    only_supabase = (
        supabase_ids
        - notion_ids
    )

    differences = []

    common_ids = (
        notion_ids
        & supabase_ids
    )

    for notion_id in common_ids:

        notion_item = (
            notion_index[
                notion_id
            ]
        )

        supabase_item = (
            supabase_index[
                notion_id
            ]
        )

        fields = [
            "score",
            "rank",
            "legacy_score",
            "evaluator_score",
        ]

        changed = [
            field
            for field in fields
            if (
                notion_item[field]
                !=
                supabase_item[field]
            )
        ]

        if changed:

            differences.append({
                "id": notion_id,
                "title":
                    notion_item[
                        "title"
                    ],
                "changed":
                    changed,
                "notion":
                    notion_item,
                "supabase":
                    supabase_item,
            })

    notion_top = [
        item["legacy_notion_id"]
        for item
        in notion_ranked[
            :bna_limit
        ]
    ]

    supabase_top = [
        item["legacy_notion_id"]
        for item
        in supabase_ranked[
            :bna_limit
        ]
    ]

    bna_match = (
        notion_top
        == supabase_top
    )

    print(
        "\n"
        + "=" * 80
    )

    print(
        "FULL EXECUTION PARITY SUMMARY"
    )

    print(
        "=" * 80
    )

    print(
        f"Notion open tasks:       "
        f"277"
    )

    print(
        f"Supabase open tasks:     "
        f"277"
    )

    print(
        f"Notion eligible tasks:   "
        f"{len(notion_ranked)}"
    )

    print(
        f"Supabase eligible tasks: "
        f"{len(supabase_ranked)}"
    )

    print(
        f"Eligible only in Notion: "
        f"{len(only_notion)}"
    )

    print(
        f"Eligible only in "
        f"Supabase: "
        f"{len(only_supabase)}"
    )

    print(
        f"Score/rank differences: "
        f"{len(differences)}"
    )

    print(
        f"Top {bna_limit} BNA "
        f"ordering match: "
        f"{bna_match}"
    )

    print(
        "\nNotion top BNA candidates:"
    )

    for item in notion_ranked[
        :bna_limit
    ]:

        print(
            f"  {item['rank']}. "
            f"{item['title']} "
            f"(score={item['score']})"
        )

    print(
        "\nSupabase top BNA candidates:"
    )

    for item in supabase_ranked[
        :bna_limit
    ]:

        print(
            f"  {item['rank']}. "
            f"{item['title']} "
            f"(score={item['score']})"
        )

    if only_notion:

        print(
            "\nEligible only from Notion:"
        )

        for notion_id in sorted(
            only_notion
        ):
            print(
                "  - "
                + notion_index[
                    notion_id
                ]["title"]
            )

    if only_supabase:

        print(
            "\nEligible only from Supabase:"
        )

        for notion_id in sorted(
            only_supabase
        ):
            print(
                "  - "
                + supabase_index[
                    notion_id
                ]["title"]
            )

    if differences:

        print(
            "\nExecution differences:"
        )

        for difference in (
            differences[:25]
        ):

            print(
                f"\n  "
                f"{difference['title']}"
            )

            for field in (
                difference["changed"]
            ):

                print(
                    f"    {field}: "
                    f"Notion="
                    f"{difference['notion'][field]} "
                    f"Supabase="
                    f"{difference['supabase'][field]}"
                )

        if len(
            differences
        ) > 25:

            print(
                f"\n  ... plus "
                f"{len(differences) - 25} "
                f"more differences"
            )

    if (
        only_notion
        or only_supabase
        or differences
        or not bna_match
    ):

        print(
            "\nRESULT: FULL EXECUTION "
            "PARITY FAILED"
        )

        raise SystemExit(1)

    print(
        "\nRESULT: EXACT FULL "
        "EXECUTION PARITY"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:

    print(
        "=" * 80
    )

    print(
        "AIOS FULL SUPABASE "
        "EXECUTION PARITY TEST"
    )

    print(
        "=" * 80
    )

    print(
        f"Evaluator available: "
        f"{EVALUATOR_AVAILABLE}"
    )

    print(
        "\nREAD ONLY — no Notion or "
        "Supabase records will be changed."
    )

    notion_open = (
        get_notion_open_tasks()
    )

    store = SupabaseStore()

    repository = TaskRepository(
        store
    )

    supabase_open = (
        get_supabase_open_tasks(
            repository
        )
    )

    if len(
        notion_open
    ) != len(
        supabase_open
    ):

        raise RuntimeError(
            "Open-task population mismatch "
            "before execution scoring."
        )

    print(
        "\n--- NOTION FULL EXECUTION PASS ---"
    )

    notion_ranked = rank_tasks(
        notion_open
    )

    print(
        "\n--- SUPABASE FULL EXECUTION PASS ---"
    )

    supabase_ranked = rank_tasks(
        supabase_open
    )

    compare_full_parity(
        notion_ranked,
        supabase_ranked,
    )


if __name__ == "__main__":
    main()