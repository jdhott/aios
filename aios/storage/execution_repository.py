from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from aios.storage.supabase_store import SupabaseStore


class ExecutionRepository:
    """
    Persistence layer for AIOS execution runs and task evaluations.

    AIOS execution logic should use this repository rather than
    accessing the Supabase tables directly.
    """

    def __init__(self, store: SupabaseStore):
        self.store = store

    def create_run(
        self,
        run_type: str,
        *,
        tasks_scanned: Optional[int] = None,
        version: Optional[str] = None,
        git_commit: Optional[str] = None,
    ) -> str:
        response = (
            self.store.client
            .table("aios_runs")
            .insert({
                "run_type": run_type,
                "status": "running",
                "version": version,
                "git_commit": git_commit,
                "started_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "tasks_scanned": tasks_scanned,
                "error_count": 0,
            })
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Failed to create AIOS run."
            )

        return response.data[0]["id"]

    def complete_run(
        self,
        run_id: str,
        *,
        tasks_created: Optional[int] = None,
        projects_created: Optional[int] = None,
    ) -> None:
        values: dict[str, Any] = {
            "status": "completed",
            "completed_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        if tasks_created is not None:
            values["tasks_created"] = tasks_created

        if projects_created is not None:
            values["projects_created"] = projects_created

        (
            self.store.client
            .table("aios_runs")
            .update(values)
            .eq("id", run_id)
            .execute()
        )

    def fail_run(
        self,
        run_id: str,
        *,
        error_count: int = 1,
    ) -> None:
        (
            self.store.client
            .table("aios_runs")
            .update({
                "status": "failed",
                "completed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "error_count": error_count,
            })
            .eq("id", run_id)
            .execute()
        )

    def write_evaluations(
        self,
        run_id: str,
        evaluations: list[dict[str, Any]],
    ) -> None:
        if not evaluations:
            return

        rows = []

        for evaluation in evaluations:
            rows.append({
                "task_id":
                    evaluation["task_id"],

                "aios_run_id":
                    run_id,

                "execution_score":
                    evaluation.get(
                        "execution_score"
                    ),

                "execution_rank":
                    evaluation.get(
                        "execution_rank"
                    ),

                "is_execution_eligible":
                    evaluation.get(
                        "is_execution_eligible",
                        True,
                    ),

                "eligible_quick_win":
                    evaluation.get(
                        "eligible_quick_win",
                        False,
                    ),

                "evaluation_reason":
                    evaluation.get(
                        "evaluation_reason"
                    ),
            })

        (
            self.store.client
            .table("task_evaluations")
            .insert(rows)
            .execute()
        )

    def get_run(
        self,
        run_id: str,
    ) -> Optional[dict[str, Any]]:
        response = (
            self.store.client
            .table("aios_runs")
            .select("*")
            .eq("id", run_id)
            .limit(1)
            .execute()
        )

        rows = response.data or []

        return rows[0] if rows else None

    def get_run_evaluations(
        self,
        run_id: str,
    ) -> list[dict[str, Any]]:
        response = (
            self.store.client
            .table("task_evaluations")
            .select("*")
            .eq("aios_run_id", run_id)
            .order("execution_rank")
            .execute()
        )

        return response.data or []