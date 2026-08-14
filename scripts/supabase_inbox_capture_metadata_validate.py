#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
repo = (root / "aios/storage/inbox_repository.py").read_text()
sql = (root / "sql/002_add_inbox_capture_metadata.sql").read_text()
run = (root / "run_aios.py").read_text()

checks = [
    ("CaptureMetadata import", "from aios.ingestion.capture_metadata import CaptureMetadata" in repo),
    ("create_item accepts metadata", "capture_metadata: Optional[CaptureMetadata]" in repo),
    ("Brain Dump helper exists", "def create_brain_dump_item(" in repo),
    ("raw text preserved", '"text": text' in repo),
    ("structured fields persisted", all(x in repo for x in [
        '"clean_text"', '"due_date"', '"project_hint"',
        '"is_urgent"', '"is_important"', '"is_just_do_it"'
    ])),
    ("schema columns present", all(x in sql for x in [
        "clean_text text", "due_date date", "project_hint text",
        "is_urgent boolean", "is_important boolean", "is_just_do_it boolean"
    ])),
    ("production still Notion", "NotionInboxSource(" in run and "SupabaseInboxSource(" not in run),
]
ast.parse(repo)
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: SUPABASE INBOX CAPTURE METADATA POC VALIDATION FAILED")
print("RESULT: SUPABASE INBOX CAPTURE METADATA POC STRUCTURE VALID")
