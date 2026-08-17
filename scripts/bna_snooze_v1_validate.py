from pathlib import Path

api = Path("aios/api/app.py").read_text()
web = Path("aios/web_capture/app.py").read_text()
engine = Path("execution_engine_v2.py").read_text()
runtime = Path("run_aios.py").read_text()

checks = [
    ("BNA snooze API exists", '@app.post("/tasks/{task_id}/snooze"' in api),
    ("BNA snooze reuses defer_until", '"defer_until": defer_until' in api),
    ("snooze processor trigger is backgrounded", 'background_tasks.add_task(_request_processor_run)' in api),
    ("Later today writes timestamp", 'preset == "later_today"' in api and 'target.isoformat()' in api),
    ("date presets remain date-only", 'preset == "tomorrow"' in api and '.date() + timedelta(days=1)' in api),
    ("execution engine supports timestamp defer", 'if "T" in text:' in engine and 'target > current' in engine),
    ("main runtime supports timestamp defer", 'if "T" in text:' in runtime and 'target > current' in runtime),
    ("BNA card renders Snooze control", '<summary>Snooze</summary>' in web),
    ("BNA has all v1 snooze choices", all(label in web for label in ('Later today', 'Tomorrow', '3 days', '1 week', 'Pick date'))),
    ("web snooze requests focus refresh", 'Best+Next+Action+snoozed.&refresh_focus=1' in web),
    ("focus API skips future-deferred stale winner", '_is_future_defer_value(candidate_task.get("defer_until"))' in api),
]

failed = []
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
    if not ok:
        failed.append(label)

if failed:
    print("RESULT: BNA SNOOZE V1 STRUCTURE VALIDATION FAILED")
    raise SystemExit(1)
print("RESULT: BNA SNOOZE V1 STRUCTURE VALID")
