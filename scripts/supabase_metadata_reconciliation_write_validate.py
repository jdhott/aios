"""
Read-only structural validation for metadata reconciliation write cutover.

Run:
    python -m scripts.supabase_metadata_reconciliation_write_validate
"""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]

    runtime = (
        root / "run_aios.py"
    ).read_text()

    reconciliation = (
        root
        / "core"
        / "metadata"
        / "reconciliation.py"
    ).read_text()

    checks = [
        (
            "execution writer constructed once",
            runtime.count(
                "execution_state_update_fn = build_execution_update_fn("
            )
            == 1,
        ),
        (
            "Quick Win writer constructed once",
            runtime.count(
                "quick_win_state_update_fn = build_quick_win_update_fn("
            )
            == 1,
        ),
        (
            "Execution Engine reuses canonical writer",
            "update_fn=execution_state_update_fn"
            in runtime,
        ),
        (
            "Quick Win refresh reuses canonical writer",
            "quick_win_update_fn = quick_win_state_update_fn"
            in runtime,
        ),
        (
            "reconciliation resolves runtime execution writer",
            '"execution_state_update_fn"'
            in reconciliation,
        ),
        (
            "reconciliation resolves runtime Quick Win writer",
            '"quick_win_state_update_fn"'
            in reconciliation,
        ),
        (
            "Supabase presentation cleanup delegates",
            "update_fn=quick_win_update_fn"
            in reconciliation,
        ),
        (
            "Supabase execution cleanup delegates",
            "update_fn=execution_update_fn"
            in reconciliation,
        ),
        (
            "Supabase rank rewrite delegates",
            "_apply_rank_actions_with_runtime_writer"
            in reconciliation,
        ),
        (
            "deprecated metadata diagnostic-only in Supabase",
            "Deprecated Notion-era metadata is diagnostic-only"
            in reconciliation,
        ),
        (
            "Supabase direct-Notion mutation guard marker present",
            "direct Notion task mutation disabled"
            in reconciliation,
        ),
    ]

    failed = [
        label
        for label, ok in checks
        if not ok
    ]

    for label, ok in checks:
        print(
            f"{'PASS' if ok else 'FAIL'}: "
            f"{label}"
        )

    if failed:
        print(
            "\nRESULT: METADATA RECONCILIATION "
            "WRITE CUTOVER VALIDATION FAILED"
        )
        for label in failed:
            print(
                f"  - {label}"
            )
        raise SystemExit(1)

    print(
        "\nRESULT: METADATA RECONCILIATION "
        "WRITE CUTOVER STRUCTURE VALID"
    )


if __name__ == "__main__":
    main()
