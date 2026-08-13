"""
Compare Notion and Supabase project READ representations.

READ ONLY.

Run:
    python -m scripts.supabase_project_read_parity
"""

from __future__ import annotations

from aios.storage.project_source import (
    get_supabase_projects,
    is_active_legacy_project,
    legacy_status,
)

from scripts.supabase_poc_import import (
    PROJECTS_DATABASE_ID,
    query_database,
)


def notion_title(
    project,
):
    values = (
        project
        .get("properties", {})
        .get("Project Name", {})
        .get("title", [])
    )

    return "".join(
        item.get(
            "plain_text",
            "",
        )
        for item in values
    ).strip()


def active_checkbox(
    project,
):
    prop = (
        project
        .get("properties", {})
        .get("Active", {})
    )

    if prop.get(
        "type"
    ) == "checkbox":
        return bool(
            prop.get(
                "checkbox"
            )
        )

    return None


def normalized(
    project,
):
    return {
        "name":
            notion_title(
                project
            ),
        "status":
            legacy_status(
                project
            ),
        "active":
            active_checkbox(
                project
            ),
        "is_active_effective":
            is_active_legacy_project(
                project
            ),
    }


def main() -> None:
    print("=" * 72)
    print(
        "AIOS PROJECT READ "
        "NOTION / SUPABASE PARITY"
    )
    print("=" * 72)
    print("\nREAD ONLY.")

    notion = query_database(
        PROJECTS_DATABASE_ID
    )

    supabase = (
        get_supabase_projects()
    )

    notion_by_id = {
        project["id"]:
            normalized(
                project
            )
        for project in notion
        if project.get("id")
    }

    supabase_by_legacy_id = {
        project["id"]:
            normalized(
                project
            )
        for project in supabase
        if project.get("id")
    }

    notion_ids = set(
        notion_by_id
    )
    supabase_ids = set(
        supabase_by_legacy_id
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

    for project_id in (
        notion_ids
        & supabase_ids
    ):
        if (
            notion_by_id[
                project_id
            ]
            !=
            supabase_by_legacy_id[
                project_id
            ]
        ):
            differences.append(
                project_id
            )

    notion_active = sum(
        1
        for project in notion
        if (
            is_active_legacy_project(
                project
            )
            and notion_title(
                project
            )
        )
    )

    supabase_active = sum(
        1
        for project in supabase
        if (
            is_active_legacy_project(
                project
            )
            and notion_title(
                project
            )
        )
    )

    print(
        f"\nNotion projects:           "
        f"{len(notion)}"
    )
    print(
        f"Supabase projects:         "
        f"{len(supabase)}"
    )
    print(
        f"Notion active projects:    "
        f"{notion_active}"
    )
    print(
        f"Supabase active projects:  "
        f"{supabase_active}"
    )
    print(
        f"Only in Notion:            "
        f"{len(only_notion)}"
    )
    print(
        f"Only in Supabase:          "
        f"{len(only_supabase)}"
    )
    print(
        f"Field differences:         "
        f"{len(differences)}"
    )

    failures = []

    if len(notion) != len(supabase):
        failures.append(
            "Project counts differ."
        )

    if (
        notion_active
        != supabase_active
    ):
        failures.append(
            "Active-project counts differ."
        )

    if only_notion:
        failures.append(
            f"Projects only in Notion: "
            f"{len(only_notion)}"
        )

    if only_supabase:
        failures.append(
            f"Projects only in Supabase: "
            f"{len(only_supabase)}"
        )

    if differences:
        failures.append(
            f"Project field differences: "
            f"{len(differences)}"
        )

    if failures:
        print(
            "\nRESULT: PROJECT READ PARITY FAILED"
        )

        for failure in failures:
            print(
                f"  - {failure}"
            )

        if differences:
            print(
                "\nFirst differing project IDs:"
            )

            for project_id in (
                differences[:10]
            ):
                print(
                    f"  - {project_id}"
                )
                print(
                    "    Notion:   ",
                    notion_by_id[
                        project_id
                    ],
                )
                print(
                    "    Supabase: ",
                    supabase_by_legacy_id[
                        project_id
                    ],
                )

        raise SystemExit(1)

    print(
        "\nRESULT: EXACT PROJECT READ PARITY"
    )


if __name__ == "__main__":
    main()
