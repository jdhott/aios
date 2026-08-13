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

    # update_notion_page callers may sometimes pass the inner property body
    # without a Notion "type" key. Support that shape too.
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


class ExecutionStateDualWriter:
    """
    Temporary migration writer.

    Notion remains the existing write path.
    When AIOS_DATASTORE=supabase, execution-state mutations are mirrored into
    Supabase task_execution_state after the Notion update succeeds.

    This writer intentionally handles only execution-state fields:
      - Execution Score
      - Execution Rank
      - Best Next Action

    Surfaced Quick Win is still handled by its existing reconciliation path.
    """

    def __init__(
        self,
        notion_update_fn: ExecutionUpdateFn,
        *,
        mirror_to_supabase: bool,
    ):
        self.notion_update_fn = notion_update_fn
        self.mirror_to_supabase = mirror_to_supabase

        self._store = None
        self._task_repository = None
        self._execution_repository = None

        self._notion_to_supabase_task_id: dict[str, str] | None = None

    def _ensure_repositories(self) -> None:
        if self._store is not None:
            return

        self._store = SupabaseStore()
        self._task_repository = TaskRepository(self._store)
        self._execution_repository = ExecutionRepository(self._store)

    def _ensure_task_map(self) -> None:
        if self._notion_to_supabase_task_id is not None:
            return

        self._ensure_repositories()

        assert self._task_repository is not None

        tasks = self._task_repository.get_all_tasks()

        self._notion_to_supabase_task_id = {
            task.legacy_notion_id: task.id
            for task in tasks
            if task.legacy_notion_id
        }

        print(
            "[Execution Dual Write] "
            f"Loaded task ID mappings: "
            f"{len(self._notion_to_supabase_task_id)}"
        )

    def _mirror(
        self,
        notion_task_id: str,
        properties: dict[str, Any],
    ) -> None:
        self._ensure_task_map()

        assert self._notion_to_supabase_task_id is not None
        assert self._execution_repository is not None

        supabase_task_id = self._notion_to_supabase_task_id.get(
            notion_task_id
        )

        if not supabase_task_id:
            raise RuntimeError(
                "Execution dual-write could not map "
                f"Notion task ID {notion_task_id} to Supabase."
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
            properties,
            "Execution Score",
        )

        rank, has_rank = _extract_number_property(
            properties,
            "Execution Rank",
        )

        bna, has_bna = _extract_checkbox_property(
            properties,
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

    def __call__(
        self,
        notion_task_id: str,
        properties: dict[str, Any],
    ):
        result = self.notion_update_fn(
            notion_task_id,
            properties,
        )

        if not self.mirror_to_supabase:
            return result

        relevant = {
            key: value
            for key, value in properties.items()
            if key in {
                "Execution Score",
                "Execution Rank",
                "Best Next Action",
            }
        }

        if relevant:
            self._mirror(
                notion_task_id,
                relevant,
            )

        return result


def build_execution_update_fn(
    *,
    notion_update_fn: ExecutionUpdateFn,
    datastore: str,
) -> ExecutionUpdateFn:
    """
    Return the execution update callback used by Execution Engine V2.

    notion:
        original Notion-only behavior

    supabase:
        Notion write first, then mirror execution state into Supabase
    """

    normalized = (
        datastore
        .strip()
        .lower()
    )

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
        "[Execution Dual Write] "
        "Notion remains primary write target; "
        "mirroring execution state to Supabase"
    )

    return ExecutionStateDualWriter(
        notion_update_fn,
        mirror_to_supabase=True,
    )
