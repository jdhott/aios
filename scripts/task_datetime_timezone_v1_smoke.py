from datetime import date, datetime
from zoneinfo import ZoneInfo

from aios.temporal import (
    is_future_task_datetime,
    local_date_for_task_datetime,
    serialize_task_datetime,
    task_datetime,
)

TORONTO = ZoneInfo("America/Toronto")

# Exact failure window: UTC is Aug 20 while Toronto is still Aug 19.
evening = datetime(2026, 8, 19, 20, 35, tzinfo=TORONTO)
tomorrow = serialize_task_datetime(date(2026, 8, 20))
assert tomorrow == "2026-08-20T04:00:00+00:00", tomorrow
assert is_future_task_datetime(tomorrow, now=evening)
assert not is_future_task_datetime(
    tomorrow,
    now=datetime(2026, 8, 20, 0, 0, tzinfo=TORONTO),
)

# Date-only legacy data is interpreted as Toronto midnight, not UTC midnight.
assert serialize_task_datetime("2026-08-20") == "2026-08-20T04:00:00+00:00"
assert local_date_for_task_datetime("2026-08-20T04:00:00+00:00").isoformat() == "2026-08-20"

# DST is resolved by the IANA timezone rather than a hard-coded offset.
assert serialize_task_datetime("2026-12-11") == "2026-12-11T05:00:00+00:00"

# A real time-of-day defer remains a real instant.
later = serialize_task_datetime(datetime(2026, 8, 20, 17, 0, tzinfo=TORONTO))
assert later == "2026-08-20T21:00:00+00:00", later

# Already-aware values preserve their instant when normalized.
aware = task_datetime("2026-08-20T17:00:00-04:00")
assert aware.isoformat() == "2026-08-20T21:00:00+00:00"

print("PASS: Toronto evening boundary")
print("PASS: local-midnight calendar snooze")
print("PASS: DST-aware timezone normalization")
print("PASS: time-of-day instant preservation")
print("RESULT: TASK DATETIME TIMEZONE V1 SMOKE TEST PASSED")
