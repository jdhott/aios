#!/usr/bin/env python3
from __future__ import annotations
import ast
from pathlib import Path


def fn(text, name):
    tree=ast.parse(text); lines=text.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return "\n".join(lines[node.lineno-1:node.end_lineno])
    raise RuntimeError(name)


def main():
    root=Path(__file__).resolve().parents[1]
    text=(root/'run_aios.py').read_text()
    created=fn(text,'archive_created_item')
    reviewed=fn(text,'archive_reviewed_items')
    checks=[
      ('Supabase created items finalize directly', 'AIOS_INBOX_SOURCE == "supabase"' in created and 'inbox_source.remove_item(item)' in created),
      ('Supabase reviewed items finalize directly', 'AIOS_INBOX_SOURCE == "supabase"' in reviewed and 'inbox_source.remove_item(item)' in reviewed),
      ('Notion archive section only created for Notion inbox', 'and AIOS_INBOX_SOURCE == "notion"' in text),
      ('Supabase non-task notes bypass Notion archive', 'if AIOS_INBOX_SOURCE == "supabase":\n            inbox_source.remove_item(item)\n        else:\n            archive_non_task_note_item' in text),
      ('Supabase non-task ideas bypass Notion archive', 'if AIOS_INBOX_SOURCE == "supabase":\n            inbox_source.remove_item(item)\n        else:\n            archive_non_task_idea_item' in text),
      ('Notion archive trimming requires an archive section', 'elif archive_section_id:\n    trim_archive_runs(keep=5)' in text),
      ('Notion dashboard update is legacy datastore only', 'if not TEST_MODE and AIOS_DATASTORE == "notion":\n    update_aios_dashboard()' in text),
      ('Supabase dashboard authority marker exists', 'legacy Notion dashboard update disabled' in text),
    ]
    ast.parse(text)
    for label,ok in checks: print(f"{'PASS' if ok else 'FAIL'}: {label}")
    if not all(ok for _,ok in checks):
        print('RESULT: SUPABASE NOTION HOT-PATH CUTOVER V1 VALIDATION FAILED'); raise SystemExit(1)
    print('RESULT: SUPABASE NOTION HOT-PATH CUTOVER V1 STRUCTURE VALID')
if __name__=='__main__': main()
