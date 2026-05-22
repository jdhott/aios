
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

RELATIVE_TEMPORAL_TOKENS = [
    "tomorrow morning",
    "tomorrow afternoon",
    "tomorrow evening",
    "this morning",
    "this afternoon",
    "this evening",
    "today",
    "tomorrow",
    "tonight",
]

def cleanup_temporal_tokens(text: str) -> str:
    if not text:
        return ""

    cleaned = text

    for token in sorted(
        RELATIVE_TEMPORAL_TOKENS,
        key=len,
        reverse=True,
    ):
        cleaned = re.sub(
            rf"\b{re.escape(token)}\b",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip(" -")

def extract_defer_until(text: str):
    return None

def normalize_due_date(dt):
    return dt

def _extract_relative_due_date(text: str):
    lowered = (text or "").lower()

    now = datetime.now()

    if "tomorrow" in lowered:
        return now.date() + timedelta(days=1)

    if "today" in lowered or "tonight" in lowered:
        return now.date()

    return None

def extract_temporal_metadata(text: str) -> dict:
    cleaned_title = cleanup_temporal_tokens(text)

    due_date = _extract_relative_due_date(text)

    temporal_tokens_found = [
        token
        for token in RELATIVE_TEMPORAL_TOKENS
        if token in (text or "").lower()
    ]

    payload = {
        "cleaned_title": cleaned_title,
        "cleaned_text": cleaned_title,
        "due_date": normalize_due_date(due_date),
        "defer_until": extract_defer_until(text),
        "temporal_tokens_found": temporal_tokens_found,
    }

    logger.info(
        "[TEMPORAL AUTHORITY] input=%r cleaned=%r due_date=%r tokens=%r",
        text,
        cleaned_title,
        due_date,
        temporal_tokens_found,
    )

    return payload
