#!/usr/bin/env python3
from dotenv import find_dotenv, load_dotenv
import argparse
from aios.ingestion.capture_metadata import parse_capture_metadata
from aios.storage.inbox_repository import InboxRepository
from aios.storage.supabase_store import SupabaseStore

def main():
    p = argparse.ArgumentParser()
    p.add_argument("text")
    p.add_argument("--note", action="append", default=[])
    args = p.parse_args()
    load_dotenv(find_dotenv() or ".env", override=True)
    repo = InboxRepository(SupabaseStore())
    row = repo.create_brain_dump_item(
        raw_text=args.text,
        notes=args.note,
        parser=parse_capture_metadata,
        source_metadata={"capture_interface": "cli_app_boundary_v1"},
    )
    print("=== SUPABASE INBOX CAPTURED ===")
    for key in (
        "id","status","source","text","clean_text","due_date",
        "project_hint","is_urgent","is_important","is_just_do_it"
    ):
        print(f"{key}:", row.get(key))

if __name__ == "__main__":
    main()
