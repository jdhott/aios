"""
Validate the fully Supabase-backed execution and Quick Win state.

READ ONLY.

Run:
    python -m scripts.supabase_execution_pipeline_validate
"""

from __future__ import annotations

from aios.storage.execution_repository import ExecutionRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


def main() -> None:
    print("=" * 72)
    print("AIOS SUPABASE EXECUTION PIPELINE VALIDATION")
    print("=" * 72)
    print("\nREAD ONLY.")

    store = SupabaseStore()
    execution_repo = ExecutionRepository(store)
    task_repo = TaskRepository(store)

    state = execution_repo.get_current_state()
    tasks = task_repo.get_all_tasks()

    tasks_by_id = {
        task.id: task
        for task in tasks
    }

    ranked = [
        row
        for row in state.values()
        if row.get("execution_rank") is not None
    ]
    ranked.sort(key=lambda row: row["execution_rank"])

    ranks = [
        int(row["execution_rank"])
        for row in ranked
    ]

    bna_ids = {
        row["task_id"]
        for row in state.values()
        if bool(row.get("best_next_action", False))
    }

    surfaced_ids = {
        row["task_id"]
        for row in state.values()
        if bool(row.get("surfaced_quick_win", False))
    }

    quick_win_ids = {
        task.id
        for task in tasks
        if task.is_quick_win
    }

    expected_bna_ids = {
        row["task_id"]
        for row in ranked
        if int(row["execution_rank"]) <= 5
    }

    failures = []

    if len(state) != 15:
        failures.append(
            f"Expected 15 current execution-state rows; found {len(state)}"
        )

    if len(ranked) != 10:
        failures.append(
            f"Expected 10 ranked rows; found {len(ranked)}"
        )

    if ranks != list(range(1, 11)):
        failures.append(
            f"Execution ranks are not canonical 1..10: {ranks}"
        )

    if bna_ids != expected_bna_ids:
        failures.append(
            "BNA state does not exactly match ranks 1..5"
        )

    if len(surfaced_ids) != 5:
        failures.append(
            f"Expected 5 Surfaced Quick Wins; found {len(surfaced_ids)}"
        )

    bna_quick_win_overlap = bna_ids & quick_win_ids

    if bna_quick_win_overlap:
        failures.append(
            "BNA tasks still marked Quick Win: "
            f"{len(bna_quick_win_overlap)}"
        )

    surfaced_not_quick_win = surfaced_ids - quick_win_ids

    if surfaced_not_quick_win:
        failures.append(
            "Surfaced Quick Wins missing Quick Win eligibility: "
            f"{len(surfaced_not_quick_win)}"
        )

    missing_state_tasks = [
        task_id
        for task_id in (bna_ids | surfaced_ids)
        if task_id not in tasks_by_id
    ]

    if missing_state_tasks:
        failures.append(
            f"Execution state references missing tasks: "
            f"{len(missing_state_tasks)}"
        )

    missing_scores = [
        row["task_id"]
        for row in ranked
        if row.get("execution_score") is None
    ]

    if missing_scores:
        failures.append(
            f"Ranked rows missing scores: {len(missing_scores)}"
        )

    print(f"\nCurrent execution-state rows: {len(state)}")
    print(f"Ranked execution rows:        {len(ranked)}")
    print(f"Best Next Actions:            {len(bna_ids)}")
    print(f"Surfaced Quick Wins:          {len(surfaced_ids)}")
    print(f"Quick Win eligible tasks:     {len(quick_win_ids)}")
    print(f"BNA / Quick Win overlap:      {len(bna_quick_win_overlap)}")
    print(f"Surfaced not Quick Win:       {len(surfaced_not_quick_win)}")
    print(f"Ranked rows missing score:    {len(missing_scores)}")
    print(f"Rank sequence:                {ranks}")

    if failures:
        print("\nRESULT: SUPABASE EXECUTION PIPELINE VALIDATION FAILED")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)

    print("\nRESULT: SUPABASE EXECUTION PIPELINE IS CLEAN")


if __name__ == "__main__":
    main()
