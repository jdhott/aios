import core.storage.supabase_authority_audit as authority_audit
from core.storage.supabase_authority_audit import classify_mutation


def chk(method, url, payload, expected):
    got, _ = classify_mutation(method, url, payload)
    if got != expected:
        raise RuntimeError(f"{method} {url}: {got} != {expected}")


def main():
    pages = "https://api.notion.com/v1/pages"
    chk(
        "PATCH",
        "https://api.notion.com/v1/blocks/x/children",
        {},
        "unexpected_notion",
    )
    chk(
        "POST",
        pages,
        {"parent": {"database_id": "legacy-task-db"}},
        "unexpected_notion",
    )
    chk(
        "PATCH",
        "https://api.notion.com/v1/pages/task1",
        {"properties": {}},
        "unexpected_notion",
    )

    authority_audit._EVENTS.clear()
    authority_audit._ENABLED = True
    authority_audit._record(
        "POST",
        "https://api.notion.com/v1/databases/33333333333333333333333333333333/query",
        {"page_size": 8},
    )
    if authority_audit._EVENTS:
        raise RuntimeError(
            "Read-only Notion database query was incorrectly recorded as a mutation"
        )

    print("Any Notion mutation is unexpected in Supabase mode: PASS")
    print("Database query POST exclusion: PASS")
    print("RESULT: SUPABASE AUTHORITY AUDIT SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
