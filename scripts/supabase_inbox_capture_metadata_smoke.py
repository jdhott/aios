#!/usr/bin/env python3
from datetime import datetime, timezone
from uuid import uuid4
from dotenv import find_dotenv, load_dotenv

from aios.ingestion import capture_metadata
from aios.storage.inbox_repository import InboxRepository
from aios.storage.supabase_store import SupabaseStore

load_dotenv(find_dotenv() or ".env", override=True)

capture_metadata.configure_capture_metadata({
    "normalize": lambda text: str(text or "").strip().lower(),
    "clean_task_title": lambda text: " ".join(str(text or "").split()).strip(),
})

repo = InboxRepository(SupabaseStore())
marker = "AIOS_CAPTURE_METADATA_" + uuid4().hex
raw = f"JDI Call plumber {marker} tomorrow urgent [Basement Recovery]"
created_id = None

try:
    row = repo.create_brain_dump_item(
        raw_text=raw,
        notes=["Temporary controlled capture metadata smoke"],
        parser=capture_metadata.parse_capture_metadata,
        source_metadata={
            "test": True,
            "created_by": "scripts.supabase_inbox_capture_metadata_smoke",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    created_id = str(row["id"])
    stored = repo.get_row(created_id)
    if stored["text"] != raw:
        raise RuntimeError("Raw text not preserved.")
    clean = stored.get("clean_text") or ""
    for token in ["JDI", "urgent", "tomorrow", "Basement Recovery"]:
        if token.lower() in clean.lower():
            raise RuntimeError(f"Metadata token remained in clean_text: {token}")
    if marker not in clean:
        raise RuntimeError("Business text lost during parsing.")
    if stored.get("project_hint") != "Basement Recovery":
        raise RuntimeError("Project hint not persisted.")
    if stored.get("is_urgent") is not True:
        raise RuntimeError("Urgent not persisted.")
    if stored.get("is_important") is not False:
        raise RuntimeError("Important default incorrect.")
    if stored.get("is_just_do_it") is not True:
        raise RuntimeError("JDI not persisted.")
    if not stored.get("due_date"):
        raise RuntimeError("Due date not persisted.")

    print("Raw Brain Dump text preservation: PASS")
    print("Canonical parser invocation: PASS")
    print("Clean text persistence: PASS")
    print("Due date persistence: PASS")
    print("Project hint persistence: PASS")
    print("Urgent / Important / JDI persistence: PASS")
    print("RESULT: SUPABASE INBOX CAPTURE METADATA POC SMOKE TEST PASSED")
finally:
    if created_id:
        repo.delete_item(created_id)
        if repo.get_row(created_id) is not None:
            raise RuntimeError("Temporary inbox cleanup failed.")
        print("Temporary inbox row cleanup: PASS")
