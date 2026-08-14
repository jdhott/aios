#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
run = (root / "run_aios.py").read_text()
capture = (root / "scripts/app_inbox_capture.py").read_text()
source = (root / "aios/ingestion/supabase_source.py").read_text()

for text in (run, capture, source):
    ast.parse(text)

checks = [
    ("marker", "app-service-boundary-v1-phase1" in run),
    ("default notion", 'os.getenv("AIOS_INBOX_SOURCE", "notion")' in run),
    ("selector validation", 'AIOS_INBOX_SOURCE not in {"notion", "supabase"}' in run),
    ("supabase datastore guard", 'AIOS_INBOX_SOURCE == "supabase"' in run and 'AIOS_DATASTORE != "supabase"' in run),
    ("SupabaseInboxSource import", "from aios.ingestion.supabase_source import SupabaseInboxSource" in run),
    ("source-neutral pipeline read", "inbox_items = inbox_source.list_pending_items()" in run),
    ("processed lifecycle", "self.repository.mark_processed(" in source),
    ("canonical capture", "create_brain_dump_item(" in capture and "parser=parse_capture_metadata" in capture),
]
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: APP SERVICE BOUNDARY V1 PHASE 1 VALIDATION FAILED")
print("RESULT: APP SERVICE BOUNDARY V1 PHASE 1 STRUCTURE VALID")
