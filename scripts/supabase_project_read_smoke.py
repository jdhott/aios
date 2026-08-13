"""
Read-only smoke test for Supabase project reads.

Run:
    python -m scripts.supabase_project_read_smoke
"""

from __future__ import annotations

from aios.storage.project_source import (
    get_supabase_projects,
    is_active_legacy_project,
)


def title(project):
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


def main() -> None:
    projects = get_supabase_projects()

    active = [
        project
        for project in projects
        if (
            is_active_legacy_project(
                project
            )
            and title(project)
        )
    ]

    missing_names = [
        project.get("id")
        for project in projects
        if not title(project)
    ]

    if missing_names:
        raise RuntimeError(
            f"Projects missing names: "
            f"{len(missing_names)}"
        )

    print(
        f"Projects returned: {len(projects)}"
    )
    print(
        f"Active projects returned: "
        f"{len(active)}"
    )
    print(
        "Supabase project read smoke test passed."
    )


if __name__ == "__main__":
    main()
