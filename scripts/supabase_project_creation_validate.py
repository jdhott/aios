"""
Read-only validation for Supabase-primary / Notion-mirrored projects.

During this temporary mirror stage:
- every persisted Supabase project must have a unique legacy_notion_id
- every Supabase legacy_notion_id must exist in Notion
- project counts should match exactly
- name/status/active should reconcile for mapped projects

Run:
    python -m scripts.supabase_project_creation_validate
"""

from __future__ import annotations

from aios.storage.project_repository import ProjectRepository
from aios.storage.supabase_store import SupabaseStore

from scripts.supabase_poc_import import (
    PROJECTS_DATABASE_ID,
    query_database,
)


def plain_title(
    props,
    name,
):
    prop = props.get(
        name,
        {},
    )

    values = prop.get(
        "title",
        [],
    )

    return "".join(
        item.get("plain_text", "")
        for item in values
    ).strip()


def select_or_status(
    props,
    name,
):
    prop = props.get(
        name,
        {},
    )

    select = prop.get(
        "select"
    )

    if isinstance(
        select,
        dict,
    ):
        return select.get(
            "name"
        )

    status = prop.get(
        "status"
    )

    if isinstance(
        status,
        dict,
    ):
        return status.get(
            "name"
        )

    return None


def checkbox(
    props,
    name,
):
    prop = props.get(
        name,
        {},
    )

    if "checkbox" not in prop:
        return False

    return bool(
        prop.get("checkbox")
    )


def main() -> None:
    print("=" * 72)
    print(
        "AIOS SUPABASE-PRIMARY "
        "PROJECT CREATION VALIDATION"
    )
    print("=" * 72)
    print("\nREAD ONLY.")

    repo = ProjectRepository(
        SupabaseStore()
    )

    projects = (
        repo.get_all_projects()
    )

    notion_pages = query_database(
        PROJECTS_DATABASE_ID
    )

    notion_by_id = {
        page["id"]: page
        for page in notion_pages
        if page.get("id")
    }

    legacy_ids = [
        project.legacy_notion_id
        for project in projects
        if project.legacy_notion_id
    ]

    missing_legacy = [
        project.id
        for project in projects
        if not project.legacy_notion_id
    ]

    duplicate_legacy = (
        len(legacy_ids)
        - len(set(legacy_ids))
    )

    missing_notion_mirrors = [
        legacy_id
        for legacy_id in legacy_ids
        if legacy_id not in notion_by_id
    ]

    differences = []

    for project in projects:
        notion_id = (
            project.legacy_notion_id
        )

        if not notion_id:
            continue

        page = notion_by_id.get(
            notion_id
        )

        if not page:
            continue

        props = page.get(
            "properties",
            {},
        )

        notion_name = plain_title(
            props,
            "Project Name",
        )

        notion_status = select_or_status(
            props,
            "Status",
        )

        # The Active property was present in the verified migration source.
        notion_active = checkbox(
            props,
            "Active",
        )

        if (
            notion_name
            and project.name
            != notion_name
        ):
            differences.append(
                (
                    project.id,
                    "name",
                )
            )

        if (
            project.status
            != notion_status
        ):
            differences.append(
                (
                    project.id,
                    "status",
                )
            )

        if (
            bool(project.is_active)
            != bool(notion_active)
        ):
            differences.append(
                (
                    project.id,
                    "is_active",
                )
            )

    print(
        f"\nSupabase projects:          "
        f"{len(projects)}"
    )
    print(
        f"Notion projects:            "
        f"{len(notion_pages)}"
    )
    print(
        f"Missing legacy IDs:         "
        f"{len(missing_legacy)}"
    )
    print(
        f"Duplicate legacy IDs:       "
        f"{duplicate_legacy}"
    )
    print(
        f"Missing Notion mirrors:     "
        f"{len(missing_notion_mirrors)}"
    )
    print(
        f"Field differences:          "
        f"{len(differences)}"
    )

    failures = []

    if (
        len(projects)
        != len(notion_pages)
    ):
        failures.append(
            "Project counts differ: "
            f"Supabase={len(projects)}, "
            f"Notion={len(notion_pages)}"
        )

    if missing_legacy:
        failures.append(
            f"Projects missing legacy ID: "
            f"{len(missing_legacy)}"
        )

    if duplicate_legacy:
        failures.append(
            f"Duplicate legacy IDs: "
            f"{duplicate_legacy}"
        )

    if missing_notion_mirrors:
        failures.append(
            "Supabase projects missing "
            f"Notion mirror: "
            f"{len(missing_notion_mirrors)}"
        )

    if differences:
        failures.append(
            f"Project field differences: "
            f"{len(differences)}"
        )

    if failures:
        print(
            "\nRESULT: SUPABASE-PRIMARY "
            "PROJECT CREATION VALIDATION FAILED"
        )

        for failure in failures:
            print(
                f"  - {failure}"
            )

        raise SystemExit(1)

    print(
        "\nRESULT: EXACT PROJECT MIRROR PARITY"
    )


if __name__ == "__main__":
    main()
