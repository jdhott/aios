#!/usr/bin/env python3
import ast
from pathlib import Path

MOVED = {
    "find_first_synced_block",
    "get_block_age_seconds",
    "extract_note_texts_from_block",
    "extract_brain_dump_items",
}

GENERIC_READERS = {
    "get_block_text",
    "get_block_children",
    "get_block",
}

def functions(text):
    tree = ast.parse(text)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }

def main():
    root = Path(__file__).resolve().parents[1]
    run_text = (root / "run_aios.py").read_text()
    notion_text = (root / "aios" / "ingestion" / "notion_source.py").read_text()
    source_text = (root / "aios" / "ingestion" / "source.py").read_text()

    run_funcs = functions(run_text)
    notion_funcs = functions(notion_text)

    checks = [
        ("InboxSource protocol exists", "class InboxSource(Protocol)" in source_text and "list_pending_items" in source_text),
        ("NotionInboxSource exists", "class NotionInboxSource" in notion_text and "def list_pending_items" in notion_text),
        ("four Notion extraction helpers left run_aios", not (MOVED & run_funcs)),
        ("four Notion extraction helpers live in notion_source", MOVED <= notion_funcs),
        ("generic Notion block readers remain in runtime", GENERIC_READERS <= run_funcs),
        ("runtime configures Notion inbox source", "notion_inbox_source.configure_notion_source(globals())" in run_text),
        ("runtime constructs NotionInboxSource", "NotionInboxSource(" in run_text),
        ("pipeline reads through source boundary", "inbox_source.list_pending_items()" in run_text),
        ("direct extractor call removed from pipeline", "extract_brain_dump_items(BRAIN_DUMP_PAGE_ID)" not in run_text),
        ("Notion source returns source-neutral InboxItem", "InboxItem(" in notion_text and 'source="notion"' in notion_text),
    ]

    ast.parse(run_text)
    ast.parse(notion_text)
    ast.parse(source_text)

    for label, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {label}")

    if not all(ok for _, ok in checks):
        print("\nRESULT: NOTION INBOX SOURCE EXTRACTION VALIDATION FAILED")
        raise SystemExit(1)

    print("\nRESULT: NOTION INBOX SOURCE EXTRACTION STRUCTURE VALID")

if __name__ == "__main__":
    main()
