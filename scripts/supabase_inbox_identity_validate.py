#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
repo = (root / "aios/storage/inbox_repository.py").read_text()
sql = (root / "sql/004_add_inbox_source_identity.sql").read_text()
run = (root / "run_aios.py").read_text()

checks = [
    ("source identity lookup exists", "def get_by_source_identity(" in repo),
    ("shadow get-or-create exists", "def get_or_create_shadow_item(" in repo),
    ("lookup uses source + source_item_id",
        '.eq("source", source)' in repo and '.eq("source_item_id", source_item_id)' in repo),
    ("shadow metadata preserves source context",
        '"source_container_id"' in repo and '"source_type"' in repo and '"shadow": True' in repo),
    ("shadow preserves text and notes",
        "text=item.text" in repo and "notes=list(item.notes or [])" in repo),
    ("unique source identity index exists",
        "create unique index if not exists inbox_items_source_identity_uidx" in sql
        and "(source, source_item_id)" in sql
        and "where source_item_id is not null" in sql),
    ("production runtime unchanged", "get_or_create_shadow_item(" not in run),
]

ast.parse(repo)

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: SUPABASE INBOX IDENTITY BRIDGE VALIDATION FAILED")

print("RESULT: SUPABASE INBOX IDENTITY BRIDGE STRUCTURE VALID")
