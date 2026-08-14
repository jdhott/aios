#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
audit = (root / "core/storage/supabase_authority_audit.py").read_text()
run = (root / "run_aios.py").read_text()
clar = (root / "aios/clarification.py").read_text()
writer = (root / "aios/storage/notion_task_mirror_writer.py").read_text()
reconcile = (root / "scripts/notion_task_mirror_title_reconcile.py").read_text()

for text in (audit, run, clar, writer, reconcile):
    ast.parse(text)

checks = [
    ("dedicated title writer exists", "class NotionTaskMirrorTitleWriter" in writer),
    ("writer is Task Name title-only", '"Task Name"' in writer and '"Status"' not in writer and '"Done"' not in writer),
    ("audit predicate exists", "def _is_task_mirror_title_patch(payload):" in audit),
    ("title-only PATCH allowed", "Supabase-authoritative task title mirrored to Notion presentation" in audit),
    ("generic page PATCH remains blocked", "Notion page {method} in Supabase mode" in audit),
    ("writer configured in Supabase mode", "[Task Mirror Title] Writer configured" in run),
    ("clarification mirror helper exists", "def _mirror_resolved_task_title(" in clar),
    ("mirror failure non-blocking", "Non-blocking mirror update failed" in clar),
    ("reconciliation dry-run default", "Dry run only. No Notion titles were changed." in reconcile),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: NOTION TASK MIRROR TITLE SYNC VALIDATION FAILED")

print("RESULT: NOTION TASK MIRROR TITLE SYNC STRUCTURE VALID")
