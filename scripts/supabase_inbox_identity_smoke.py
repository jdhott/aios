#!/usr/bin/env python3
from uuid import uuid4
from dotenv import find_dotenv, load_dotenv

from aios.ingestion.models import InboxItem
from aios.storage.inbox_repository import InboxRepository
from aios.storage.supabase_store import SupabaseStore

load_dotenv(find_dotenv() or ".env", override=True)

repo = InboxRepository(SupabaseStore())
external_id = "notion-shadow-smoke-" + uuid4().hex

item = InboxItem(
    text="Temporary identity bridge smoke",
    notes=["Temporary source-neutral shadow row"],
    source="notion",
    source_item_id=external_id,
    source_container_id="synced-block-smoke",
    source_type="paragraph",
)

created_id = None

try:
    first = repo.get_or_create_shadow_item(item)
    created_id = str(first["id"])

    second = repo.get_or_create_shadow_item(item)

    if str(second["id"]) != created_id:
        raise RuntimeError("Repeated shadow creation returned a different Supabase UUID.")

    found = repo.get_by_source_identity(
        source="notion",
        source_item_id=external_id,
    )

    if not found or str(found["id"]) != created_id:
        raise RuntimeError("Source identity lookup failed.")

    metadata = found.get("source_metadata") or {}

    if metadata.get("source_container_id") != "synced-block-smoke":
        raise RuntimeError("source_container_id was not preserved.")

    if metadata.get("source_type") != "paragraph":
        raise RuntimeError("source_type was not preserved.")

    response = (
        repo.store.client
        .table("inbox_items")
        .select("id")
        .eq("source", "notion")
        .eq("source_item_id", external_id)
        .execute()
    )

    rows = response.data or []
    if len(rows) != 1:
        raise RuntimeError(f"Expected one shadow row; found {len(rows)}")

    print("External source identity lookup: PASS")
    print("Shadow row creation: PASS")
    print("Repeated get-or-create idempotency: PASS")
    print("Stable Supabase UUID: PASS")
    print("Source metadata preservation: PASS")
    print("Unique row count: PASS")
    print("RESULT: SUPABASE INBOX IDENTITY BRIDGE SMOKE TEST PASSED")
finally:
    if created_id:
        repo.delete_item(created_id)
        if repo.get_row(created_id) is not None:
            raise RuntimeError("Temporary shadow row cleanup failed.")
        print("Temporary shadow row cleanup: PASS")
