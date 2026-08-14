#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
texts = {
    "metadata": (root / "aios/storage/task_metadata_writer.py").read_text(),
    "lifecycle": (root / "aios/storage/task_lifecycle_writer.py").read_text(),
    "relation": (root / "aios/storage/task_project_relation_writer.py").read_text(),
}

checks = [
    ("metadata refresh_tasks exists", "def refresh_tasks(self)" in texts["metadata"]),
    ("metadata retries after miss", "[Task Metadata Write] Refreshed task ID mappings after cache miss" in texts["metadata"] and "to Supabase after refresh." in texts["metadata"]),
    ("lifecycle refresh_tasks exists", "def refresh_tasks(self)" in texts["lifecycle"]),
    ("lifecycle retries after miss", "[Task Lifecycle Write] Refreshed task ID mappings after cache miss" in texts["lifecycle"] and "to Supabase after refresh." in texts["lifecycle"]),
    ("project relation refresh_tasks exists", "def refresh_tasks(self)" in texts["relation"]),
    ("project relation retries after miss", "[Project Relation Write] Refreshed task ID mappings after cache miss" in texts["relation"] and "to Supabase after refresh." in texts["relation"]),
    ("project refresh remains", "def refresh_projects(self)" in texts["relation"]),
]

for text in texts.values():
    ast.parse(text)

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: TASK MAPPING CACHE REFRESH VALIDATION FAILED")

print("RESULT: TASK MAPPING CACHE REFRESH STRUCTURE VALID")
