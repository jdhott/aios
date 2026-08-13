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


class ExecutionStatePrimaryWriter:
    """
    Transitional execution-state writer.

    When AIOS_DATASTORE=supabase:
      1. Supabase task_execution_state is updated first.
      2. The existing Notion update runs second as a temporary mirror.

    This establishes Supabase as the primary execution-state write target
    while retaining Notion for one more parity-validation stage.

    Fields handled here:
      - Execution Score
      - Execution Rank
      - Best Next Action (derived from rank when necessary)

    Surfaced Quick Win remains on the existing Notion reconciliation path
    for this stage.
    """

    def __init__(
        self,
        notion_update_fn: ExecutionUpdateFn,
    ):
        self.notion_update_fn = notion_update_fn

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
            "[Execution Primary Write] "
            f"Loaded task ID mappings: "
            f"{len(self._notion_to_supabase_task_id)}"
        )

    def _write_supabase(
        self,
        notion_task_id: str,
        properties: dict[str, Any],
    ) -> None:
        self._ensure_task_map()

        assert self._notion_to_supabase_task_id is not None

        supabase_task_id = self._notion_to_supabase_task_id.get(
            notion_task_id
        )

        if not supabase_task_id:
            raise RuntimeError(
                "Execution primary write could not map "
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
            self._write_supabase(
                notion_task_id,
                relevant,
            )

        # Temporary validation mirror. If this fails, the exception is
        # intentionally surfaced rather than silently accepting divergence.
        return self.notion_update_fn(
            notion_task_id,
            properties,
        )


def build_execution_update_fn(
    *,
    notion_update_fn: ExecutionUpdateFn,
    datastore: str,
) -> ExecutionUpdateFn:
    """
    notion:
        Original Notion-only behavior.

    supabase:
        Supabase primary execution-state write, followed by Notion mirror.
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
        "[Execution Primary Write] "
        "Supabase is primary execution-state write target; "
        "Notion remains temporary mirror"
    )

    return ExecutionStatePrimaryWriter(
        notion_update_fn
    )


class QuickWinPresentationPrimaryWriter:
    """
    Transitional Quick Win presentation writer.

    When AIOS_DATASTORE=supabase:
      - Surfaced Quick Win is written to Supabase first.
      - The complete original update is then mirrored to Notion.
      - The underlying Quick Win eligibility checkbox remains a Notion task
        field in this stage and is not written to task_execution_state.

    This lets task_execution_state become authoritative for the
    surfaced_quick_win presentation flag without changing unrelated task
    metadata yet.
    """

    def __init__(
        self,
        notion_update_fn: ExecutionUpdateFn,
    ):
        self.notion_update_fn = notion_update_fn

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
            "[Quick Win Primary Write] "
            f"Loaded task ID mappings: "
            f"{len(self._notion_to_supabase_task_id)}"
        )

    def _write_surfaced_quick_win(
        self,
        notion_task_id: str,
        value: bool,
    ) -> None:
        self._ensure_task_map()

        assert self._notion_to_supabase_task_id is not None

        supabase_task_id = self._notion_to_supabase_task_id.get(
            notion_task_id
        )

        if not supabase_task_id:
            raise RuntimeError(
                "Quick Win primary write could not map "
                f"Notion task ID {notion_task_id} to Supabase."
            )

        self._execution_repository.set_surfaced_quick_win(
            supabase_task_id,
            bool(value),
        )

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
            self._write_surfaced_quick_win(
                notion_task_id,
                bool(surfaced_value),
            )

        # Temporary validation mirror. This still carries any underlying
        # Quick Win eligibility change to Notion exactly as before.
        return self.notion_update_fn(
            notion_task_id,
            properties,
        )


def build_quick_win_update_fn(
    *,
    notion_update_fn: ExecutionUpdateFn,
    datastore: str,
) -> ExecutionUpdateFn:
    """
    notion:
        Original Notion-only Quick Win reconciliation behavior.

    supabase:
        Surfaced Quick Win -> Supabase first, then full Notion mirror.
        Underlying Quick Win eligibility remains Notion-backed for now.
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
        "[Quick Win Primary Write] "
        "Supabase is primary Surfaced Quick Win target; "
        "Notion remains temporary mirror"
    )

    return QuickWinPresentationPrimaryWriter(
        notion_update_fn
    )
