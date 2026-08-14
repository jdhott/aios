#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
run = (root / "run_aios.py").read_text()

archive_marker = '[Notion Archive Module] Canonical Brain Dump archive helpers loaded'
refresh_marker = '[Inbox Source] Notion lifecycle dependencies refreshed'

checks = [
    ("archive module marker exists", archive_marker in run),
    ("lifecycle refresh marker exists", refresh_marker in run),
    ("notion source is reconfigured after archive load",
        run.find(archive_marker) < run.find("notion_source.configure_notion_source(globals())", run.find(archive_marker))),
    ("refresh occurs before runtime pipeline",
        run.find(refresh_marker) < run.find("Brain Dump synced blocks found") if "Brain Dump synced blocks found" in run else True),
]

ast.parse(run)

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: NOTION INBOX LIFECYCLE INIT FIX VALIDATION FAILED")

print("RESULT: NOTION INBOX LIFECYCLE INIT FIX STRUCTURE VALID")
