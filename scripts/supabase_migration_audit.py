"""
AIOS Supabase full-migration readiness audit.

READ ONLY.

This script classifies Notion properties into:

1. CORE MAPPED
   Stored directly in the new Supabase schema.

2. LEGACY METADATA
   Preserved inside legacy_metadata JSON.

3. DERIVED / INTENTIONALLY EXCLUDED
   Not migrated as task/project columns because they are:
   - derived
   - reverse relations
   - execution outputs
   - obsolete Notion workflow fields
   - otherwise intentionally excluded

Only populated properties that fall into none of those categories
are treated as unresolved migration blockers.

It does NOT modify Notion or Supabase.

Run:

    python -m scripts.supabase_migration_audit
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from scripts.supabase_poc_import import (
    PROJECTS_DATABASE_ID,
    TASKS_DATABASE_ID,
    query_database,
)


# ---------------------------------------------------------------------------
# Task property classification
# ---------------------------------------------------------------------------

CORE_TASK_PROPERTIES = {
    "Task Name",
    "Open Loop",
    "Done",
    "Archived",
    "Status",
    "Importance",
    "Urgency",
    "Effort",
    "Duration",
    "Due Date",
    "Defer Until",
    "Just Do It",
    "Quick Win",
    "Suggested Project",
    "Project",
    "Parent Task",
    "Step Order",
}


LEGACY_TASK_PROPERTIES = {
    "AI Generated",
    "Do",
    "Do Date",
    "Duplicate",
    "Duplicate notes",
    "Priority",
    "Reviewed",
    "Start",
    "End",
    "Tags",
    "Task Type",
    "Who",
}


DERIVED_TASK_PROPERTIES = {
    # AIOS execution state now belongs in execution history.
    "Execution Rank",
    "Execution Score",

    # Current/legacy AI presentation or ranking state.
    "Strong Candidate",
    "Surfaced Quick Win",
    "Focus",
    "Focus Now",

    # Reverse/derived relations.
    "Sub Tasks",
    "Has Open Subtasks",

    # Notion-managed timestamps already mapped from page metadata.
    "Create Date",
    "Modified Date",

    # Currently unused AI workflow properties.
    "AI Confidence",
    "AI Modified",
    "Broken Down By AI",
    "Clarified By AI",

    # Currently unused relations / ontology fields.
    "Goal",
    "Knowledge Topic",
    "Notes",
    "Pillar",
    "PiIlar Type",
}


# ---------------------------------------------------------------------------
# Project property classification
# ---------------------------------------------------------------------------

CORE_PROJECT_PROPERTIES = {
    "Project Name",
    "Status",
    "Active",
}


LEGACY_PROJECT_PROPERTIES = {
    "Area",
    "Priority",
    "Project Type",
}


DERIVED_PROJECT_PROPERTIES = {
    # Notion rollups / reverse relations.
    "Focus Now Tasks",
    "Last Activity",
    "Open Tasks",
    "Task Relation",

    # Notion-managed timestamp.
    "Last Modified",

    # Currently unused legacy/ontology properties.
    "AI Locked",
    "Areas",
    "Notes",
    "Notes DB",
    "Outome",
    "Related to Resources (Project)",
    "Roles",
    "Tags",
    "User Created",
}


# ---------------------------------------------------------------------------
# Property inspection helpers
# ---------------------------------------------------------------------------

def property_is_populated(
    prop: dict[str, Any],
) -> bool:

    prop_type = prop.get("type")

    if prop_type == "title":
        return bool(prop.get("title"))

    if prop_type == "rich_text":
        return bool(prop.get("rich_text"))

    if prop_type == "checkbox":
        return prop.get("checkbox") is True

    if prop_type == "select":
        return prop.get("select") is not None

    if prop_type == "multi_select":
        return bool(prop.get("multi_select"))

    if prop_type == "status":
        return prop.get("status") is not None

    if prop_type == "date":
        return prop.get("date") is not None

    if prop_type == "number":
        return prop.get("number") is not None

    if prop_type == "relation":
        return bool(prop.get("relation"))

    if prop_type == "people":
        return bool(prop.get("people"))

    if prop_type == "files":
        return bool(prop.get("files"))

    if prop_type == "url":
        return bool(prop.get("url"))

    if prop_type == "email":
        return bool(prop.get("email"))

    if prop_type == "phone_number":
        return bool(prop.get("phone_number"))

    if prop_type == "formula":
        value = prop.get(
            "formula",
            {},
        )

        formula_type = value.get("type")

        if formula_type:
            return (
                value.get(formula_type)
                is not None
            )

        return bool(value)

    if prop_type == "rollup":
        return bool(
            prop.get("rollup")
        )

    if prop_type == "created_time":
        return bool(
            prop.get("created_time")
        )

    if prop_type == "last_edited_time":
        return bool(
            prop.get("last_edited_time")
        )

    if prop_type == "created_by":
        return bool(
            prop.get("created_by")
        )

    if prop_type == "last_edited_by":
        return bool(
            prop.get("last_edited_by")
        )

    return bool(
        prop.get(prop_type)
    )


def relation_count(
    prop: dict[str, Any],
) -> int:

    if prop.get("type") != "relation":
        return 0

    return len(
        prop.get(
            "relation",
            [],
        )
    )


def page_title(
    page: dict[str, Any],
    title_property: str,
) -> str:

    prop = (
        page.get(
            "properties",
            {},
        )
        .get(
            title_property,
            {},
        )
    )

    values = prop.get(
        "title",
        [],
    )

    text = "".join(
        item.get("plain_text", "")
        for item in values
    ).strip()

    return text or "(Untitled)"


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_property(
    name: str,
    core: set[str],
    legacy: set[str],
    derived: set[str],
) -> str:

    if name in core:
        return "CORE"

    if name in legacy:
        return "LEGACY"

    if name in derived:
        return "DERIVED"

    return "UNRESOLVED"


# ---------------------------------------------------------------------------
# Generic property audit
# ---------------------------------------------------------------------------

def audit_properties(
    pages: list[dict[str, Any]],
    core_properties: set[str],
    legacy_properties: set[str],
    derived_properties: set[str],
    title_property: str,
    label: str,
) -> dict[str, int]:

    types: dict[
        str,
        Counter[str],
    ] = defaultdict(Counter)

    populated_counts: Counter[str] = Counter()
    presence_counts: Counter[str] = Counter()

    examples: dict[
        str,
        list[str],
    ] = defaultdict(list)

    for page in pages:

        props = page.get(
            "properties",
            {},
        )

        title = page_title(
            page,
            title_property,
        )

        for name, prop in props.items():

            presence_counts[name] += 1

            prop_type = (
                prop.get("type")
                or "(unknown)"
            )

            types[name][prop_type] += 1

            if property_is_populated(prop):

                populated_counts[name] += 1

                if len(
                    examples[name]
                ) < 3:

                    examples[name].append(
                        title
                    )

    property_names = sorted(
        presence_counts.keys()
    )

    print("\n" + "=" * 80)
    print(
        f"{label.upper()} PROPERTY AUDIT"
    )
    print("=" * 80)

    print(
        f"Records examined: {len(pages)}"
    )

    print(
        f"Properties found: "
        f"{len(property_names)}"
    )

    print("\nAll properties:")

    unresolved_populated: dict[
        str,
        int,
    ] = {}

    for name in property_names:

        classification = classify_property(
            name,
            core_properties,
            legacy_properties,
            derived_properties,
        )

        type_text = ", ".join(
            f"{prop_type}:{count}"
            for prop_type, count
            in types[name].items()
        )

        print(
            f"  {classification:10} "
            f"{name:<30} "
            f"populated={populated_counts[name]:>4} "
            f"present={presence_counts[name]:>4} "
            f"type={type_text}"
        )

        if (
            classification == "UNRESOLVED"
            and populated_counts[name] > 0
        ):
            unresolved_populated[name] = (
                populated_counts[name]
            )

    print(
        "\nPopulated unresolved properties:"
    )

    if not unresolved_populated:
        print("  None")

    else:

        for (
            name,
            count,
        ) in unresolved_populated.items():

            print(
                f"  - {name}: "
                f"{count} records"
            )

            for example in examples[name]:
                print(
                    f"      example: "
                    f"{example}"
                )

    return unresolved_populated


# ---------------------------------------------------------------------------
# Task relationship audit
# ---------------------------------------------------------------------------

def audit_task_relationships(
    pages: list[dict[str, Any]],
) -> tuple[int, int]:

    multi_project = []
    multi_parent = []

    project_relations = 0
    parent_relations = 0

    for page in pages:

        props = page.get(
            "properties",
            {},
        )

        title = page_title(
            page,
            "Task Name",
        )

        project_count = relation_count(
            props.get(
                "Project",
                {},
            )
        )

        parent_count = relation_count(
            props.get(
                "Parent Task",
                {},
            )
        )

        if project_count:
            project_relations += 1

        if parent_count:
            parent_relations += 1

        if project_count > 1:
            multi_project.append(
                (
                    title,
                    project_count,
                )
            )

        if parent_count > 1:
            multi_parent.append(
                (
                    title,
                    parent_count,
                )
            )

    print("\n" + "=" * 80)
    print("TASK RELATIONSHIP AUDIT")
    print("=" * 80)

    print(
        f"Tasks with Project relation: "
        f"{project_relations}"
    )

    print(
        f"Tasks with Parent relation:  "
        f"{parent_relations}"
    )

    print(
        f"Tasks with >1 Project:        "
        f"{len(multi_project)}"
    )

    print(
        f"Tasks with >1 Parent:         "
        f"{len(multi_parent)}"
    )

    return (
        len(multi_project),
        len(multi_parent),
    )


# ---------------------------------------------------------------------------
# Task lifecycle audit
# ---------------------------------------------------------------------------

def checkbox_value(
    prop: dict[str, Any],
) -> bool:

    return (
        prop.get("type") == "checkbox"
        and prop.get("checkbox") is True
    )


def audit_task_lifecycle(
    pages: list[dict[str, Any]],
) -> None:

    state_counts = Counter()

    for page in pages:

        props = page.get(
            "properties",
            {},
        )

        is_open = checkbox_value(
            props.get(
                "Open Loop",
                {},
            )
        )

        is_done = checkbox_value(
            props.get(
                "Done",
                {},
            )
        )

        is_archived = checkbox_value(
            props.get(
                "Archived",
                {},
            )
        )

        state_counts[
            (
                is_open,
                is_done,
                is_archived,
            )
        ] += 1

    print("\n" + "=" * 80)
    print("TASK LIFECYCLE AUDIT")
    print("=" * 80)

    print(
        "Observed Open / Done / "
        "Archived combinations:"
    )

    for (
        state,
        count,
    ) in sorted(
        state_counts.items(),
        key=lambda item: -item[1],
    ):

        print(
            f"  Open={state[0]:<5} "
            f"Done={state[1]:<5} "
            f"Archived={state[2]:<5} "
            f"count={count}"
        )

    print(
        "\nNote: Open Loop and Done are "
        "preserved independently for "
        "migration parity."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:

    print("=" * 80)
    print(
        "AIOS SUPABASE "
        "FULL-MIGRATION READINESS AUDIT"
    )
    print("=" * 80)

    print(
        "\nREAD ONLY — no Notion or "
        "Supabase records will be changed."
    )

    print(
        "\nReading Projects from Notion..."
    )

    projects = query_database(
        PROJECTS_DATABASE_ID
    )

    print(
        f"Projects read: {len(projects)}"
    )

    print(
        "\nReading Tasks from Notion..."
    )

    tasks = query_database(
        TASKS_DATABASE_ID
    )

    print(
        f"Tasks read: {len(tasks)}"
    )

    unresolved_projects = (
        audit_properties(
            projects,
            CORE_PROJECT_PROPERTIES,
            LEGACY_PROJECT_PROPERTIES,
            DERIVED_PROJECT_PROPERTIES,
            "Project Name",
            "Projects",
        )
    )

    unresolved_tasks = (
        audit_properties(
            tasks,
            CORE_TASK_PROPERTIES,
            LEGACY_TASK_PROPERTIES,
            DERIVED_TASK_PROPERTIES,
            "Task Name",
            "Tasks",
        )
    )

    (
        multi_project_count,
        multi_parent_count,
    ) = audit_task_relationships(
        tasks
    )

    audit_task_lifecycle(
        tasks
    )

    blockers = []

    if unresolved_tasks:
        blockers.append(
            "Tasks contain populated "
            "unresolved properties."
        )

    if unresolved_projects:
        blockers.append(
            "Projects contain populated "
            "unresolved properties."
        )

    if multi_project_count:
        blockers.append(
            "Some tasks have multiple "
            "Project relationships."
        )

    if multi_parent_count:
        blockers.append(
            "Some tasks have multiple "
            "Parent Task relationships."
        )

    print("\n" + "=" * 80)
    print("MIGRATION READINESS SUMMARY")
    print("=" * 80)

    print(
        f"Projects examined:        "
        f"{len(projects)}"
    )

    print(
        f"Tasks examined:           "
        f"{len(tasks)}"
    )

    print(
        f"Unresolved task fields:   "
        f"{len(unresolved_tasks)}"
    )

    print(
        f"Unresolved project fields:"
        f" {len(unresolved_projects)}"
    )

    print(
        f"Multi-project tasks:      "
        f"{multi_project_count}"
    )

    print(
        f"Multi-parent tasks:       "
        f"{multi_parent_count}"
    )

    if blockers:

        print(
            "\nRESULT: REVIEW REQUIRED "
            "BEFORE FULL MIGRATION"
        )

        print(
            "\nPotential migration blockers:"
        )

        for blocker in blockers:
            print(
                f"  - {blocker}"
            )

    else:

        print(
            "\nRESULT: SCHEMA READY "
            "FOR FULL MIGRATION"
        )


if __name__ == "__main__":
    main()