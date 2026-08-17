#!/usr/bin/env python3

from aios.ingestion.models import InboxItem
from aios.review.models import InboxReview


def main():
    native_item = InboxItem(
        text="Check generator quote",
        notes=[],
        source="brain_dump",
        source_item_id="native-inbox-123",
        inbox_row_id="native-inbox-123",
        source_type="inbox_item",
    )

    legacy_item = InboxItem(
        text="Check old generator quote",
        notes=[],
        source="notion",
        source_item_id="notion-block-xyz",
        source_container_id="brain-dump-sync",
        source_type="paragraph",
    )

    class FakeInboxRepo:
        def __init__(self):
            self.native_rows = {
                "native-inbox-123": {
                    "id": "native-inbox-123",
                    "source_metadata": {},
                }
            }
            self.shadow_rows = {}

        def get_row(self, inbox_id):
            return self.native_rows.get(inbox_id)

        def get_by_source_identity(
            self,
            *,
            source,
            source_item_id,
        ):
            return self.shadow_rows.get(
                (source, source_item_id)
            )

        def get_review_rows_for_item(self, item):
            rows = []

            if item.inbox_row_id:
                row = self.get_row(
                    str(item.inbox_row_id)
                )
                if row:
                    rows.append(row)

            legacy = self.get_by_source_identity(
                source=item.source,
                source_item_id=item.source_item_id,
            )

            if (
                legacy
                and all(
                    row["id"] != legacy["id"]
                    for row in rows
                )
            ):
                rows.append(legacy)

            return rows

        def get_or_create_shadow_item(self, item):
            key = (
                item.source,
                item.source_item_id,
            )

            existing = self.shadow_rows.get(key)

            if existing:
                return existing

            row = {
                "id": "legacy-shadow-123",
                "source_metadata": {
                    "shadow": True,
                },
            }

            self.shadow_rows[key] = row
            return row

        def get_review_row_for_item(self, item):
            rows = self.get_review_rows_for_item(
                item
            )

            if rows:
                return rows[0]

            return self.get_or_create_shadow_item(
                item
            )

    class FakeReviewRepo:
        def __init__(self):
            self.created = []
            self.open_by_inbox = {}

        def get_open_reviews_for_item(
            self,
            inbox_id,
        ):
            return list(
                self.open_by_inbox.get(
                    inbox_id,
                    [],
                )
            )

        def create_review(self, **kwargs):
            self.created.append(kwargs)

            review = InboxReview(
                id=f"review-{len(self.created)}",
                inbox_item_id=kwargs[
                    "inbox_item_id"
                ],
                review_type=kwargs[
                    "review_type"
                ],
                state="pending",
                payload=kwargs["payload"],
            )

            self.open_by_inbox.setdefault(
                kwargs["inbox_item_id"],
                [],
            ).append(review)

            return review

    inbox_repo = FakeInboxRepo()
    review_repo = FakeReviewRepo()

    def write_once(item):
        # Search native + legacy-compatible rows
        # before creating another review.
        for row in (
            inbox_repo
            .get_review_rows_for_item(item)
        ):
            for review in (
                review_repo
                .get_open_reviews_for_item(
                    str(row["id"])
                )
            ):
                if (
                    review.review_type
                    == "possible_duplicate"
                ):
                    return review

        row = (
            inbox_repo
            .get_review_row_for_item(item)
        )

        return review_repo.create_review(
            inbox_item_id=str(row["id"]),
            review_type="possible_duplicate",
            payload={
                "original_text": item.text,
                "candidate_task_id":
                    "task-456",
                "candidate_task_title":
                    "Review generator quote",
                "match_score": 0.72,
                "confidence": "Medium",
                "allowed_decisions": [
                    "link_existing",
                    "create_anyway",
                    "ignore",
                ],
                "authority":
                    "supabase_review_authority_v1",
            },
        )

    # Native Supabase item owns its review directly.
    first = write_once(native_item)
    second = write_once(native_item)

    assert first.id == second.id
    assert (
        first.inbox_item_id
        == "native-inbox-123"
    )

    assert not inbox_repo.shadow_rows

    print(
        "Native inbox row owns new review: PASS"
    )
    print(
        "Native review idempotency: PASS"
    )

    # Legacy/Notion-origin item still gets a
    # compatibility shadow row.
    legacy_first = write_once(legacy_item)
    legacy_second = write_once(legacy_item)

    assert legacy_first.id == legacy_second.id
    assert (
        legacy_first.inbox_item_id
        == "legacy-shadow-123"
    )

    print(
        "Legacy shadow fallback: PASS"
    )
    print(
        "Legacy review idempotency: PASS"
    )

    assert len(review_repo.created) == 2

    for row in review_repo.created:
        assert (
            row["payload"]["authority"]
            == "supabase_review_authority_v1"
        )

    print(
        "Supabase review authority marker: PASS"
    )
    print(
        "RESULT: POSSIBLE DUPLICATE "
        "REVIEW OWNERSHIP SMOKE TEST PASSED"
    )


if __name__ == "__main__":
    main()
