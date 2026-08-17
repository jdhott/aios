"""
Structural validation for Native Task Identity v1.

Run:
    python -m scripts.native_task_identity_v1_validate
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(label: str, condition: bool, failures: list[str]) -> None:
    if condition:
        print(f"PASS: {label}")
    else:
        print(f"FAIL: {label}")
        failures.append(label)


def main() -> None:
    metadata = (ROOT / "aios/storage/task_metadata_writer.py").read_text()
    lifecycle = (ROOT / "aios/storage/task_lifecycle_writer.py").read_text()
    execution = (ROOT / "aios/storage/execution_state_writer.py").read_text()

    failures: list[str] = []

    for label, source in [
        ("metadata writer accepts native identity", metadata),
        ("lifecycle writer accepts native identity", lifecycle),
        ("execution writer accepts native identity", execution),
    ]:
        check(
            label,
            "identity_map[task.id] = task.id" in source,
            failures,
        )

    check(
        "metadata keeps legacy compatibility",
        "identity_map[task.legacy_notion_id] = task.id" in metadata,
        failures,
    )
    check(
        "lifecycle keeps legacy compatibility",
        "identity_map[task.legacy_notion_id] = task.id" in lifecycle,
        failures,
    )
    check(
        "execution keeps legacy compatibility",
        "identity_map[task.legacy_notion_id] = task.id" in execution,
        failures,
    )
    check(
        "execution refreshes stale identity cache",
        "Same-process task creation" in execution
        and "self._identity_to_supabase_task_id = None" in execution,
        failures,
    )
    check(
        "metadata errors are source-neutral",
        "could not resolve task identity" in metadata
        and "could not map Notion task ID" not in metadata,
        failures,
    )
    check(
        "lifecycle errors are source-neutral",
        "could not resolve task identity" in lifecycle
        and "could not map Notion task ID" not in lifecycle,
        failures,
    )
    check(
        "execution errors are source-neutral",
        "Could not resolve task identity" in execution
        and "Could not map Notion task ID" not in execution,
        failures,
    )

    if failures:
        print("RESULT: NATIVE TASK IDENTITY V1 STRUCTURE VALIDATION FAILED")
        raise SystemExit(1)

    print("RESULT: NATIVE TASK IDENTITY V1 STRUCTURE VALID")


if __name__ == "__main__":
    main()
