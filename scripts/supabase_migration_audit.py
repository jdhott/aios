"""
AIOS Supabase full-migration readiness audit.

READ ONLY.

This script examines every Notion Task and Project and reports:

- all properties present in Notion
- property types
- how often each property is populated
- which properties are currently mapped to the Supabase model
- which populated properties are currently unmapped
- tasks with multiple Project relations
- tasks with multiple Parent Task relations
- basic lifecycle-state inconsistencies

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
# Properties intentionally represented in the current Supabase POC schema
# ---------------------------------------------------------------------------

MAPPED_TASK_PROPERTIES = {
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
    "Project",
    "Parent Task",
    "Step Order",
}


MAPPED_PROJECT_PROPERTIES = {
    "Project Name",
    "Status",
    "Active",
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
        # False is still a meaningful stored value,
        # but for migration auditing we only count True
        # as materially populated.
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
        value = prop.get("formula", {})
        formula_type = value.get("type")

        if formula_type:
            return value.get(formula_type) is not None

        return bool(value)

    if prop_type == "rollup":
        return bool(prop.get("rollup"))

    if prop_type == "created_time":
        return bool(prop.get("created_time"))

    if prop_type == "last_edited_time":
        return bool(prop.get("last_edited_time"))

    if prop_type == "created_by":
        return bool(prop.get("created_by"))

    if prop_type == "last_edited_by":
        return bool(prop.get("last_edited_by"))

    # Unknown property types should be treated conservatively.
    return bool(prop.get(prop_type))


def relation_count(
    prop: dict[str, Any],
) -> int:
    if prop.get("type") != "relation":
        return 0

    return len(
        prop.get("relation", [])
    )


def page_title(
    page: dict[str, Any],
    title_property: str,
) -> str:
    prop = (
        page.get("properties", {})
        .get(title_property, {})
    )

    values = prop.get("title", [])

    text = "".join(
        item.get("plain_text", "")
        for item in values
    ).strip()

    return text or "(Untitled)"


# ---------------------------------------------------------------------------
# Generic database-property audit
# ---------------------------------------------------------------------------

def audit_properties(
    pages: list[dict[str, Any]],
    mapped_properties: set[str],
    title_property: str,
    label: str,
) -> None:

    types: dict[str, Counter[str]] = defaultdict(Counter)
    populated_counts: Counter[str] = Counter()
    presence_counts: Counter[str] = Counter()

    examples: dict[str, list[str]] = defaultdict(list)

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

                if len(examples[name]) < 3:
                    examples[name].append(title)

    property_names = sorted(
        presence_counts.keys()
    )

    print("\n" + "=" * 80)
    print(f"{label.upper()} PROPERTY AUDIT")
    print("=" * 80)

    print(
        f"Records examined: {len(pages)}"
    )

    print(
        f"Properties found: {len(property_names)}"
    )

    print("\nAll properties:")

    for name in property_names:
        mapped = (
            "MAPPED"
            if name in mapped_properties
            else "UNMAPPED"
        )

        type_text = ", ".join(
            f"{prop_type}:{count}"
            for prop_type, count
            in types[name].items()
        )

        print(
            f"  {mapped:8} "
            f"{name:<30} "
            f"populated={populated_counts[name]:>4} "
            f"present={presence_counts[name]:>4} "
            f"type={type_text}"
        )

    populated_unmapped = [
        name
        for name in property_names
        if (
            name not in mapped_properties
            and populated_counts[name] > 0
        )
    ]

    print("\nPopulated but currently unmapped:")

    if not populated_unmapped:
        print("  None")

    else:
        for name in populated_unmapped:
            print(
                f"  - {name}: "
                f"{populated_counts[name]} records"
            )

            for example in examples[name]:
                print(
                    f"      example: {example}"
                )


# ---------------------------------------------------------------------------
# Task-specific integrity checks
# ---------------------------------------------------------------------------

def audit_task_relationships(
    pages: list[dict[str, Any]],
) -> None:

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

    if multi_project:
        print(
            "\nWARNING: Multiple-project tasks:"
        )

        for title, count in multi_project[:20]:
            print(
                f"  - {title} ({count} projects)"
            )

        if len(multi_project) > 20:
            print(
                f"  ... plus "
                f"{len(multi_project) - 20} more"
            )

    if multi_parent:
        print(
            "\nWARNING: Multiple-parent tasks:"
        )

        for title, count in multi_parent[:20]:
            print(
                f"  - {title} ({count} parents)"
            )

        if len(multi_parent) > 20:
            print(
                f"  ... plus "
                f"{len(multi_parent) - 20} more"
            )


# ---------------------------------------------------------------------------
# Lifecycle consistency audit
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

    contradictions = []

    state_counts = Counter()

    for page in pages:
        props = page.get(
            "properties",
            {},
        )

        title = page_title(
            page,
            "Task Name",
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

        # This is the most obvious contradictory state.
        if is_open and is_done:
            contradictions.append(
                (
                    title,
                    is_open,
                    is_done,
                    is_archived,
                )
            )

    print("\n" + "=" * 80)
    print("TASK LIFECYCLE AUDIT")
    print("=" * 80)

    print(
        "Observed Open / Done / Archived combinations:"
    )

    for state, count in sorted(
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
        "\nOpen=True AND Done=True: "
        f"{len(contradictions)}"
    )

    if contradictions:
        print(
            "\nTasks with contradictory open/done state:"
        )

        for item in contradictions[:20]:
            print(
                f"  - {item[0]}"
            )

        if len(contradictions) > 20:
            print(
                f"  ... plus "
                f"{len(contradictions) - 20} more"
            )


# ---------------------------------------------------------------------------
# Migration readiness summary
# ---------------------------------------------------------------------------

def populated_unmapped_properties(
    pages: list[dict[str, Any]],
    mapped_properties: set[str],
) -> dict[str, int]:

    counts: Counter[str] = Counter()

    for page in pages:
        props = page.get(
            "properties",
            {},
        )

        for name, prop in props.items():

            if name in mapped_properties:
                continue

            if property_is_populated(prop):
                counts[name] += 1

    return dict(counts)


def count_multi_relations(
    pages: list[dict[str, Any]],
    property_name: str,
) -> int:

    return sum(
        1
        for page in pages
        if relation_count(
            page.get(
                "properties",
                {},
            ).get(
                property_name,
                {},
            )
        ) > 1
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:

    print("=" * 80)
    print("AIOS SUPABASE FULL-MIGRATION READINESS AUDIT")
    print("=" * 80)

    print(
        "\nREAD ONLY — no Notion or "
        "Supabase records will be changed."
    )

    print("\nReading Projects from Notion...")

    projects = query_database(
        PROJECTS_DATABASE_ID
    )

    print(
        f"Projects read: {len(projects)}"
    )

    print("\nReading Tasks from Notion...")

    tasks = query_database(
        TASKS_DATABASE_ID
    )

    print(
        f"Tasks read: {len(tasks)}"
    )

    audit_properties(
        projects,
        MAPPED_PROJECT_PROPERTIES,
        "Project Name",
        "Projects",
    )

    audit_properties(
        tasks,
        MAPPED_TASK_PROPERTIES,
        "Task Name",
        "Tasks",
    )

    audit_task_relationships(
        tasks
    )

    audit_task_lifecycle(
        tasks
    )

    task_unmapped = (
        populated_unmapped_properties(
            tasks,
            MAPPED_TASK_PROPERTIES,
        )
    )

    project_unmapped = (
        populated_unmapped_properties(
            projects,
            MAPPED_PROJECT_PROPERTIES,
        )
    )

    multi_project_count = (
        count_multi_relations(
            tasks,
            "Project",
        )
    )

    multi_parent_count = (
        count_multi_relations(
            tasks,
            "Parent Task",
        )
    )

    blockers = []

    if task_unmapped:
        blockers.append(
            "Tasks contain populated "
            "unmapped properties."
        )

    if project_unmapped:
        blockers.append(
            "Projects contain populated "
            "unmapped properties."
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
        f"Projects examined:       "
        f"{len(projects)}"
    )

    print(
        f"Tasks examined:          "
        f"{len(tasks)}"
    )

    print(
        f"Unmapped task fields:    "
        f"{len(task_unmapped)}"
    )

    print(
        f"Unmapped project fields: "
        f"{len(project_unmapped)}"
    )

    print(
        f"Multi-project tasks:     "
        f"{multi_project_count}"
    )

    print(
        f"Multi-parent tasks:      "
        f"{multi_parent_count}"
    )

    if blockers:
        print(
            "\nRESULT: REVIEW REQUIRED BEFORE "
            "FULL MIGRATION"
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
            "\nRESULT: SCHEMA READY FOR "
            "FULL MIGRATION"
        )


if __name__ == "__main__":
    main()