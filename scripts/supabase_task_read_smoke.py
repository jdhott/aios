"""
Read-only smoke test for the Supabase task compatibility source.

Run:
    python -m scripts.supabase_task_read_smoke
"""

from __future__ import annotations

from aios.storage.task_source import (
    get_supabase_quick_win_candidate_tasks,
    get_supabase_runtime_open_tasks,
    query_supabase_tasks_legacy,
)


def title(
    task,
):
    values = (
        task
        .get(
            "properties",
            {},
        )
        .get(
            "Task Name",
            {},
        )
        .get(
            "title",
            [],
        )
    )

    return "".join(
        item.get(
            "plain_text",
            "",
        )
        for item in values
    ).strip()


def main() -> None:
    runtime_open = (
        get_supabase_runtime_open_tasks()
    )

    quick_win_population = (
        get_supabase_quick_win_candidate_tasks()
    )

    project_open = (
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
            sorts=[
                {
                    "timestamp":
                        "created_time",
                    "direction":
                        "descending",
                }
            ],
            page_size=25,
        )
    )

    completed_memory = (
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

    populations = {
        "runtime_open":
            runtime_open,
        "quick_win_candidates":
            quick_win_population,
        "project_open":
            project_open,
        "completed_memory":
            completed_memory,
    }

    for (
        name,
        tasks,
    ) in populations.items():
        missing_ids = [
            task
            for task in tasks
            if not task.get(
                "id"
            )
        ]

        missing_titles = [
            task
            for task in tasks
            if not title(
                task
            )
        ]

        if missing_ids:
            raise RuntimeError(
                f"{name}: "
                f"{len(missing_ids)} "
                "tasks missing IDs."
            )

        if missing_titles:
            raise RuntimeError(
                f"{name}: "
                f"{len(missing_titles)} "
                "tasks missing titles."
            )

        print(
            f"{name}: {len(tasks)}"
        )

    print(
        "Supabase task read smoke test passed."
    )


if __name__ == "__main__":
    main()
