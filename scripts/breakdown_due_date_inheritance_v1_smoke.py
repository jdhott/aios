from datetime import datetime
from zoneinfo import ZoneInfo

def effective_due(child, parent):
    return child.get("due_at") or parent.get("due_at")

def due_today(raw, today):
    if not raw:
        return False
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.date() <= today
        return dt.astimezone(ZoneInfo("America/Toronto")).date() <= today
    except (TypeError, ValueError):
        return str(raw)[:10] <= today.isoformat()

today = datetime(2026, 8, 18, tzinfo=ZoneInfo("America/Toronto")).date()

parent = {"due_at": "2026-08-18"}
child_no_due = {"due_at": None}
child_override = {"due_at": "2026-08-20"}

assert effective_due(child_no_due, parent) == "2026-08-18"
assert due_today(effective_due(child_no_due, parent), today)
print("Parent due date makes undated child eligible for Today: PASS")

assert effective_due(child_override, parent) == "2026-08-20"
assert not due_today(effective_due(child_override, parent), today)
print("Explicit child due date overrides parent: PASS")

assert effective_due({"due_at": None}, {"due_at": None}) is None
print("No due date remains unscheduled: PASS")

print("RESULT: BREAKDOWN DUE-DATE INHERITANCE V1 SMOKE TEST PASSED")
