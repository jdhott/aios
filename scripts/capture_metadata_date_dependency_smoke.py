#!/usr/bin/env python3
"""Offline regression test for the now self-contained date parser."""
from __future__ import annotations

from aios.ingestion import capture_metadata


def main():
    # Only the broad title helpers remain injected. Date parsing itself should
    # now need no run_aios constants or helper functions.
    capture_metadata.configure_capture_metadata(
        {
            "normalize": lambda text: str(text or "").strip().lower(),
            "clean_task_title": lambda text: " ".join(
                str(text or "").split()
            ).strip(),
        }
    )

    flag_cases = [
        (
            "JDI Call flooring contractor [Basement Recovery]",
            True,
            False,
            False,
            "Basement Recovery",
        ),
        (
            "Call plumber urgent important",
            False,
            True,
            True,
            "",
        ),
        (
            "Call plumber ASAP",
            False,
            True,
            False,
            "",
        ),
    ]

    for raw, jdi, urgent, important, project in flag_cases:
        parsed = capture_metadata.parse_task_flags(raw)
        if parsed["jdi"] != jdi:
            raise RuntimeError(
                f"JDI parse mismatch for {raw!r}"
            )
        if parsed["urgent"] != urgent:
            raise RuntimeError(
                f"Urgent parse mismatch for {raw!r}"
            )
        if parsed["important"] != important:
            raise RuntimeError(
                f"Important parse mismatch for {raw!r}"
            )
        if parsed["manual_project"] != project:
            raise RuntimeError(
                f"Project parse mismatch for {raw!r}"
            )

    date_cases = [
        "Buy mulch May 10",
        "Call plumber tomorrow",
        "Finish report Friday",
        "Plan outing this weekend",
        "Plan outing next weekend",
    ]

    for raw in date_cases:
        due = capture_metadata.extract_due_date(raw)
        if due is None:
            raise RuntimeError(
                f"Due date not recognized for {raw!r}"
            )

    cleaned = capture_metadata.strip_due_date_phrases(
        "Buy mulch - urgent - May 10"
    )
    if "may 10" in cleaned.lower():
        raise RuntimeError(
            "Month/day phrase remained after stripping"
        )

    structured = capture_metadata.parse_capture_metadata(
        "JDI Call plumber tomorrow urgent [Basement Recovery]"
    )

    if not structured.is_jdi:
        raise RuntimeError(
            "Structured JDI mapping failed"
        )
    if not structured.is_urgent:
        raise RuntimeError(
            "Structured urgent mapping failed"
        )
    if structured.project_hint != "Basement Recovery":
        raise RuntimeError(
            "Structured project hint mapping failed"
        )
    if structured.due_date is None:
        raise RuntimeError(
            "Structured due-date mapping failed"
        )

    print("JDI / urgent / important parsing: PASS")
    print("[project hint] parsing: PASS")
    print("Month/day date parsing: PASS")
    print("Relative date parsing: PASS")
    print("Weekday date parsing: PASS")
    print("Weekend date parsing: PASS")
    print("Date phrase stripping: PASS")
    print("CaptureMetadata mapping: PASS")
    print(
        "RESULT: CAPTURE METADATA DATE DEPENDENCY FIX "
        "SMOKE TEST PASSED"
    )


if __name__ == "__main__":
    main()
