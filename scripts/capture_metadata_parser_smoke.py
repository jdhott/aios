#!/usr/bin/env python3
import re
from datetime import datetime, timedelta

from aios.ingestion import capture_metadata


def _normalize(text):
    return re.sub(r"\s+", " ", str(text or "").strip()).lower()


def _clean_task_title(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _next_weekday_date(today, target_weekday, include_today=False):
    days_ahead = (target_weekday - today.weekday()) % 7
    if days_ahead == 0 and not include_today:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def main():
    capture_metadata.configure_capture_metadata(
        {
            "re": re,
            "datetime": datetime,
            "timedelta": timedelta,
            "normalize": _normalize,
            "clean_task_title": _clean_task_title,
            "_next_weekday_date": _next_weekday_date,
        }
    )

    cases = [
        ("JDI Call flooring contractor [Basement Recovery]", True, False, False, "Basement Recovery", "Call flooring contractor"),
        ("Call plumber urgent important", False, True, True, "", "Call plumber"),
        ("Call plumber ASAP", False, True, False, "", "Call plumber"),
        ("[urgent] Call flooring contractor", False, True, False, "", "Call flooring contractor"),
        ("Discuss [Basement Recovery] naming", False, False, False, "", "Discuss Basement Recovery naming"),
    ]

    for raw, jdi, urgent, important, project, title in cases:
        parsed = capture_metadata.parse_task_flags(raw)
        expected = {
            "jdi": jdi,
            "urgent": urgent,
            "important": important,
            "manual_project": project,
            "clean_title": title,
        }
        for key, value in expected.items():
            if parsed.get(key) != value:
                raise RuntimeError(
                    f"{raw!r}: {key}={parsed.get(key)!r}; expected {value!r}"
                )

    raw = "Buy mulch - urgent - May 10"
    parsed = capture_metadata.parse_task_flags(raw)
    due = capture_metadata.extract_due_date(raw)
    clean = capture_metadata.strip_due_date_phrases(parsed["clean_title"])

    if due is None:
        raise RuntimeError("Month/day due date not recognized")
    if "may 10" in clean.lower():
        raise RuntimeError("Due date phrase not stripped")

    structured = capture_metadata.parse_capture_metadata(
        "JDI Call plumber tomorrow urgent [Basement Recovery]"
    )

    if not structured.is_jdi or not structured.is_urgent:
        raise RuntimeError("Structured flag mapping failed")
    if structured.project_hint != "Basement Recovery":
        raise RuntimeError("Structured project mapping failed")
    if structured.due_date is None:
        raise RuntimeError("Structured due date mapping failed")

    print("Current JDI syntax: PASS")
    print("Current urgent / ASAP syntax: PASS")
    print("Current important syntax: PASS")
    print("Current [project hint] syntax: PASS")
    print("Natural-language due date parsing: PASS")
    print("Due-date title stripping: PASS")
    print("Source-neutral CaptureMetadata mapping: PASS")
    print("RESULT: CAPTURE METADATA PARSER EXTRACTION SMOKE TEST PASSED")

if __name__ == "__main__":
    main()
