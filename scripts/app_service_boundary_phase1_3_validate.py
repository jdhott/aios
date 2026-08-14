#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
model = (root / "aios/ingestion/models.py").read_text()
repo = (root / "aios/storage/inbox_repository.py").read_text()
source = (root / "aios/ingestion/supabase_source.py").read_text()
run = (root / "run_aios.py").read_text()

for text in (model, repo, source, run):
    ast.parse(text)

checks = [
    (
        "InboxItem has durable inbox_row_id",
        "inbox_row_id: str | None = None" in model,
    ),
    (
        "repository preserves external source_item_id",
        'row.get("source_item_id")' in repo
        and 'inbox_row_id=str(row["id"])' in repo,
    ),
    (
        "repository preserves source metadata",
        'source_metadata.get(' in repo,
    ),
    (
        "shadow rows excluded from capture ingestion",
        '.get("shadow")' in repo
        and "Skipped {skipped} shadow row(s) from capture ingestion" in repo,
    ),
    (
        "Supabase lifecycle uses inbox_row_id",
        "item.inbox_row_id" in source
        and "self.repository.mark_processed(" in source,
    ),
    (
        "runtime marker exists",
        'INBOX_IDENTITY_SHADOW_FILTER_VERSION = "app-service-boundary-v1-phase1.3"'
        in run,
    ),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit(
        "RESULT: APP SERVICE BOUNDARY PHASE 1.3 VALIDATION FAILED"
    )

print(
    "RESULT: APP SERVICE BOUNDARY PHASE 1.3 STRUCTURE VALID"
)
