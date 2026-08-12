"""
Write one execution POC run and its task evaluations to Supabase
through TaskRepository + ExecutionRepository.

This script:
- reads the existing Supabase POC task sample through TaskRepository
- runs the current Execution Engine scoring logic
- persists the run through ExecutionRepository
- persists task evaluations through ExecutionRepository
- verifies the stored results

It does NOT modify Notion.
"""

from __future__ import annotations

from aios.storage.execution_repository import ExecutionRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository

from scripts.supabase_execution_parity import (
    get_open_tasks,
    rank_tasks_like_execution_engine,
    task_model_to_engine_task,
)


def main() -> None:
    print("=" * 72)
    print("AIOS SUPABASE REPOSITORY EVALUATION POC")
    print("=" * 72)

    store = SupabaseStore()
    task_repository = TaskRepository(store)
    execution_repository = ExecutionRepository(store)

    print("\nReading current POC tasks through TaskRepository...")

    tasks = task_repository.get_all_tasks()

    if not tasks:
        raise RuntimeError(
            "No POC tasks found in Supabase."
        )

    engine_tasks = [
        task_model_to_engine_task(task)
        for task in tasks
    ]

    open_tasks = get_open_tasks(
        engine_tasks
    )

    ranked = rank_tasks_like_execution_engine(
        open_tasks
    )

    print(f"POC tasks found:      {len(tasks)}")
    print(f"Open tasks:           {len(open_tasks)}")
    print(f"Eligible evaluations: {len(ranked)}")

    print("\nCreating AIOS run through ExecutionRepository...")

    run_id = execution_repository.create_run(
        "task_repository_execution_poc",
        tasks_scanned=len(open_tasks),
    )

    print(f"Run created: {run_id}")

    try:
        task_id_map = {
            task.legacy_notion_id: task.id
            for task in tasks
            if task.legacy_notion_id
        }

        evaluations = []

        for item in ranked:
            legacy_id = item["legacy_notion_id"]

            supabase_task_id = task_id_map.get(
                legacy_id
            )

            if not supabase_task_id:
                raise RuntimeError(
                    "Missing Supabase task mapping "
                    f"for {legacy_id}"
                )

            reasons = item.get("reasons") or []

            evaluations.append({
                "task_id": supabase_task_id,
                "execution_score": item["score"],
                "execution_rank": item["rank"],
                "is_execution_eligible": True,
                "eligible_quick_win": bool(
                    item["task"]
                    .get("properties", {})
                    .get("Quick Win", {})
                    .get("checkbox", False)
                ),
                "evaluation_reason": (
                    ", ".join(
                        str(reason)
                        for reason in reasons
                    )
                    or None
                ),
            })

        print(
            f"\nWriting {len(evaluations)} "
            "evaluations through ExecutionRepository..."
        )

        execution_repository.write_evaluations(
            run_id,
            evaluations,
        )

        execution_repository.complete_run(
            run_id
        )

    except Exception:
        execution_repository.fail_run(
            run_id
        )
        raise

    print("\nValidating repository results...")

    run = execution_repository.get_run(
        run_id
    )

    stored = execution_repository.get_run_evaluations(
        run_id
    )

    print("\n" + "=" * 72)
    print("REPOSITORY VALIDATION")
    print("=" * 72)

    print(
        f"Run status:           "
        f"{run['status'] if run else 'MISSING'}"
    )

    print(
        f"Expected evaluations: {len(ranked)}"
    )

    print(
        f"Stored evaluations:   {len(stored)}"
    )

    if not run:
        raise RuntimeError(
            "Run could not be read back."
        )

    if run["status"] != "completed":
        raise RuntimeError(
            f"Unexpected run status: {run['status']}"
        )

    if len(stored) != len(ranked):
        raise RuntimeError(
            "Evaluation count mismatch."
        )

    print("\nStored rankings:")

    for row in stored:
        print(
            f"  rank={row['execution_rank']:>2} "
            f"score={row['execution_score']} "
            f"quick_win={row['eligible_quick_win']} "
            f"task={row['task_id']}"
        )

    print(
        "\nRESULT: TASK + EXECUTION "
        "REPOSITORY POC SUCCESSFUL"
    )

    print(
        f"AIOS run ID: {run_id}"
    )


if __name__ == "__main__":
    main()