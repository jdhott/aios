#!/usr/bin/env python3
import argparse
import json

from dotenv import find_dotenv, load_dotenv
from aios.services.review_service import ReviewService


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--type",
        action="append",
        dest="review_types",
        choices=["clarification", "possible_duplicate"],
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    load_dotenv(find_dotenv() or ".env", override=True)

    service = ReviewService()
    reviews = service.list_pending_reviews(
        review_types=args.review_types,
    )

    if args.json:
        print(json.dumps(
            [review.to_dict() for review in reviews],
            indent=2,
            sort_keys=True,
        ))
        return

    print("=== APP REVIEW SERVICE — OPEN REVIEW QUEUE ===")
    print("Count:", len(reviews))

    for index, review in enumerate(reviews, 1):
        print()
        print(f"[{index}] {review.review_type} state={review.state}")
        print("  id:", review.id)
        print("  inbox_item_id:", review.inbox_item_id)
        print("  subject:", review.subject_text)
        print("  options:", review.options)
        print("  payload:", json.dumps(
            review.payload,
            sort_keys=True,
            default=str,
        ))


if __name__ == "__main__":
    main()
