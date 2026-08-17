from datetime import datetime
from zoneinfo import ZoneInfo

from aios.api.app import TaskSnoozeRequest, _resolve_task_snooze_until, _is_future_defer_value
from execution_engine_v2 import is_deferred_until_future

TORONTO = ZoneInfo("America/Toronto")
now = datetime(2026, 8, 17, 13, 30, tzinfo=TORONTO)

later = _resolve_task_snooze_until(TaskSnoozeRequest(preset="later_today"), now=now)
assert later.startswith("2026-08-17T17:00:00")
print("Later today resolves to same-day timestamp: PASS")

tomorrow = _resolve_task_snooze_until(TaskSnoozeRequest(preset="tomorrow"), now=now)
assert tomorrow == "2026-08-18"
print("Tomorrow preserves date-only defer semantics: PASS")

three_days = _resolve_task_snooze_until(TaskSnoozeRequest(preset="three_days"), now=now)
assert three_days == "2026-08-20"
print("Three-day snooze resolves correctly: PASS")

future_timestamp_task = {
    "properties": {"Defer Until": {"date": {"start": "2026-08-17T17:00:00-04:00"}}}
}
assert is_deferred_until_future(future_timestamp_task, now=now)
assert not is_deferred_until_future(
    future_timestamp_task,
    now=datetime(2026, 8, 17, 17, 1, tzinfo=TORONTO),
)
print("Execution eligibility honors intra-day timestamp: PASS")

future_date_task = {
    "properties": {"Defer Until": {"date": {"start": "2026-08-18"}}}
}
assert is_deferred_until_future(future_date_task, today=now.date(), now=now)
assert not is_deferred_until_future(
    future_date_task,
    today=datetime(2026, 8, 18, tzinfo=TORONTO).date(),
    now=datetime(2026, 8, 18, 0, 1, tzinfo=TORONTO),
)
print("Existing date-only defer semantics preserved: PASS")

assert _is_future_defer_value("2026-08-17T17:00:00-04:00", now=now)
assert not _is_future_defer_value("2026-08-17T12:00:00-04:00", now=now)
print("Dashboard focus filter honors snooze timestamp: PASS")

print("RESULT: BNA SNOOZE V1 SMOKE TEST PASSED")
