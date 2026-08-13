from __future__ import annotations

from typing import Any, Callable

from aios.storage.execution_repository import ExecutionRepository
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_repository import TaskRepository


ExecutionUpdateFn = Callable[[str, dict[str, Any]], Any]


def _extract_number_property(
    properties: dict[str, Any],
    name: str,
):
    prop = properties.get(name)

    if not isinstance(prop, dict):
        return None, False

    if prop.get("type") == "number":
        return prop.get("number"), True

    if "number" in prop:
        return prop.get("number"), True

    return None, False


def _extract_checkbox_property(
    properties: dict[str, Any],
    name: str,
):
    prop = properties.get(name)

    if not isinstance(prop, dict):
        return None, False

    if prop.get("type") == "checkbox":
        return bool(prop.get("checkbox")), True

    if "checkbox" in prop:
        return bool(prop.get("checkbox")), True

    return None, False


class _SupabaseExecutionStateBase:
    def __init__(self):
        self._store = SupabaseStore()
        self._task_repository = TaskRepository(self._store)
        self._execution_repository = ExecutionRepository(self._store)
        self._notion_to_supabase_task_id: dict[str, str] | None = None

    def _ensure_task_map(self) -> None:
        if self._notion_to_supabase_task_id is not None:
            return

        tasks = self._task_repository.get_all_tasks()

        self._notion_to_supabase_task_id = {
            task.legacy_notion_id: task.id
            for task in tasks
            if task.legacy_notion_id
        }

        print(
            "[Supabase Execution Write] "
            f"Loaded task ID mappings: "
            f"{len(self._notion_to_supabase_task_id)}"
        )

    def _supabase_task_id(
        self,
        notion_task_id: str,
    ) -> str:
        self._ensure_task_map()

        assert self._notion_to_supabase_task_id is not None

        task_id = self._notion_to_supabase_task_id.get(
            notion_task_id
        )

        if not task_id:
            raise RuntimeError(
                "Could not map Notion task ID "
                f"{notion_task_id} to Supabase."
            )

        return task_id


class ExecutionStateSupabaseWriter(_SupabaseExecutionStateBase):
    """
    Supabase-only execution-state writer.

    When AIOS_DATASTORE=supabase, Execution Engine V2 writes current
    execution state only to task_execution_state.

    Notion is NOT updated for:
      - Execution Score
      - Execution Rank
      - Best Next Action
    """

    def __call__(
        self,
        notion_task_id: str,
        properties: dict[str, Any],
    ):
        relevant = {
            key: value
            for key, value in properties.items()
            if key in {
                "Execution Score",
                "Execution Rank",
                "Best Next Action",
            }
        }

        if not relevant:
            return None

        supabase_task_id = self._supabase_task_id(
            notion_task_id
        )

        current = (
            self._execution_repository.get_current_state_for_task(
                supabase_task_id
            )
            or {}
        )

        state = {
            "task_id": supabase_task_id,
            "execution_score": current.get("execution_score"),
            "execution_rank": current.get("execution_rank"),
            "best_next_action": bool(
                current.get("best_next_action", False)
            ),
            "surfaced_quick_win": bool(
                current.get("surfaced_quick_win", False)
            ),
        }

        score, has_score = _extract_number_property(
            relevant,
            "Execution Score",
        )

        rank, has_rank = _extract_number_property(
            relevant,
            "Execution Rank",
        )

        bna, has_bna = _extract_checkbox_property(
            relevant,
            "Best Next Action",
        )

        if has_score:
            state["execution_score"] = score

        if has_rank:
            state["execution_rank"] = rank

        if has_bna:
            state["best_next_action"] = bool(bna)
        elif has_rank:
            state["best_next_action"] = (
                rank is not None
                and rank <= 5
            )

        self._execution_repository.upsert_current_state(
            [state]
        )

        return None


def build_execution_update_fn(
    *,
    notion_update_fn: ExecutionUpdateFn,
    datastore: str,
) -> ExecutionUpdateFn:
    """
    notion:
        Original Notion-only execution-state behavior.

    supabase:
        Supabase-only execution-state writes.
    """

    normalized = datastore.strip().lower()

    if normalized not in {
        "notion",
        "supabase",
    }:
        raise ValueError(
            "datastore must be 'notion' or 'supabase'"
        )

    if normalized == "notion":
        return notion_update_fn

    print(
        "[Execution State Write] "
        "Supabase-only execution-state writes active; "
        "Notion execution-state mirror disabled"
    )

    return ExecutionStateSupabaseWriter()


class QuickWinSupabaseWriter(_SupabaseExecutionStateBase):
    """
    Supabase-primary Quick Win presentation writer.

    Surfaced Quick Win is written ONLY to Supabase.

    The underlying Quick Win eligibility checkbox is still task metadata
    that has not yet been migrated to a Supabase write path. If the
    reconciliation needs to clear Quick Win on a BNA overlap, that one
    task-metadata mutation is still sent to Notion.

    Therefore this class removes the Notion *execution-state* mirror while
    preserving the separate, not-yet-migrated Quick Win task-metadata write.
    """

    def __init__(
        self,
        notion_update_fn: ExecutionUpdateFn,
    ):
        super().__init__()
        self.notion_update_fn = notion_update_fn

    def __call__(
        self,
        notion_task_id: str,
        properties: dict[str, Any],
    ):
        surfaced_value, has_surfaced = _extract_checkbox_property(
            properties,
            "Surfaced Quick Win",
        )

        if has_surfaced:
            supabase_task_id = self._supabase_task_id(
                notion_task_id
            )

            self._execution_repository.set_surfaced_quick_win(
                supabase_task_id,
                bool(surfaced_value),
            )

        # Quick Win itself is eligibility/task metadata, not current
        # execution-state. Keep that isolated Notion mutation until task
        # metadata writes are migrated.
        quick_win_property = properties.get("Quick Win")

        if isinstance(quick_win_property, dict):
            return self.notion_update_fn(
                notion_task_id,
                {
                    "Quick Win": quick_win_property,
                },
            )

        return None


def build_quick_win_update_fn(
    *,
    notion_update_fn: ExecutionUpdateFn,
    datastore: str,
) -> ExecutionUpdateFn:
    """
    notion:
        Original Notion-only Quick Win reconciliation.

    supabase:
        Surfaced Quick Win -> Supabase only.
        Quick Win eligibility -> Notion only, if a mutation is required.
    """

    normalized = datastore.strip().lower()

    if normalized not in {
        "notion",
        "supabase",
    }:
        raise ValueError(
            "datastore must be 'notion' or 'supabase'"
        )

    if normalized == "notion":
        return notion_update_fn

    print(
        "[Quick Win State Write] "
        "Surfaced Quick Win writes are Supabase-only; "
        "underlying Quick Win eligibility remains Notion-backed"
    )

    return QuickWinSupabaseWriter(
        notion_update_fn
    )
