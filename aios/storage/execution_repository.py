from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from aios.storage.supabase_store import SupabaseStore


class ExecutionRepository:
    """
    Persistence layer for AIOS execution runs, historical evaluations,
    and current mutable execution state.
    """

    def __init__(self, store: SupabaseStore):
        self.store = store

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Historical evaluations
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Current execution state
    # ------------------------------------------------------------------

    def get_current_state(
        self,
    ) -> dict[str, dict[str, Any]]:
        """
        Return current execution state indexed by Supabase task UUID.

        Shape:

            {
                task_id: {
                    "execution_score": ...,
                    "execution_rank": ...,
                    "best_next_action": ...,
                    "surfaced_quick_win": ...,
                    "last_run_id": ...,
                    "updated_at": ...,
                }
            }
        """

        rows: list[dict[str, Any]] = []

        page_size = 1000
        start = 0

        while True:
            response = (
                self.store.client
                .table("task_execution_state")
                .select("*")
                .order("task_id")
                .range(
                    start,
                    start + page_size - 1,
                )
                .execute()
            )

            batch = response.data or []

            rows.extend(batch)

            if len(batch) < page_size:
                break

            start += page_size

        return {
            row["task_id"]: row
            for row in rows
            if row.get("task_id")
        }

    def get_current_state_for_task(
        self,
        task_id: str,
    ) -> Optional[dict[str, Any]]:
        response = (
            self.store.client
            .table("task_execution_state")
            .select("*")
            .eq("task_id", task_id)
            .limit(1)
            .execute()
        )

        rows = response.data or []

        return rows[0] if rows else None

    def upsert_current_state(
        self,
        states: list[dict[str, Any]],
        *,
        run_id: Optional[str] = None,
    ) -> None:
        """
        Upsert current execution state for one or more tasks.

        Each state requires:
            task_id

        Optional:
            execution_score
            execution_rank
            best_next_action
            surfaced_quick_win

        last_run_id is populated from run_id when supplied.
        """

        if not states:
            return

        now = datetime.now(
            timezone.utc
        ).isoformat()

        rows = []

        for state in states:
            task_id = state.get("task_id")

            if not task_id:
                raise ValueError(
                    "Current execution state requires task_id."
                )

            row = {
                "task_id": task_id,
                "execution_score":
                    state.get("execution_score"),
                "execution_rank":
                    state.get("execution_rank"),
                "best_next_action":
                    bool(
                        state.get(
                            "best_next_action",
                            False,
                        )
                    ),
                "surfaced_quick_win":
                    bool(
                        state.get(
                            "surfaced_quick_win",
                            False,
                        )
                    ),
                "updated_at": now,
            }

            if run_id is not None:
                row["last_run_id"] = run_id

            rows.append(row)

        (
            self.store.client
            .table("task_execution_state")
            .upsert(
                rows,
                on_conflict="task_id",
            )
            .execute()
        )

    def clear_execution_state(
        self,
        task_ids: list[str],
        *,
        run_id: Optional[str] = None,
    ) -> None:
        """
        Clear execution score/rank/BNA for the supplied tasks.

        Surfaced Quick Win is intentionally preserved because it is a
        separate presentation overlay and may be reconciled independently.
        """

        if not task_ids:
            return

        values: dict[str, Any] = {
            "execution_score": None,
            "execution_rank": None,
            "best_next_action": False,
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        if run_id is not None:
            values["last_run_id"] = run_id

        (
            self.store.client
            .table("task_execution_state")
            .update(values)
            .in_(
                "task_id",
                task_ids,
            )
            .execute()
        )

    def set_surfaced_quick_win(
        self,
        task_id: str,
        value: bool,
        *,
        run_id: Optional[str] = None,
    ) -> None:
        """
        Set the current Surfaced Quick Win state for one task.
        """

        row: dict[str, Any] = {
            "task_id": task_id,
            "surfaced_quick_win": bool(value),
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        if run_id is not None:
            row["last_run_id"] = run_id

        (
            self.store.client
            .table("task_execution_state")
            .upsert(
                row,
                on_conflict="task_id",
            )
            .execute()
        )