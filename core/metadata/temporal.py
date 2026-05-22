from __future__ import annotations

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

RELATIVE_TEMPORAL_TOKENS = [
    "today",
    "tomorrow",
    "tonight",
    "tomorrow morning",
    "tomorrow afternoon",
    "tomorrow evening",
]


def cleanup_temporal_tokens(text: str) -> str:
    if not text:
        return ""

    cleaned = text

    phrases = sorted(
        RELATIVE_TEMPORAL_TOKENS,
        key=len,
        reverse=True,
    )

    for phrase in phrases:
        cleaned = cleaned.replace(f" {phrase}", "")
        cleaned = cleaned.replace(f" {phrase.title()}", "")

    return " ".join(cleaned.split()).strip()


def normalize_due_date(dt):
    return dt


def extract_defer_until(text: str):
    return None


def _extract_relative_due_date(text: str):
    lowered = (text or "").lower()

    now = datetime.now()

    if "tomorrow" in lowered:
        return now.date() + timedelta(days=1)

    if "today" in lowered or "tonight" in lowered:
        return now.date()

    return None


def extract_temporal_metadata(text: str) -> dict:
    cleaned_text = cleanup_temporal_tokens(text)

    due_date = _extract_relative_due_date(text)

    temporal_tokens_found = [
        token
        for token in RELATIVE_TEMPORAL_TOKENS
        if token in (text or "").lower()
    ]

    payload = {
        "cleaned_text": cleaned_text,
        "due_date": normalize_due_date(due_date),
        "defer_until": extract_defer_until(text),
        "temporal_tokens_found": temporal_tokens_found,
    }

    logger.info(
        "[TEMPORAL] input=%r cleaned=%r due_date=%r tokens=%r",
        text,
        cleaned_text,
        due_date,
        temporal_tokens_found,
    )

    return payload


def is_due_today(task) -> bool:
    due_date = None

    if isinstance(task, dict):
        due_date = task.get("due_date") or task.get("Due Date")

    if due_date is None:
        return False

    if hasattr(due_date, "date"):
        due_date = due_date.date()

    return due_date == datetime.now().date()


def is_overdue(task) -> bool:
    due_date = None

    if isinstance(task, dict):
        due_date = task.get("due_date") or task.get("Due Date")

    if due_date is None:
        return False

    if hasattr(due_date, "date"):
        due_date = due_date.date()

    return due_date < datetime.now().date()


def is_due_soon(task, days: int = 3) -> bool:
    due_date = None

    if isinstance(task, dict):
        due_date = task.get("due_date") or task.get("Due Date")

    if due_date is None:
        return False

    if hasattr(due_date, "date"):
        due_date = due_date.date()

    today = datetime.now().date()

    return today <= due_date <= (today + timedelta(days=days))