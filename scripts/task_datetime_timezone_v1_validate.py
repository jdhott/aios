from pathlib import Path

root = Path(__file__).resolve().parents[1]
api = (root / "aios/api/app.py").read_text()
engine = (root / "execution_engine_v2.py").read_text()
repo = (root / "aios/storage/task_repository.py").read_text()
temporal = (root / "aios/temporal.py").read_text()
migration = (root / "migrations/20260820_task_datetime_timezone_v1.sql").read_text()

checks = [
    ("canonical timezone helper", 'DEFAULT_LOCAL_TIMEZONE = "America/Toronto"' in temporal),
    ("date-only values localize before UTC", "datetime.combine(parsed_date, time.min)" in temporal),
    ("API snooze uses shared serializer", "serialize_task_datetime(target" in api),
    ("dashboard uses shared future check", "is_future_task_datetime(" in api),
    ("execution engine uses shared future check", "is_future_task_datetime(raw" in engine),
    ("repository parses task datetimes with timezone semantics", "due_at=task_datetime(" in repo and "defer_until=task_datetime(" in repo),
    ("repository serializes task datetimes", '"due_at": serialize_task_datetime(task.due_at)' in repo),
    ("migration targets timestamptz", "type timestamptz" in migration),
    ("migration interprets legacy dates in Toronto", "at time zone 'America/Toronto'" in migration),
]

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(("PASS: " if ok else "FAIL: ") + name)
if failed:
    raise SystemExit("FAILED: " + ", ".join(failed))
print("RESULT: TASK DATETIME TIMEZONE V1 STRUCTURE VALID")
