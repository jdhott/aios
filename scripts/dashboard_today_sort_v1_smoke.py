from datetime import datetime
from zoneinfo import ZoneInfo

TORONTO = ZoneInfo("America/Toronto")
importance_order = {
    "High Importance": 0,
    "Medium Importance": 1,
    "Low Importance": 2,
}

def score_key(row: dict):
    score = row.get("execution_score")
    rank = row.get("execution_rank")
    return (
        score is None,
        -(float(score) if score is not None else 0.0),
        rank is None,
        int(rank) if rank is not None else 999999,
        (row.get("title") or "").lower(),
    )

def today_sort_key(row: dict):
    raw_due = row.get("effective_due_at") or row.get("due_at")
    try:
        due_dt = datetime.fromisoformat(str(raw_due).replace("Z", "+00:00"))
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=TORONTO)
        else:
            due_dt = due_dt.astimezone(TORONTO)
        due_key = due_dt
    except (TypeError, ValueError):
        due_key = datetime.max.replace(tzinfo=TORONTO)
    return (importance_order.get(row.get("importance"), 99), due_key, *score_key(row))

rows = [
    {"title": "Medium overdue", "importance": "Medium Importance", "due_at": "2026-08-18T04:00:00+00:00", "execution_score": 99},
    {"title": "High today", "importance": "High Importance", "due_at": "2026-08-20T04:00:00+00:00", "execution_score": 1},
    {"title": "High older", "importance": "High Importance", "due_at": "2026-08-19T04:00:00+00:00", "execution_score": 2},
    {"title": "Low oldest", "importance": "Low Importance", "due_at": "2026-08-01T04:00:00+00:00", "execution_score": 100},
    {"title": "High same date stronger score", "importance": "High Importance", "due_at": "2026-08-20T04:00:00+00:00", "execution_score": 50},
]

ordered = [row["title"] for row in sorted(rows, key=today_sort_key)]
expected = [
    "High older",
    "High same date stronger score",
    "High today",
    "Medium overdue",
    "Low oldest",
]
if ordered != expected:
    raise SystemExit(f"FAIL: unexpected Today order: {ordered}")
print("PASS: importance precedes due date")
print("PASS: due date ascends within importance")
print("PASS: execution score is tie-breaker only")

winter = {"title": "Winter", "importance": "High Importance", "due_at": "2026-12-01T05:00:00+00:00"}
summer = {"title": "Summer", "importance": "High Importance", "due_at": "2026-08-20T04:00:00+00:00"}
if today_sort_key(winter)[1].hour != 0 or today_sort_key(summer)[1].hour != 0:
    raise SystemExit("FAIL: timezone-aware due instants do not normalize to Toronto local midnight")
print("PASS: Toronto DST-aware due sorting")

print("RESULT: DASHBOARD TODAY SORT V1 SMOKE TEST PASSED")
