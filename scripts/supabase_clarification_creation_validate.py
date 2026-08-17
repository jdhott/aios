"""Read-only structural validation for Supabase-primary clarification creation."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    runtime = (root / "run_aios.py").read_text()
    review_service = (root / "aios/services/review_service.py").read_text()

    clarify_branch = runtime[
        runtime.index('elif decision == "clarify":'):
        runtime.index('    else:', runtime.index('elif decision == "clarify":'))
    ]

    dispatcher_start = runtime.index("def create_notion_task(")
    dispatcher_end = runtime.index("def create_and_update_task(", dispatcher_start)
    dispatcher = runtime[dispatcher_start:dispatcher_end]

    checks = [
        ("clarification branch requests Supabase-primary creation",
         "supabase_primary=True" in clarify_branch),
        ("dispatcher no longer excludes clarification tasks",
         "and not is_clarification" not in dispatcher),
        ("top-level Supabase-primary guard remains",
         'AIOS_DATASTORE == "supabase"' in dispatcher
         and "parent_task_id is None" in dispatcher
         and "step_order is None" in dispatcher),
        ("temporary Notion mirror remains general creation compatibility",
         "notion_create_fn=_create_notion_task_only" in dispatcher),
        ("Notion rollback remains general creation compatibility",
         "notion_rollback_fn=update_notion_page" in dispatcher),
        ("clarification review is created after authoritative task creation",
         "maybe_create_clarification_review(" in runtime
         and "create_clarification_review(" in runtime),
        ("clarification review requires authoritative Supabase task id",
         'first_page.get("_supabase_id")' in runtime
         and "Clarification task has no authoritative" in runtime),
        ("accepted clarification updates authoritative task directly",
         "def resolve_clarification(" in review_service
         and "self.task_repository.update_task(" in review_service
         and '"status": "Ready"' in review_service),
        ("accepted clarification resolves review without rerouting classifier",
         "resolve_clarification_review(" in review_service),
    ]

    failed = [label for label, ok in checks if not ok]

    for label, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {label}")

    if failed:
        print("\nRESULT: CLARIFICATION CREATION CUTOVER VALIDATION FAILED")
        for label in failed:
            print(f"  - {label}")
        raise SystemExit(1)

    print("\nRESULT: CLARIFICATION CREATION CUTOVER STRUCTURE VALID")


if __name__ == "__main__":
    main()
