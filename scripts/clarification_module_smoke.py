#!/usr/bin/env python3
"""
Offline smoke test for the canonical clarification module.

No Notion or Supabase network requests are made.
"""
from __future__ import annotations

from datetime import date

from aios import clarification as clarification


def main() -> None:
    lifecycle_calls = []
    metadata_calls = []
    errors = []

    def fake_increment(key, amount=1):
        errors.append((key, amount))

    def fake_lifecycle(
        page_id,
        properties,
        *,
        datastore,
        notion_update_fn,
    ):
        lifecycle_calls.append(
            (page_id, properties, datastore)
        )
        return {
            "id": page_id,
            "properties": dict(properties),
            "_source": datastore,
        }

    def fake_metadata(
        task,
        properties,
        *,
        datastore,
        notion_update_fn,
    ):
        metadata_calls.append(
            (task["id"], properties, datastore)
        )
        updated = dict(task)
        merged = dict(task.get("properties", {}))
        merged.update(properties)
        updated["properties"] = merged
        return updated

    def forbidden_notion_write(*args, **kwargs):
        raise AssertionError(
            "Direct Notion page write should not be used by "
            "datastore-aware clarification state updates."
        )

    clarification.configure_clarification_module(
        {
            "READY_STATUS": "Ready",
            "CLARIFY_STATUS": "Needs Clarification",
            "AIOS_DATASTORE": "supabase",
            "update_task_lifecycle": fake_lifecycle,
            "update_task_metadata": fake_metadata,
            "update_notion_page": forbidden_notion_write,
            "increment_summary": fake_increment,
        }
    )

    result = clarification.update_task_from_selection(
        "legacy-notion-task-1",
        "Write detailed canning list",
        is_jdi=False,
        is_urgent=True,
        is_important=True,
        due_date=date(2026, 8, 20),
    )

    if not result:
        raise RuntimeError(
            "Selection update returned no task"
        )

    if len(lifecycle_calls) != 1:
        raise RuntimeError(
            f"Expected one lifecycle call, got {len(lifecycle_calls)}"
        )

    if len(metadata_calls) != 1:
        raise RuntimeError(
            f"Expected one metadata call, got {len(metadata_calls)}"
        )

    if lifecycle_calls[0][2] != "supabase":
        raise RuntimeError(
            "Lifecycle update did not use Supabase"
        )

    if metadata_calls[0][2] != "supabase":
        raise RuntimeError(
            "Metadata update did not use Supabase"
        )

    clarification.update_clarification_title(
        "legacy-notion-task-2",
        "Choose preserving foods",
    )

    if len(lifecycle_calls) != 2:
        raise RuntimeError(
            "Clarification-title update did not use lifecycle writer"
        )

    if errors:
        raise RuntimeError(
            f"Unexpected error-summary increments: {errors}"
        )

    print(
        "Datastore-aware selection update: PASS"
    )
    print(
        "Datastore-aware clarification-title update: PASS"
    )
    print(
        "Direct Notion page mutation not invoked: PASS"
    )
    print(
        "RESULT: CLARIFICATION MODULE CONSOLIDATION "
        "SMOKE TEST PASSED"
    )


if __name__ == "__main__":
    main()
