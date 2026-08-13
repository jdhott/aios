"""
Offline smoke test for metadata reconciliation datastore routing.

NO network or production database writes are performed.

The test invokes the private datastore-routing helpers with fake runtime
writers and proves:
- Quick Win cleanup reaches only the Quick Win writer.
- execution cleanup reaches only the execution writer.
- canonical rank assignment reaches only the execution writer.
- legacy direct-Notion functions are not needed for Supabase routing.

Run:
    python -m scripts.supabase_metadata_reconciliation_write_smoke
"""

from __future__ import annotations

from core.metadata.reconciliation import (
    _apply_actions_with_runtime_writer,
    _apply_rank_actions_with_runtime_writer,
)


def main() -> None:
    quick_calls = []
    execution_calls = []

    def fake_quick(
        page_id,
        properties,
    ):
        quick_calls.append(
            (
                page_id,
                properties,
            )
        )

    def fake_execution(
        page_id,
        properties,
    ):
        execution_calls.append(
            (
                page_id,
                properties,
            )
        )

    presentation_actions = [
        {
            "page_id":
                "notion-task-1",
            "title":
                "Deferred task",
            "properties": {
                "Quick Win": {
                    "checkbox":
                        False,
                }
            },
        }
    ]

    execution_actions = [
        {
            "page_id":
                "notion-task-2",
            "title":
                "Closed task",
            "properties": {
                "Execution Score": {
                    "number":
                        None,
                },
                "Execution Rank": {
                    "number":
                        None,
                },
                "Best Next Action": {
                    "checkbox":
                        False,
                },
            },
        }
    ]

    rank_actions = [
        {
            "page_id":
                "notion-task-3",
            "title":
                "Ranked task A",
            "new_rank":
                1,
        },
        {
            "page_id":
                "notion-task-4",
            "title":
                "Ranked task B",
            "new_rank":
                2,
        },
    ]

    updated, errors = (
        _apply_actions_with_runtime_writer(
            presentation_actions,
            update_fn=fake_quick,
        )
    )

    if updated != 1 or errors:
        raise RuntimeError(
            "Quick Win routing failed."
        )

    updated, errors = (
        _apply_actions_with_runtime_writer(
            execution_actions,
            update_fn=fake_execution,
        )
    )

    if updated != 1 or errors:
        raise RuntimeError(
            "Execution cleanup routing failed."
        )

    updated, errors = (
        _apply_rank_actions_with_runtime_writer(
            rank_actions,
            update_fn=fake_execution,
        )
    )

    if updated != 2 or errors:
        raise RuntimeError(
            "Rank routing failed."
        )

    if quick_calls != [
        (
            "notion-task-1",
            {
                "Quick Win": {
                    "checkbox":
                        False,
                }
            },
        )
    ]:
        raise RuntimeError(
            "Quick Win writer received unexpected calls."
        )

    if execution_calls[0] != (
        "notion-task-2",
        {
            "Execution Score": {
                "number":
                    None,
            },
            "Execution Rank": {
                "number":
                    None,
            },
            "Best Next Action": {
                "checkbox":
                    False,
            },
        },
    ):
        raise RuntimeError(
            "Execution cleanup writer received unexpected payload."
        )

    expected_rank_calls = [
        (
            "notion-task-3",
            {
                "Execution Rank": {
                    "number":
                        1,
                }
            },
        ),
        (
            "notion-task-4",
            {
                "Execution Rank": {
                    "number":
                        2,
                }
            },
        ),
    ]

    if execution_calls[1:] != expected_rank_calls:
        raise RuntimeError(
            "Rank writer received unexpected calls."
        )

    print(
        "Quick Win reconciliation routing: PASS"
    )
    print(
        "Execution cleanup routing: PASS"
    )
    print(
        "Canonical rank routing: PASS"
    )
    print(
        "No network or Notion mutation path invoked."
    )

    print(
        "\nRESULT: METADATA RECONCILIATION "
        "WRITE SMOKE TEST PASSED"
    )


if __name__ == "__main__":
    main()
