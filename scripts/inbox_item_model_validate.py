#!/usr/bin/env python3
import ast
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[1]
    run_text = (root / "run_aios.py").read_text()
    model_text = (root / "aios" / "ingestion" / "models.py").read_text()

    checks = [
        ("InboxItem model exists", "class InboxItem(" in model_text),
        (
            "InboxItem is Mapping-compatible",
            "Mapping[str, Any]" in model_text
            and "def __getitem__" in model_text
            and "def __iter__" in model_text,
        ),
        (
            "legacy Brain Dump keys are preserved",
            all(
                key in model_text
                for key in ['"block_id"', '"block_type"', '"parent_block_id"']
            ),
        ),
        (
            "runtime imports InboxItem",
            "from aios.ingestion.models import InboxItem" in run_text,
        ),
        (
            "Notion extractor constructs InboxItem",
            'source="notion"' in run_text and "InboxItem(" in run_text,
        ),
        (
            "legacy dictionary append removed",
            '"parent_block_id": synced_block_id' not in run_text,
        ),
        (
            "source-neutral fields are populated",
            "source_item_id=block_id" in run_text
            and "source_container_id=synced_block_id" in run_text
            and "source_type=block_type" in run_text,
        ),
    ]

    ast.parse(run_text)
    ast.parse(model_text)

    for label, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {label}")

    if not all(ok for _, ok in checks):
        print("\nRESULT: INBOX ITEM MODEL CUTOVER VALIDATION FAILED")
        raise SystemExit(1)

    print("\nRESULT: INBOX ITEM MODEL CUTOVER STRUCTURE VALID")

if __name__ == "__main__":
    main()
