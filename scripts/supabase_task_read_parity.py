"""
Read-only Notion / Supabase task READ parity validation.

Compares the exact task populations used by the live runtime:
1. Runtime open tasks:
     Open Loop=True, Done=False
2. Project-cognition open tasks:
     Open Loop=True, Done=False, Archived=False
3. Quick Win candidate population:
     Open Loop=True, Done=False, Archived=False, Just Do It=False
4. Historical operational memory:
     Done=True, Archived=False

The historical-memory order comparison uses Notion last_edited_time versus
Supabase updated_at, which is the intended migration equivalent.

Run:
    python -m scripts.supabase_task_read_parity
"""

from __future__ import annotations

from scripts.supabase_poc_import import (
    TASKS_DATABASE_ID,
    query_database,
)

from aios.storage.task_source import (
    get_supabase_quick_win_candidate_tasks,
    get_supabase_runtime_open_tasks,
    query_supabase_tasks_legacy,
)


def checkbox(
    task,
    name,
) -> bool:
    return bool(
        (
            task
            .get(
                "properties",
                {},
            )
            .get(
                name,
                {},
            )
            .get(
                "checkbox"
            )
        )
    )


def task_id(
    task,
):
    return task.get(
        "id"
    )


def filter_notion(
    tasks,
    *,
    open_loop=None,
    done=None,
    archived=None,
    just_do_it=None,
):
    result = []

    for task in tasks:
        checks = [
            (
                "Open Loop",
                open_loop,
            ),
            (
                "Done",
                done,
            ),
            (
                "Archived",
                archived,
            ),
            (
                "Just Do It",
                just_do_it,
            ),
        ]

        keep = True

        for (
            name,
            expected,
        ) in checks:
            if expected is None:
                continue

            if (
                checkbox(
                    task,
                    name,
                )
                != expected
            ):
                keep = False
                break

        if keep:
            result.append(
                task
            )

    return result


def compare_population(
    name,
    notion,
    supabase,
):
    notion_ids = {
        task_id(task)
        for task in notion
        if task_id(task)
    }

    supabase_ids = {
        task_id(task)
        for task in supabase
        if task_id(task)
    }

    only_notion = (
        notion_ids
        - supabase_ids
    )

    only_supabase = (
        supabase_ids
        - notion_ids
    )

    print(
        f"\n{name}:"
    )
    print(
        f"  Notion:          "
        f"{len(notion)}"
    )
    print(
        f"  Supabase:        "
        f"{len(supabase)}"
    )
    print(
        f"  Only in Notion:  "
        f"{len(only_notion)}"
    )
    print(
        f"  Only in Supabase:"
        f" {len(only_supabase)}"
    )

    return (
        only_notion,
        only_supabase,
    )


def notion_updated_key(
    task,
):
    return str(
        task.get(
            "last_edited_time"
        )
        or ""
    )


def main() -> None:
    print("=" * 72)
    print(
        "AIOS TASK READ "
        "NOTION / SUPABASE PARITY"
    )
    print("=" * 72)
    print(
        "\nREAD ONLY."
    )

    notion_all = query_database(
        TASKS_DATABASE_ID
    )

    notion_runtime_open = (
        filter_notion(
            notion_all,
            open_loop=True,
            done=False,
        )
    )

    supabase_runtime_open = (
        get_supabase_runtime_open_tasks()
    )

    notion_project_open = (
        filter_notion(
            notion_all,
            open_loop=True,
            done=False,
            archived=False,
        )
    )

    supabase_project_open = (
        query_supabase_tasks_legacy(
            filter_payload={
                "and": [
                    {
                        "property":
                            "Open Loop",
                        "checkbox": {
                            "equals":
                                True,
                        },
                    },
                    {
                        "property":
                            "Done",
                        "checkbox": {
                            "equals":
                                False,
                        },
                    },
                    {
                        "property":
                            "Archived",
                        "checkbox": {
                            "equals":
                                False,
                        },
                    },
                ]
            },
            page_size=100,
        )
    )

    notion_quick_win = (
        filter_notion(
            notion_all,
            open_loop=True,
            done=False,
            archived=False,
            just_do_it=False,
        )
    )

    supabase_quick_win = (
        get_supabase_quick_win_candidate_tasks()
    )

    notion_completed = (
        filter_notion(
            notion_all,
            done=True,
            archived=False,
        )
    )

    notion_completed.sort(
        key=notion_updated_key,
        reverse=True,
    )

    supabase_completed = (
        query_supabase_tasks_legacy(
            filter_payload={
                "and": [
                    {
                        "property":
                            "Done",
                        "checkbox": {
                            "equals":
                                True,
                        },
                    },
                    {
                        "property":
                            "Archived",
                        "checkbox": {
                            "equals":
                                False,
                        },
                    },
                ]
            },
            sorts=[
                {
                    "timestamp":
                        "last_edited_time",
                    "direction":
                        "descending",
                }
            ],
            page_size=300,
        )
    )

    failures = []

    comparisons = [
        (
            "Runtime open",
            notion_runtime_open,
            supabase_runtime_open,
        ),
        (
            "Project-cognition open",
            notion_project_open,
            supabase_project_open,
        ),
        (
            "Quick Win candidates",
            notion_quick_win,
            supabase_quick_win,
        ),
        (
            "Completed operational memory",
            notion_completed,
            supabase_completed,
        ),
    ]

    for (
        name,
        notion,
        supabase,
    ) in comparisons:
        only_notion, only_supabase = (
            compare_population(
                name,
                notion,
                supabase,
            )
        )

        if (
            only_notion
            or only_supabase
        ):
            failures.append(
                (
                    name,
                    len(
                        only_notion
                    ),
                    len(
                        only_supabase
                    ),
                )
            )

    # Order is diagnostic rather than a hard failure because Notion
    # last_edited_time and Supabase updated_at can differ when migration or
    # Supabase-only maintenance writes occur.
    notion_order = [
        task_id(task)
        for task in notion_completed
    ]

    supabase_order = [
        task_id(task)
        for task in supabase_completed
    ]

    order_match = (
        notion_order
        == supabase_order
    )

    print(
        "\nCompleted-memory order "
        f"exact match: {order_match}"
    )

    if not order_match:
        first_difference = None

        for index, (
            notion_id,
            supabase_id,
        ) in enumerate(
            zip(
                notion_order,
                supabase_order,
            )
        ):
            if notion_id != supabase_id:
                first_difference = (
                    index,
                    notion_id,
                    supabase_id,
                )
                break

        if first_difference:
            print(
                "First order difference: "
                f"index={first_difference[0]} "
                f"notion={first_difference[1]} "
                f"supabase={first_difference[2]}"
            )

    if failures:
        print(
            "\nRESULT: TASK READ PARITY FAILED"
        )

        for (
            name,
            only_notion_count,
            only_supabase_count,
        ) in failures:
            print(
                f"  - {name}: "
                f"only_notion="
                f"{only_notion_count}, "
                f"only_supabase="
                f"{only_supabase_count}"
            )

        raise SystemExit(1)

    print(
        "\nRESULT: EXACT TASK READ "
        "POPULATION PARITY"
    )


if __name__ == "__main__":
    main()
