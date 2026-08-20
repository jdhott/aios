from __future__ import annotations

from datetime import date, datetime, time, timezone
import os
from typing import Any
from zoneinfo import ZoneInfo


DEFAULT_LOCAL_TIMEZONE = "America/Toronto"


def local_timezone(timezone_name: str | None = None) -> ZoneInfo:
    """Return the canonical AIOS workflow timezone.

    AIOS stores absolute instants, but user-facing calendar semantics such as
    "today" and "tomorrow" are resolved in this local timezone first.
    """
    name = timezone_name or os.getenv("AIOS_LOCAL_TIMEZONE", DEFAULT_LOCAL_TIMEZONE)
    return ZoneInfo(name)


def local_now(*, now: datetime | None = None, timezone_name: str | None = None) -> datetime:
    tz = local_timezone(timezone_name)
    if now is None:
        return datetime.now(tz)
    if now.tzinfo is None:
        return now.replace(tzinfo=tz)
    return now.astimezone(tz)


def _parse_datetime_text(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def task_datetime(
    value: Any,
    *,
    timezone_name: str | None = None,
) -> datetime | None:
    """Normalize a task due/defer value to an aware UTC datetime.

    Date-only values intentionally mean local midnight in the AIOS workflow
    timezone. Naive datetimes are also interpreted in that timezone. Aware
    datetimes retain their instant and are normalized to UTC.
    """
    if value in (None, ""):
        return None

    tz = local_timezone(timezone_name)

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime.combine(value, time.min)
    else:
        text = str(value).strip()
        if not text:
            return None
        if len(text) == 10:
            try:
                parsed_date = date.fromisoformat(text[:10])
                dt = datetime.combine(parsed_date, time.min)
            except ValueError:
                dt = _parse_datetime_text(text)
        else:
            dt = _parse_datetime_text(text)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)

    return dt.astimezone(timezone.utc)


def serialize_task_datetime(
    value: Any,
    *,
    timezone_name: str | None = None,
) -> str | None:
    dt = task_datetime(value, timezone_name=timezone_name)
    return dt.isoformat() if dt is not None else None


def local_date_for_task_datetime(
    value: Any,
    *,
    timezone_name: str | None = None,
) -> date | None:
    dt = task_datetime(value, timezone_name=timezone_name)
    if dt is None:
        return None
    return dt.astimezone(local_timezone(timezone_name)).date()


def is_future_task_datetime(
    value: Any,
    *,
    now: datetime | None = None,
    timezone_name: str | None = None,
) -> bool:
    target = task_datetime(value, timezone_name=timezone_name)
    if target is None:
        return False
    current = local_now(now=now, timezone_name=timezone_name).astimezone(timezone.utc)
    return target > current
