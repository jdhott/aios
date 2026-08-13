"""
Validate current Supabase execution state after a Supabase-only AIOS run.

READ ONLY.

Run:
    python -m scripts.supabase_execution_state_validate
"""

from __future__ import annotations

from aios.storage.execution_repository import ExecutionRepository
from aios.storage.supabase_store import SupabaseStore


def main() -> None:
    print("=" * 72)
    print("AIOS SUPABASE CURRENT EXECUTION-STATE VALIDATION")
    print("=" * 72)
    print("\nREAD ONLY.")

    repo = ExecutionRepository(
        SupabaseStore()
    )

    state = repo.get_current_state()

    ranked = [
        row
        for row in state.values()
        if row.get("execution_rank") is not None
    ]

    ranked.sort(
        key=lambda row: row["execution_rank"]
    )

    ranks = [
        int(row["execution_rank"])
        for row in ranked
    ]

    bna = [
        row
        for row in state.values()
        if bool(row.get("best_next_action", False))
    ]

    surfaced = [
        row
        for row in state.values()
        if bool(row.get("surfaced_quick_win", False))
    ]

    ranked_ids = {
        row["task_id"]
        for row in ranked
    }

    bna_ids = {
        row["task_id"]
        for row in bna
    }

    surfaced_ids = {
        row["task_id"]
        for row in surfaced
    }

    expected_bna_ids = {
        row["task_id"]
        for row in ranked
        if int(row["execution_rank"]) <= 5
    }

    failures = []

    if len(state) != 15:
        failures.append(
            f"Expected 15 current-state rows; found {len(state)}"
        )

    if len(ranked) != 10:
        failures.append(
            f"Expected 10 ranked rows; found {len(ranked)}"
        )

    if ranks != list(range(1, 11)):
        failures.append(
            f"Execution ranks are not canonical 1..10: {ranks}"
        )

    if len(bna) != 5:
        failures.append(
            f"Expected 5 BNAs; found {len(bna)}"
        )

    if bna_ids != expected_bna_ids:
        failures.append(
            "BNA state does not exactly match ranks 1..5"
        )

    if len(surfaced) != 5:
        failures.append(
            f"Expected 5 Surfaced Quick Wins; found {len(surfaced)}"
        )

    overlap = bna_ids & surfaced_ids

    if overlap:
        failures.append(
            f"BNA / Surfaced Quick Win overlap found: {len(overlap)}"
        )

    missing_scores = [
        row["task_id"]
        for row in ranked
        if row.get("execution_score") is None
    ]

    if missing_scores:
        failures.append(
            f"Ranked rows missing execution scores: {len(missing_scores)}"
        )

    print(f"\nCurrent state rows:        {len(state)}")
    print(f"Ranked execution rows:     {len(ranked)}")
    print(f"Best Next Actions:         {len(bna)}")
    print(f"Surfaced Quick Wins:       {len(surfaced)}")
    print(f"BNA / Quick Win overlap:   {len(overlap)}")
    print(f"Ranked rows missing score: {len(missing_scores)}")
    print(f"Rank sequence:             {ranks}")

    if failures:
        print("\nRESULT: SUPABASE EXECUTION STATE VALIDATION FAILED")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)

    print("\nRESULT: SUPABASE EXECUTION STATE IS CLEAN")


if __name__ == "__main__":
    main()
