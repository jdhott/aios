from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from typing import Any


@dataclass(frozen=True)
class CaptureMetadata:
    original_text: str
    clean_text: str
    due_date: Any
    project_hint: str
    is_urgent: bool
    is_important: bool
    is_jdi: bool


def configure_capture_metadata(namespace):
    globals().update(namespace)


# -------------------------------------------------------------------------
# DATE PARSER DEPENDENCIES OWNED HERE
# -------------------------------------------------------------------------
MONTH_NAME_PATTERN = r"(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)"

MONTH_DAY_DATE_PATTERN = rf"\b(?:by|due|on)?\s*{MONTH_NAME_PATTERN}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b"

DUE_DATE_WORD_PATTERNS = [
    MONTH_DAY_DATE_PATTERN,
    # Put longer phrases first so compound phrases are removed as a unit before
    # shorter patterns see only part of the phrase.
    r"\b(?:by|due|on|for)\s+(?:today|tomorrow)\s+(?:morning|afternoon|evening|night)\b",
    r"\b(?:by|due|on|for)\s+(?:today|tomorrow|tonight)\b",
    r"\b(?:by|due|on|for)\s+this\s+(?:morning|afternoon|evening|week|weekend)\b",
    r"\b(?:by|due|on|for)\s+next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|weekend)\b",
    r"\b(?:by|due|on|for)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\b(?:today|tomorrow)\s+(?:morning|afternoon|evening|night)\b",
    r"\btoday\b",
    r"\btomorrow\b",
    r"\btonight\b",
    r"\bthis\s+(?:morning|afternoon|evening|week|weekend)\b",
    r"\bnext\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|weekend)\b",
]

def _next_weekday_date(today, weekday_num, include_today=False):
    """Return the next date for weekday_num, where Monday is 0."""
    days_ahead = (weekday_num - today.weekday()) % 7
    if days_ahead == 0 and not include_today:
        days_ahead = 7
    return today + timedelta(days=days_ahead)

def parse_capture_metadata(text: str) -> CaptureMetadata:
    parsed = parse_task_flags(text)
    due_date = extract_due_date(text)
    cleaned = strip_due_date_phrases(parsed["clean_title"])
    cleaned = cleaned or parsed["clean_title"]

    return CaptureMetadata(
        original_text=parsed.get("original_text", str(text or "")),
        clean_text=cleaned,
        due_date=due_date,
        project_hint=parsed.get("manual_project", ""),
        is_urgent=bool(parsed.get("urgent", False)),
        is_important=bool(parsed.get("important", False)),
        is_jdi=bool(parsed.get("jdi", False)),
    )


def parse_manual_project_tag(text):
    """Extract an explicit manual project hint from a Brain Dump item.

    Primary syntax:
    - [Basement Recovery] Get flooring quote
    - Get flooring quote [Basement Recovery]

    A bracketed value is treated as a project hint only when it appears at the
    beginning or end of the item. Known AIOS control flags such as [urgent] and
    [JDI] remain normal task flags rather than becoming project hints.

    Returns (clean_text, project_name). The hint is user intent and should not
    remain in the final task title.
    """
    raw = str(text or "").strip()
    if not raw:
        return raw, ""

    reserved_flags = {
        "jdi",
        "just do it",
        "urgent",
        "asap",
        "important",
        "very important",
        "high importance",
    }

    edge_patterns = [
        re.compile(r"^\s*\[([^\[\]]+?)\]\s*(.*?)\s*$"),
        re.compile(r"^\s*(.*?)\s*\[([^\[\]]+?)\]\s*$"),
    ]

    # Prefix: [Project Hint] Task title
    match = edge_patterns[0].match(raw)
    if match:
        candidate = re.sub(r"\s+", " ", match.group(1)).strip(" -–—:|;\t")
        remainder = match.group(2).strip()
        if candidate and normalize(candidate) not in reserved_flags and remainder:
            return remainder, candidate

    # Suffix: Task title [Project Hint]
    match = edge_patterns[1].match(raw)
    if match:
        remainder = match.group(1).strip()
        candidate = re.sub(r"\s+", " ", match.group(2)).strip(" -–—:|;\t")
        if candidate and normalize(candidate) not in reserved_flags and remainder:
            return remainder, candidate

    return raw, ""


def parse_task_flags(text):
    original_text = text.strip()
    text_without_project_tag, manual_project = parse_manual_project_tag(original_text)

    is_jdi = bool(
        re.search(r"\bJDI\b", original_text, flags=re.IGNORECASE)
        or re.search(r"\bjust do it\b", original_text, flags=re.IGNORECASE)
    )

    is_urgent = bool(
        re.search(r"\burgent\b", original_text, flags=re.IGNORECASE)
        or re.search(r"\basap\b", original_text, flags=re.IGNORECASE)
    )

    is_important = bool(
        re.search(r"\bimportant\b", original_text, flags=re.IGNORECASE)
        or re.search(r"\bvery important\b", original_text, flags=re.IGNORECASE)
        or re.search(r"\bhigh importance\b", original_text, flags=re.IGNORECASE)
    )

    clean_title = text_without_project_tag

    # Remove explicit execution / metadata flags. These are user-provided
    # control words, not part of the final task title.
    clean_title = re.sub(r"\bJDI\b", "", clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r"\bjust do it\b", "", clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r"\burgent\b", "", clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r"\basap\b", "", clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r"\bvery important\b", "", clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r"\bhigh importance\b", "", clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r"\bimportant\b", "", clean_title, flags=re.IGNORECASE)

    # Remove leftover brackets like (urgent)
    clean_title = re.sub(r"[\(\)\[\]]", "", clean_title)

    # Normalize spacing
    clean_title = re.sub(r"\s+", " ", clean_title).strip()
    clean_title = re.sub(r"^[\-\–\—\:\|\(\)\[\]\s]+", "", clean_title).strip()
    clean_title = re.sub(r"[\-\–\—\:\|\(\)\[\]\s]+$", "", clean_title).strip()

    clean_title = clean_task_title(clean_title)

    return {
        "original_text": original_text,
        "clean_title": clean_title,
        "jdi": is_jdi,
        "urgent": is_urgent,
        "important": is_important,
        "manual_project": manual_project,
    }


def sanitize_task_title_separators(text):
    """Clean separator debris left after metadata/date stripping.

    Metadata such as urgent/JDI and due-date phrases may be written between
    separators, e.g. "Buy mulch - urgent - May 10". After removing those
    tokens, titles can otherwise be left as "Buy mulch - -". This helper is
    intentionally text-only and safe to run repeatedly.
    """
    title = str(text or "").strip()

    if not title:
        return ""

    # Normalize dash variants and spacing around common separators.
    title = re.sub(r"[–—]", "-", title)
    title = re.sub(r"\s*([,:;|/])\s*", r" \1 ", title)
    title = re.sub(r"\s*-\s*", " - ", title)

    # Collapse empty/repeated separators created by removed metadata/date text.
    title = re.sub(r"(?:\s+[-,:;|/])+\s*[-,:;|/]\s*", " - ", title)
    title = re.sub(r"\s*[-,:;|/]\s*$", "", title)
    title = re.sub(r"^\s*[-,:;|/]\s*", "", title)

    # Clean punctuation/spacing and remove dangling connector punctuation.
    title = re.sub(r"\s+([,.;:!?])", r"\1", title)
    title = re.sub(r"([,.;:!?])\s*$", "", title)
    title = re.sub(r"\s+", " ", title).strip()

    return title


def strip_due_date_phrases(text):
    """Remove scheduling words from the visible task title.

    Due-date extraction happens separately with extract_due_date(). This helper
    only cleans the title so inputs like
    "Buy tickets for Ottawa Titans baseball game TODAY" become
    "Buy tickets for Ottawa Titans baseball game" while still receiving a due date.
    """
    t = str(text or "")

    for pattern in DUE_DATE_WORD_PATTERNS:
        t = re.sub(pattern, "", t, flags=re.IGNORECASE)

    # Clean leftover punctuation / spacing from removed date words.
    return sanitize_task_title_separators(t)


def extract_due_date(text):
    """Extract simple natural-language due dates from a task title.

    Supported examples:
    - today / tonight
    - tomorrow
    - this weekend / weekend  → upcoming Saturday
    - next weekend            → Saturday of the following weekend
    - by Friday / Friday      → next Friday
    """
    t = str(text or "").lower()
    today = datetime.now().date()

    month_lookup = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }

    month_day_match = re.search(
        rf"\b(?:by|due|on)?\s*({MONTH_NAME_PATTERN})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b",
        t,
        flags=re.IGNORECASE,
    )
    if month_day_match:
        month_name = month_day_match.group(1).lower()
        month = month_lookup.get(month_name)
        day = int(month_day_match.group(2))
        year = int(month_day_match.group(3)) if month_day_match.group(3) else today.year

        try:
            candidate = datetime(year, month, day).date()
        except ValueError:
            candidate = None

        # If no year was supplied and that date has already passed, assume the
        # next occurrence rather than silently dropping the due date.
        if candidate and not month_day_match.group(3) and candidate < today:
            try:
                candidate = datetime(today.year + 1, month, day).date()
            except ValueError:
                pass

        if candidate:
            return candidate

    if re.search(r"\b(today|tonight)\b", t):
        return today

    if re.search(r"\btomorrow\b", t):
        return today + timedelta(days=1)

    # Weekend handling must run before weekday matching.
    if re.search(r"\bnext\s+weekend\b", t):
        this_saturday = _next_weekday_date(today, 5, include_today=True)
        return this_saturday + timedelta(days=7)

    if re.search(r"\b(?:this\s+weekend|weekend)\b", t):
        return _next_weekday_date(today, 5, include_today=True)

    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2,
        "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
    }

    for word, day_num in weekdays.items():
        if re.search(rf"\b{word}\b", t):
            return _next_weekday_date(today, day_num, include_today=False)

    return None


